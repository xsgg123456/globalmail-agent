"""Real PG archive restoration, independent tombstones and corruption refusals."""
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from uuid import UUID, uuid4
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from globalmail_agent.adapters.backup_store import BackupStore
from globalmail_agent.adapters.deletion_journal import DeletionJournal
from globalmail_agent.adapters.object_store import ObjectStore, Scope, Source
from globalmail_agent.adapters.schema import objects, workspaces
from globalmail_agent.application.restore import RestoreService, assert_restore_open


class JournalTests(unittest.TestCase):
    def test_concurrent_append_missing_and_torn_watermark_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            journal = DeletionJournal(Path(temp))
            journal.initialize()
            with ThreadPoolExecutor(max_workers=4) as executor:
                list(executor.map(lambda i: journal.append({"action": "delete", "target_type": "object",
                    "target_id": str(i)}), range(12)))
            records, watermark = journal.read_verified()
            self.assertEqual([r["seq"] for r in records], list(range(1, 13)))
            self.assertEqual(watermark["seq"], 12)
            (Path(temp) / "records.json").write_text("[]")
            with self.assertRaisesRegex(ValueError, "integrity"):
                journal.read_verified()
            (Path(temp) / "watermark.json").unlink()
            with self.assertRaisesRegex(ValueError, "unavailable"):
                journal.initialize()


