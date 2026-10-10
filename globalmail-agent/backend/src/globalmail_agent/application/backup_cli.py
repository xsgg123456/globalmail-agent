"""Offline local maintenance CLI. Restore never points at the configured database."""
import argparse
import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4
import sqlalchemy as sa
from pydantic import SecretStr
from globalmail_agent.settings import Settings
from globalmail_agent.adapters.backup_store import BackupStore
from globalmail_agent.adapters.deletion_journal import DeletionJournal, atomic_write, canonical, verify_receipts
from globalmail_agent.adapters.object_store import ObjectStore
from globalmail_agent.application.restore import RestoreService


def configuration_manifest(settings):
    result = settings.model_dump(mode="json")
    for name in settings.__class__.model_fields:
        value = getattr(settings, name)
        if hasattr(value, "get_secret_value"):
            result[name] = {"configured": bool(value.get_secret_value()),
                "sha256": hashlib.sha256(value.get_secret_value().encode()).hexdigest()}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("backup", "restore"))
    parser.add_argument("--path", required=True, type=Path)
    parser.add_argument("--object-root", type=Path)
    parser.add_argument("--journal-root", type=Path)
    parser.add_argument("--container", default="globalmail-agent-postgres-1")
    args = parser.parse_args()
    settings = Settings.from_env()
    root = settings.object_root.absolute()
    journal = DeletionJournal(args.journal_root or settings.lifecycle_journal_root or
                              root.parent / (root.name + "-lifecycle"))
    source_url = sa.engine.make_url(settings.database_url.get_secret_value())
    if args.action == "backup":
        engine = sa.create_engine(source_url, hide_parameters=True)
        try:
            # Only a database without deletion history may initialize the external log.
            with engine.connect() as conn:
                count = conn.execute(sa.text("SELECT count(*) FROM deletion_journal")).scalar_one()
                count += conn.execute(sa.text("SELECT count(*) FROM deletion_requests")).scalar_one()
            if count:
                journal.read_verified()
            else:
                journal.initialize()
            result = BackupStore(engine, root, journal, container=args.container).create(
                args.path, configuration_manifest(settings))
            print(json.dumps({"backup_id": result["id"], "path": str(args.path.absolute())}))
        finally:
            engine.dispose()
        return
    if args.object_root is None:
        parser.error("restore requires --object-root (a new isolated directory)")
    config_path = args.object_root.absolute().parent / (args.object_root.name + "-settings.json")
    if args.object_root.exists() or config_path.exists():
        raise ValueError("restore_requires_new_target")
    # Validate backup and latest log before allocating a new database.
    BackupStore.verify(args.path)
    records, _ = journal.read_verified()
    # The currently configured source is a second monotonic witness. Its receipts
    # reject an accidentally rolled-back external log before allocating a target.
    witness = sa.create_engine(source_url, hide_parameters=True)
    try:
        with witness.connect() as conn:
            verify_receipts(conn, records)
    finally:
        witness.dispose()
    database = "globalmail_restore_" + uuid4().hex
    target_url = source_url.set(database=database)
    admin = sa.create_engine(source_url.set(database="postgres"), isolation_level="AUTOCOMMIT", hide_parameters=True)
    with admin.connect() as conn:
        conn.execute(sa.text(f'CREATE DATABASE "{database}"'))
    admin.dispose()
    engine = sa.create_engine(target_url, hide_parameters=True)
    restored = settings.model_copy(update={"object_root": args.object_root.absolute(),
        "database_url": SecretStr(target_url.render_as_string(hide_password=False)), "lifecycle_journal_root": journal.root})
    from globalmail_agent.application.lifecycle import LifecycleService
    store = ObjectStore(args.object_root, engine)

    def replay(record):
        LifecycleService(engine, store, restored, UUID(record["workspace_id"])).replay(record)

    try:
        result = RestoreService(engine, args.object_root, journal, container=args.container).restore(args.path, replay=replay)
        # Store the new target config only alongside the isolated data, never over live settings.
        configuration = configuration_manifest(settings)
        configuration.update(database_url=target_url.render_as_string(hide_password=False),
            object_root=str(args.object_root.absolute()), lifecycle_journal_root=str(journal.root),
            allowed_origins=",".join(settings.allowed_origins))
        atomic_write(config_path, canonical(configuration))
        print(json.dumps({"status": result["status"], "database": database, "settings": str(config_path)}))
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
