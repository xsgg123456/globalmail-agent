"""Independent, authenticated tombstones. A torn append fails closed, never rolls back."""
from contextlib import contextmanager
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
from uuid import uuid4
import sqlalchemy as sa


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def atomic_write(path: Path, content: bytes):
    temporary = path.with_name(path.name + "." + uuid4().hex + ".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        if os.name != "nt":
            descriptor = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
    finally:
        temporary.unlink(missing_ok=True)


def verify_receipts(connection, records):
    """A database newer than a rolled-back journal must never silently lose receipts."""
    receipts = connection.execute(sa.text("SELECT request_id, seq FROM journal_receipts")).mappings().all()
    for receipt in receipts:
        sequence = receipt["seq"]
        if sequence < 1 or sequence > len(records) or records[sequence - 1].get("request_id") != str(receipt["request_id"]):
            raise ValueError("latest_journal_not_available")


class DeletionJournal:
    def __init__(self, root: Path):
        self.root = Path(root).absolute()

    @contextmanager
    def locked(self):
        self.root.mkdir(parents=True, exist_ok=True)
        if self.root.resolve() != self.root or self.root.is_symlink():
            raise ValueError("unsafe_journal_root")
        with (self.root / "journal.lock").open("a+b") as lock:
            lock.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                yield
            finally:
                lock.seek(0)
                if os.name == "nt":
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    fcntl.flock(lock, fcntl.LOCK_UN)

    def initialize(self):
        with self.locked():
            paths = [self.root / name for name in ("key", "records.json", "watermark.json")]
            if any(path.exists() for path in paths):
                self._read()
                return
            key = secrets.token_bytes(32)
            atomic_write(paths[0], key)
            os.chmod(paths[0], 0o600)
            atomic_write(paths[1], canonical([]))
            atomic_write(paths[2], canonical(self._watermark([], key)))

    def _watermark(self, records, key):
        value = {"seq": len(records), "digest": hashlib.sha256(canonical(records)).hexdigest()}
        return {**value, "signature": hmac.new(key, canonical(value), hashlib.sha256).hexdigest()}

    def _read(self):
        try:
            key = (self.root / "key").read_bytes()
            records = json.loads((self.root / "records.json").read_bytes())
            watermark = json.loads((self.root / "watermark.json").read_bytes())
            expected = self._watermark(records, key)
            if len(key) != 32 or not hmac.compare_digest(canonical(watermark), canonical(expected)):
                raise ValueError("journal_integrity_error")
            if any(record.get("seq") != i for i, record in enumerate(records, 1)):
                raise ValueError("journal_sequence_error")
            return records, watermark
        except (OSError, TypeError, KeyError, json.JSONDecodeError):
            raise ValueError("journal_watermark_unavailable") from None

    def read_verified(self):
        with self.locked():
            return self._read()

    def append(self, record: dict):
        # Only identifiers and lifecycle metadata; never serialize arbitrary body fields.
        allowed = {"action", "target_type", "target_id", "workspace_id", "request_id",
                   "mode", "branch_id", "customer_id", "generation", "created_at", "expected_version"}
        if set(record) - allowed or not {"action", "target_type", "target_id"} <= record.keys():
            raise ValueError("invalid_journal_record")
        value = {key: str(item) for key, item in record.items()}
        with self.locked():
            records, _ = self._read()
            value["seq"] = len(records) + 1
            records.append(value)
            key = (self.root / "key").read_bytes()
            # If interrupted between these replacements, the entire journal is refused.
            atomic_write(self.root / "records.json", canonical(records))
            atomic_write(self.root / "watermark.json", canonical(self._watermark(records, key)))
            return value
