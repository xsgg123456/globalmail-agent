"""Offline joint snapshots: PostgreSQL archive, registered bytes, configuration, watermark."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.deletion_journal import atomic_write, canonical, verify_receipts


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


class PostgresArchive:
    def __init__(self, engine, container=None):
        self.engine, self.container = engine, container

    def run(self, program, arguments, *, output=None, source=None):
        url = self.engine.url
        env = os.environ.copy()
        env["PGPASSWORD"] = url.password or ""
        if self.container:
            command = ["docker", "exec", "-i", "-e", "PGPASSWORD", self.container, program]
            host, port = "127.0.0.1", "5432"
        else:
            command, host, port = [program], url.host or "localhost", str(url.port or 5432)
        command += ["-h", host, "-p", port, "-U", url.username or "", "-d", url.database]
        try:
            with open(output, "wb") if output else open(os.devnull, "wb") as stdout:
                with open(source, "rb") if source else open(os.devnull, "rb") as stdin:
                    subprocess.run(command + arguments, env=env, stdin=stdin, stdout=stdout,
                                   stderr=subprocess.PIPE, check=True, timeout=180)
        except (OSError, subprocess.SubprocessError):
            raise RuntimeError("postgres_archive_failed") from None

    def dump(self, path, snapshot):
        self.run("pg_dump", ["-Fc", "--no-owner", "--no-acl", "--snapshot", snapshot], output=path)

    def restore(self, path):
        self.run("pg_restore", ["--no-owner", "--no-acl", "--exit-on-error", "--single-transaction"], source=path)


def lock_database(connection, *, allow_inherited_tasks=False):
    connection.execute(sa.text("SET LOCAL lock_timeout = '3s'"))
    sessions = connection.execute(sa.text("SELECT count(*) FROM pg_stat_activity "
        "WHERE datname=current_database() AND pid<>pg_backend_pid() AND backend_type='client backend'" )).scalar_one()
    if sessions:
        raise ValueError("backup_requires_stopped_services")
    names = connection.execute(sa.text("SELECT schemaname, tablename FROM pg_tables "
        "WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY schemaname,tablename")).all()
    quote = connection.dialect.identifier_preparer.quote
    if names:
        connection.execute(sa.text("LOCK TABLE " + ",".join(f"{quote(s)}.{quote(t)}" for s, t in names) + " IN SHARE MODE"))
    for table in ("jobs", "agent_runs"):
        if not allow_inherited_tasks and ("public", table) in names:
            if connection.execute(sa.text(f"SELECT count(*) FROM {table} WHERE status IN ('running','leased')")).scalar_one():
                raise ValueError("backup_active_tasks")


class BackupStore:
    def __init__(self, engine, object_root: Path, journal, *, container=None):
        self.engine, self.object_root, self.journal = engine, Path(object_root).resolve(), journal
        self.archive = PostgresArchive(engine, container)

    def create(self, destination: Path, configuration: dict):
        destination = Path(destination).absolute()
        if destination.exists() or destination.resolve() != destination:
            raise ValueError("backup_target_must_be_new")
        if destination.is_relative_to(self.object_root) or self.journal.root.is_relative_to(destination):
            raise ValueError("backup_overlaps_live_data")
        destination.mkdir(parents=True)
        atomic_write(destination / "INCOMPLETE", b"closed")
        # Clear only this service's idle pool; other clients are a deterministic refusal.
        self.engine.dispose()
        with self.engine.connect() as connection:
            with connection.begin():
                lock_database(connection)
                with self.journal.locked():
                    records, watermark = self.journal._read()
                    verify_receipts(connection, records)
                    snapshot = connection.execute(sa.text("SELECT pg_export_snapshot()")).scalar_one()
                    self.archive.dump(destination / "database.dump", snapshot)
                    rows = connection.execute(sa.text("SELECT id, sha256, size_bytes FROM objects o WHERE NOT EXISTS "
                        "(SELECT 1 FROM deletion_journal j WHERE j.target_object_id=o.id AND j.state='verified')")).mappings().all()
                    (destination / "objects").mkdir()
                    for row in rows:
                        source = self.object_root / str(row["id"])
                        if source.is_symlink() or source.resolve().parent != self.object_root:
                            raise ValueError("unsafe_backup_object")
                        target = destination / "objects" / str(row["id"])
                        shutil.copyfile(source, target)
                        if target.stat().st_size != row["size_bytes"] or digest(target) != row["sha256"]:
                            raise ValueError("backup_object_integrity_error")
                    atomic_write(destination / "configuration.json", canonical(configuration))
                    files = {p.relative_to(destination).as_posix(): digest(p)
                             for p in destination.rglob("*") if p.is_file() and p.name != "INCOMPLETE"}
                    manifest = {"format": 1, "id": str(uuid4()), "watermark": watermark,
                                "source_database": self.engine.url.database, "files": files}
                    manifest["signature"] = hmac.new((self.journal.root / "key").read_bytes(),
                        canonical(manifest), hashlib.sha256).hexdigest()
                    atomic_write(destination / "manifest.json", canonical(manifest))
                    (destination / "INCOMPLETE").unlink()
                    return manifest
    @staticmethod
    def verify(source: Path):
        source = Path(source).resolve()
        if (source / "INCOMPLETE").exists():
            raise ValueError("backup_incomplete")
        manifest = json.loads((source / "manifest.json").read_bytes())
        actual = {p.relative_to(source).as_posix() for p in source.rglob("*") if p.is_file()}
        if manifest.get("format") != 1 or actual != set(manifest["files"]) | {"manifest.json"}:
            raise ValueError("backup_file_manifest_error")
        for name, expected in manifest["files"].items():
            path = source / name
            if path.is_symlink() or not path.resolve().is_relative_to(source) or digest(path) != expected:
                raise ValueError("backup_integrity_error")
        return manifest