@unittest.skipUnless(os.getenv("GLOBALMAIL_TEST_DATABASE_URL"), "requires isolated PostgreSQL")
class BackupRestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="globalmail_backup_")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        url = sa.engine.make_url(os.environ["GLOBALMAIL_TEST_DATABASE_URL"])
        self.admin = sa.create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT", hide_parameters=True)
        self.databases, self.engines = [], []
        self.addCleanup(self.cleanup)
        self.source = self.database("globalmail_backup_" + uuid4().hex)
        self.target = self.database("globalmail_restore_" + uuid4().hex)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with self.source.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
        self.journal = DeletionJournal(self.root / "journal")
        self.journal.initialize()
        self.store = ObjectStore(self.root / "source-objects", self.source)
        workspace = uuid4()
        with self.source.begin() as conn:
            conn.execute(workspaces.insert().values(id=workspace, name="backup fixture"))
        scope = Scope(workspace_id=workspace, mode="simulation", branch_id=uuid4(), customer_id=uuid4(), purpose="test")
        self.old = self.store.put(b"private old content", scope, Source(kind="test", reference="old"))
        self.keep = self.store.put(b"allowed content", scope, Source(kind="test", reference="keep"))
        self.container = os.getenv("GLOBALMAIL_TEST_PG_CONTAINER", "globalmail-agent-postgres-1")
        self.backups = BackupStore(self.source, self.store.root, self.journal, container=self.container)

    def database(self, name):
        with self.admin.connect() as conn:
            conn.execute(sa.text(f'CREATE DATABASE "{name}"'))
        self.databases.append(name)
        engine = sa.create_engine(self.admin.url.set(database=name), hide_parameters=True)
        self.engines.append(engine)
        return engine

    def cleanup(self):
        for engine in self.engines:
            engine.dispose()
        with self.admin.connect() as conn:
            for name in self.databases:
                conn.execute(sa.text(f'DROP DATABASE "{name}" WITH (FORCE)'))
        self.admin.dispose()

    def test_old_backup_replays_latest_delete_and_preserves_legal_object(self):
        from globalmail_agent.adapters.lifecycle_schema import journal_receipts
        backup = self.root / "backup"
        self.backups.create(backup, {"model": "test", "schema": "current"})
        with self.source.connect() as conn:
            workspace = conn.execute(sa.select(objects.c.workspace_id).where(objects.c.id == self.old)).scalar_one()
        self.journal.append({"action": "delete", "target_type": "object", "target_id": self.old,
            "request_id": uuid4(), "workspace_id": workspace})
        destination = self.root / "restored-objects"

        def replay(record):
            with self.target.begin() as conn:
                conn.execute(objects.delete().where(objects.c.id == record["target_id"]))
                conn.execute(journal_receipts.insert().values(request_id=UUID(record["request_id"]),
                    workspace_id=UUID(record["workspace_id"]), seq=record["seq"]))
            (destination / record["target_id"]).unlink(missing_ok=True)

        state = RestoreService(self.target, destination, self.journal, container=self.container).restore(backup, replay=replay)
        self.assertEqual(state["status"], "verified")
        assert_restore_open(destination)
        self.assertFalse((destination / str(self.old)).exists())
        self.assertEqual((destination / str(self.keep)).read_bytes(), b"allowed content")
        self.assertEqual((self.store.root / str(self.old)).read_bytes(), b"private old content")
        with self.assertRaisesRegex(ValueError, "new_object_root"):
            RestoreService(self.target, destination, self.journal).restore(backup, replay=replay)

    def test_tampered_backup_and_missing_latest_watermark_stay_closed(self):
        backup = self.root / "backup"
        self.backups.create(backup, {})
        (backup / "objects" / str(self.old)).write_bytes(b"tampered")
        destination = self.root / "closed"
        with self.assertRaisesRegex(ValueError, "integrity"):
            RestoreService(self.target, destination, self.journal).restore(backup, replay=lambda r: None)
        with self.assertRaisesRegex(RuntimeError, "restore_closed"):
            assert_restore_open(destination)
        (self.journal.root / "watermark.json").unlink()
        with self.assertRaisesRegex(ValueError, "unavailable"):
            RestoreService(self.target, self.root / "missing", self.journal).restore(backup, replay=lambda r: None)

    def test_live_connection_refuses_backup(self):
        other = sa.create_engine(self.source.url)
        try:
            with other.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
                with self.assertRaisesRegex(ValueError, "stopped_services"):
                    self.backups.create(self.root / "blocked", {})
        finally:
            other.dispose()

    def test_real_lifecycle_replay_removes_old_conversation_and_freezes_jobs(self):
        from globalmail_agent.application.conversations import ConversationService
        from globalmail_agent.application.lifecycle import LifecycleService
        from globalmail_agent.adapters.conversation_schema import conversations, jobs
        from globalmail_agent.domain.conversation import CreateConversation
        from globalmail_agent.settings import Settings
        settings = Settings(lifecycle_journal_root=self.journal.root)
        row = ConversationService(self.source, self.store).create(CreateConversation(
            expected_version=0, sender_email="restore@example.test", body="RESTORE_PRIVATE_SENTINEL"), uuid4().hex)
        cid = UUID(row["conversation_id"])
        backup = self.root / "lifecycle-backup"
        self.backups.create(backup, {})
        log_paths = [self.journal.root / name for name in ("records.json", "watermark.json")]
        old_log = [path.read_bytes() for path in log_paths]
        lifecycle = LifecycleService(self.source, self.store, settings)
        request = lifecycle.request("conversation", cid, lifecycle.preview("conversation", cid)["expected_version"])
        self.assertEqual(lifecycle.process(request["id"])["status"], "completed")
        self.backups.create(self.root / "post-deletion-backup", {})
        latest_log = [path.read_bytes() for path in log_paths]
        try:
            for path, content in zip(log_paths, old_log):
                path.write_bytes(content)
            with self.assertRaisesRegex(ValueError, "latest_journal"):
                self.backups.create(self.root / "rolled-back-journal", {})
        finally:
            for path, content in zip(log_paths, latest_log):
                path.write_bytes(content)
        destination = self.root / "lifecycle-restored"
        replay = LifecycleService(self.target, ObjectStore(destination, self.target), settings).replay
        state = RestoreService(self.target, destination, self.journal, container=self.container).restore(backup, replay=replay)
        self.assertEqual(state["status"], "verified")
        with self.target.connect() as conn:
            self.assertEqual(conn.execute(sa.select(conversations.c.lifecycle).where(conversations.c.id == cid)).scalar_one(), "deleted")
            self.assertEqual(conn.execute(sa.select(sa.func.count()).select_from(jobs).where(jobs.c.status == "queued")).scalar_one(), 0)
        self.assertFalse(any(b"RESTORE_PRIVATE_SENTINEL" in path.read_bytes() for path in destination.iterdir()))

    def test_newer_deleted_target_absent_from_old_backup_has_receipt(self):
        from globalmail_agent.application.conversations import ConversationService
        from globalmail_agent.application.lifecycle import LifecycleService
        from globalmail_agent.adapters.lifecycle_schema import journal_receipts
        from globalmail_agent.domain.conversation import CreateConversation
        from globalmail_agent.settings import Settings
        settings = Settings(lifecycle_journal_root=self.journal.root)
        backup = self.root / "before-creation"
        self.backups.create(backup, {})
        row = ConversationService(self.source, self.store).create(CreateConversation(
            expected_version=0, sender_email="absent@example.test", body="NEWER_PRIVATE_SENTINEL"), uuid4().hex)
        cid = UUID(row["conversation_id"])
        lifecycle = LifecycleService(self.source, self.store, settings)
        request = lifecycle.request("conversation", cid, lifecycle.preview("conversation", cid)["expected_version"])
        self.assertEqual(lifecycle.process(request["id"])["status"], "completed")
        destination = self.root / "absent-restored"
        service = LifecycleService(self.target, ObjectStore(destination, self.target), settings)
        state = RestoreService(self.target, destination, self.journal, container=self.container).restore(
            backup, replay=service.replay)
        self.assertEqual(state["status"], "verified")
        records, _ = self.journal.read_verified()
        self.assertTrue(service.replay(records[0])["already_absent"])
        with self.target.connect() as conn:
            receipts = conn.execute(sa.select(journal_receipts)).all()
        self.assertEqual(len(receipts), 1)
        self.assertEqual(str(receipts[0].request_id), request["id"])
        self.assertEqual(receipts[0].seq, 1)
        assert_restore_open(destination)

    def test_same_database_replay_after_rollback_failure_and_retry(self):
        from globalmail_agent.application.conversations import ConversationService
        from globalmail_agent.application.lifecycle import LifecycleService
        from globalmail_agent.application.journal_gate import assert_journal_current
        from globalmail_agent.application.replay_journal import JournalRecovery
        from globalmail_agent.adapters.conversation_schema import conversations
        from globalmail_agent.domain.conversation import CreateConversation
        from globalmail_agent.settings import Settings
        settings = Settings(lifecycle_journal_root=self.journal.root)
        row = ConversationService(self.source, self.store).create(CreateConversation(
            expected_version=0, sender_email="recovery@example.test", body="RECOVERY_PRIVATE_SENTINEL"), uuid4().hex)
        cid = UUID(row["conversation_id"])
        lifecycle = LifecycleService(self.source, self.store, settings)
        with patch.object(lifecycle, "_revoke", side_effect=RuntimeError("transaction_crash")):
            with self.assertRaisesRegex(RuntimeError, "transaction_crash"):
                lifecycle.request("conversation", cid, lifecycle.preview("conversation", cid)["expected_version"])
        with self.assertRaisesRegex(RuntimeError, "journal_replay_required"):
            assert_journal_current(self.source, self.store)
        recovery = JournalRecovery(self.source, self.store.root, self.journal, settings)
        with patch.object(LifecycleService, "replay", return_value={"status": "completed"}):
            with self.assertRaisesRegex(ValueError, "receipts_incomplete"):
                recovery.run()
        with self.assertRaisesRegex(RuntimeError, "restore_closed"):
            assert_restore_open(self.store.root)
        self.assertEqual(recovery.run()["status"], "verified")
        assert_restore_open(self.store.root)
        assert_journal_current(self.source, self.store)
        with self.source.connect() as conn:
            self.assertEqual(conn.execute(sa.select(conversations.c.lifecycle).where(
                conversations.c.id == cid)).scalar_one(), "deleted")
        self.assertFalse(any(b"RECOVERY_PRIVATE_SENTINEL" in path.read_bytes() for path in self.store.root.iterdir()))
        self.assertEqual(recovery.run()["status"], "verified")

    def test_recovery_refuses_live_connection_and_active_worker(self):
        from globalmail_agent.application.replay_journal import JournalRecovery
        from globalmail_agent.application.conversations import ConversationService
        from globalmail_agent.adapters.conversation_schema import jobs
        from globalmail_agent.domain.conversation import CreateConversation
        from globalmail_agent.settings import Settings
        recovery = JournalRecovery(self.source, self.store.root, self.journal, Settings())
        other = sa.create_engine(self.source.url)
        try:
            with other.connect() as conn:
                conn.execute(sa.text("SELECT 1"))
                with self.assertRaisesRegex(ValueError, "stopped_services"):
                    recovery.run()
        finally:
            other.dispose()
        ConversationService(self.source, self.store).create(CreateConversation(
            expected_version=0, sender_email="worker@example.test", body="worker"), uuid4().hex)
        with self.source.begin() as conn:
            conn.execute(jobs.update().values(status="running", lease_expires_at=sa.func.now() + sa.text("interval '1 minute'")))
        with self.assertRaisesRegex(ValueError, "active_tasks"):
            recovery.run()

    def test_restore_without_replay_receipt_stays_closed(self):
        backup = self.root / "receipt-backup"
        self.backups.create(backup, {})
        self.journal.append({"action": "delete", "target_type": "object", "target_id": self.old,
            "request_id": uuid4(), "workspace_id": uuid4()})
        destination = self.root / "no-receipt"
        with self.assertRaisesRegex(ValueError, "receipts_incomplete"):
            RestoreService(self.target, destination, self.journal, container=self.container).restore(
                backup, replay=lambda record: None)
        with self.assertRaisesRegex(RuntimeError, "restore_closed"):
            assert_restore_open(destination)

    def test_recovery_receipt_without_completed_deletion_stays_closed(self):
        from globalmail_agent.application.conversations import ConversationService
        from globalmail_agent.application.lifecycle import LifecycleService
        from globalmail_agent.application.replay_journal import JournalRecovery
        from globalmail_agent.domain.conversation import CreateConversation
        from globalmail_agent.settings import Settings
        settings = Settings(lifecycle_journal_root=self.journal.root)
        row = ConversationService(self.source, self.store).create(CreateConversation(
            expected_version=0, sender_email="incomplete@example.test", body="incomplete"), uuid4().hex)
        cid = UUID(row["conversation_id"])
        lifecycle = LifecycleService(self.source, self.store, settings)
        lifecycle.request("conversation", cid, lifecycle.preview("conversation", cid)["expected_version"])
        recovery = JournalRecovery(self.source, self.store.root, self.journal, settings)
        with patch.object(LifecycleService, "replay", return_value={"status": "completed"}):
            with self.assertRaisesRegex(ValueError, "deletion_incomplete"):
                recovery.run()
        with self.assertRaisesRegex(RuntimeError, "restore_closed"):
            assert_restore_open(self.store.root)
        self.assertEqual(recovery.run()["status"], "verified")
