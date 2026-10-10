"""Fresh isolated restore; no query or worker may run until every gate passes."""
import hashlib
import hmac
import json
from pathlib import Path
import re
import shutil
import sqlalchemy as sa
from globalmail_agent.adapters.backup_store import BackupStore, PostgresArchive, digest
from globalmail_agent.adapters.deletion_journal import atomic_write, canonical, verify_receipts
from globalmail_agent.application.restore_checks import freeze_inherited_work, verify_restored_database


def restore_state_path(object_root: Path):
    root = Path(object_root).absolute()
    return root.parent / (root.name + "-restore-state.json")


def assert_restore_open(object_root: Path):
    marker = restore_state_path(object_root)
    if marker.exists():
        try:
            state = json.loads(marker.read_bytes())
            if state.get("status") == "verified":
                return
        except (OSError, ValueError):
            pass
        raise RuntimeError("restore_closed")


class RestoreService:
    def __init__(self, engine, object_root: Path, journal, *, container=None):
        self.engine, self.root, self.journal = engine, Path(object_root).absolute(), journal
        self.archive = PostgresArchive(engine, container)

    def restore(self, backup: Path, *, replay, verify=None):
        if not re.fullmatch(r"globalmail_restore_[a-z0-9_]{1,45}", self.engine.url.database or ""):
            raise ValueError("restore_requires_isolated_database")
        if self.root.exists() or self.root.resolve() != self.root or restore_state_path(self.root).exists():
            raise ValueError("restore_requires_new_object_root")
        backup = Path(backup).resolve()
        if self.root.is_relative_to(backup) or self.journal.root.is_relative_to(self.root):
            raise ValueError("restore_overlaps_source")
        self.engine.dispose()
        with self.engine.connect() as connection:
            if connection.execute(sa.text("SELECT count(*) FROM pg_tables WHERE schemaname NOT IN "
                "('pg_catalog','information_schema')")).scalar_one():
                raise ValueError("restore_database_not_empty")
            if connection.execute(sa.text("SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() "
                "AND pid<>pg_backend_pid() AND backend_type='client backend'")).scalar_one():
                raise ValueError("restore_database_in_use")
        self.engine.dispose()
        self.root.mkdir(parents=True)
        marker = restore_state_path(self.root)
        atomic_write(marker, canonical({"status": "closed"}))
        with self.journal.locked():
            records, watermark = self.journal._read()
            manifest = BackupStore.verify(backup)
            signature = manifest.pop("signature", "")
            expected = hmac.new((self.journal.root / "key").read_bytes(), canonical(manifest), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                raise ValueError("backup_authentication_failed")
            old = manifest["watermark"]
            if old["seq"] > watermark["seq"] or hashlib.sha256(canonical(records[:old["seq"]])).hexdigest() != old["digest"]:
                raise ValueError("latest_journal_not_available")
            self.archive.restore(backup / "database.dump")
            with self.engine.connect() as connection:
                verify_receipts(connection, records)
            for path in (backup / "objects").iterdir():
                shutil.copyfile(path, self.root / path.name)
            freeze_inherited_work(self.engine)
            # Replay even entries preceding the snapshot: intent may have preceded DB commit.
            for record in records:
                replay(record)
            with self.engine.connect() as connection:
                verify_receipts(connection, records)
                actual = {str(row.request_id): row.seq for row in connection.execute(
                    sa.text("SELECT request_id, seq FROM journal_receipts"))}
                expected_receipts = {record["request_id"]: record["seq"] for record in records}
                if len(expected_receipts) != len(records) or actual != expected_receipts:
                    raise ValueError("restore_journal_receipts_incomplete")
            checks = verify_restored_database(self.engine, self.root)
            if verify is not None and verify() is not True:
                raise ValueError("restore_extra_verification_failed")
            if not isinstance(checks, dict) or any(checks.get(key) is not True for key in ("objects", "indexes", "task_fences")):
                raise ValueError("restore_verification_failed")
            self._verify_objects()
            state = {"status": "verified", "backup_id": manifest["id"], "watermark": watermark}
            atomic_write(marker, canonical(state))
            return state

    def _verify_objects(self):
        with self.engine.connect() as connection:
            objects = connection.execute(sa.text("SELECT id, sha256, size_bytes FROM objects o WHERE NOT EXISTS "
                "(SELECT 1 FROM deletion_journal j WHERE j.target_object_id=o.id AND j.state='verified')")).mappings().all()
        names = {str(row["id"]) for row in objects}
        for path in self.root.iterdir():
            if path.name not in names or path.is_symlink() or not path.is_file():
                raise ValueError("restore_unregistered_object")
        for row in objects:
            path = self.root / str(row["id"])
            if not path.is_file() or path.stat().st_size != row["size_bytes"] or digest(path) != row["sha256"]:
                raise ValueError("restore_object_integrity_error")
