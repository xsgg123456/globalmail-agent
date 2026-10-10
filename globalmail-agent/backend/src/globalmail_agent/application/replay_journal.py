"""Offline in-place recovery after an external intent outlives its DB transaction."""
import argparse
import json
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa

from globalmail_agent.adapters.backup_store import lock_database
from globalmail_agent.adapters.deletion_journal import DeletionJournal, atomic_write, canonical, verify_receipts
from globalmail_agent.adapters.object_store import ObjectStore
from globalmail_agent.application.lifecycle import LifecycleService
from globalmail_agent.application.restore import RestoreService, restore_state_path
from globalmail_agent.application.restore_checks import freeze_inherited_work, verify_restored_database
from globalmail_agent.settings import Settings


class JournalRecovery:
    def __init__(self, engine, object_root, journal, settings):
        self.engine, self.root = engine, Path(object_root).absolute()
        self.journal, self.settings = journal, settings

    def _offline(self, connection):
        lock_database(connection, allow_inherited_tasks=True)
        # No connected writer may remain. Unexpired leases still require waiting;
        # offline expired state is fenced below, not mistaken for a live process.
        if connection.execute(sa.text("SELECT count(*) FROM jobs WHERE status IN ('running','leased') "
            "AND lease_expires_at > now()")).scalar_one():
            raise ValueError("journal_recovery_active_tasks")
        if connection.execute(sa.text(
            "SELECT count(*) FROM agent_slots WHERE lease_owner IS NOT NULL AND lease_expires_at > now()"
        )).scalar_one():
            raise ValueError("journal_recovery_active_tasks")

    def run(self):
        if not self.root.is_dir() or self.root.resolve() != self.root:
            raise ValueError("journal_recovery_invalid_object_root")
        marker = restore_state_path(self.root)
        self.engine.dispose()
        # The external journal lock serializes replay attempts and holds the latest
        # watermark stable. API and workers see the closed marker throughout.
        with self.journal.locked():
            with self.engine.begin() as connection:
                self._offline(connection)
                atomic_write(marker, canonical({"status": "closed", "operation": "journal_replay"}))
            records, watermark = self.journal._read()
            with self.engine.connect() as connection:
                verify_receipts(connection, records)
            freeze_inherited_work(self.engine)
            store = ObjectStore(self.root, self.engine)
            for record in records:
                LifecycleService(self.engine, store, self.settings, UUID(record["workspace_id"])).replay(record)
            with self.engine.connect() as connection:
                verify_receipts(connection, records)
                actual = {str(row.request_id): row.seq for row in connection.execute(
                    sa.text("SELECT request_id, seq FROM journal_receipts"))}
                expected = {record["request_id"]: record["seq"] for record in records}
                if len(expected) != len(records) or actual != expected:
                    raise ValueError("journal_recovery_receipts_incomplete")
            verify_restored_database(self.engine, self.root)
            RestoreService(self.engine, self.root, self.journal)._verify_objects()
            self.engine.dispose()
            with self.engine.begin() as connection:
                self._offline(connection)
                state = {"status": "verified", "operation": "journal_replay", "watermark": watermark}
                atomic_write(marker, canonical(state))
            return state


def main():
    parser = argparse.ArgumentParser(description="Offline journal replay; stop API and workers first.")
    parser.add_argument("--object-root", type=Path)
    parser.add_argument("--journal-root", type=Path)
    args = parser.parse_args()
    engine = None
    try:
        settings = Settings.from_env()
        root = (args.object_root or settings.object_root).absolute()
        journal = DeletionJournal(args.journal_root or settings.lifecycle_journal_root or
                                  root.parent / (root.name + "-lifecycle"))
        engine = sa.create_engine(settings.database_url.get_secret_value(), hide_parameters=True)
        state = JournalRecovery(engine, root, journal, settings).run()
        print(json.dumps({"status": state["status"], "journal_seq": state["watermark"]["seq"]}))
        return 0
    except Exception:
        # Connection and validation errors can contain credentials or private values.
        print(json.dumps({"status": "failed", "error": "journal_recovery_failed",
                          "hint": "stop_services_check_journal_and_deletion_status_then_retry"}))
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
