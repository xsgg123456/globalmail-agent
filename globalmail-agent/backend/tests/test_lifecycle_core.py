"""Real isolated PostgreSQL lifecycle tests; no production mutations or models."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from uuid import UUID, uuid4
import sqlalchemy as sa
from agent_fixture import AgentFixture
from globalmail_agent.adapters import conversation_schema as c, agent_schema as a
from globalmail_agent.adapters.lifecycle_schema import deletion_requests
from globalmail_agent.adapters.schema import objects, deletion_journal
from globalmail_agent.application.lifecycle import LifecycleService
from globalmail_agent.application.conversation_lock import ServiceError


class LifecycleTests(AgentFixture):
    def test_newer_journal_target_absent_in_old_snapshot_is_already_deleted(self):
        from globalmail_agent.adapters.lifecycle_schema import journal_receipts
        self.lifecycle.journal.initialize()
        for kind, action in [('conversation','delete'),('attachment','revoke'),('document','withdraw')]:
            record = self.lifecycle.journal.append({'request_id':str(uuid4()), 'workspace_id':str(self.lifecycle.workspace),
                'target_type':kind, 'target_id':str(uuid4()), 'action':action})
            self.assertTrue(self.lifecycle.replay(record)['already_absent'])
        self.assertEqual(self.count(journal_receipts), 3)

    def setUp(self):
        super().setUp()
        settings = SimpleNamespace(lifecycle_journal_root=Path(self.temp.name) / "journal")
        self.lifecycle = LifecycleService(self.engine, self.store, settings)

    def request_delete(self, cid):
        preview = self.lifecycle.preview("conversation", cid)
        return self.lifecycle.request("conversation", cid, preview["expected_version"])

    def test_preview_no_writes_confirm_fences_and_purges_other_branch_preserved(self):
        cid, run = self.create_mail(body="DELETE_PRIVATE_SENTINEL")
        other, _ = self.create_mail(body="OTHER_BRANCH_KEEP", email="other@example.test")
        preview = self.lifecycle.preview("conversation", cid)
        self.assertGreater(preview["impact"]["objects"], 0)
        self.assertEqual(self.count(deletion_requests), 0)
        self.assertEqual(self.count(deletion_journal), 0)
        request = self.lifecycle.request("conversation", cid, preview["expected_version"])
        self.assertEqual(request["status"], "revoked")
        self.assertFalse(self.row(c.agent_runs, c.agent_runs.c.id == run)["checkpoint_writable"])
        with patch("globalmail_agent.observability.purge.PurgeService.purge_runs", return_value=True):
            result = self.lifecycle.process(request["id"])
        self.assertEqual(result["status"], "completed", result)
        self.assertEqual(self.row(c.conversations, c.conversations.c.id == cid)["lifecycle"], "deleted")
        self.assertEqual(self.row(c.conversations, c.conversations.c.id == other)["lifecycle"], "open")
        with self.engine.connect() as conn:
            body = conn.execute(sa.select(c.messages.c.body_object_id).where(c.messages.c.conversation_id == cid)).scalar_one()
            kept = conn.execute(sa.select(c.messages.c.body_object_id).where(c.messages.c.conversation_id == other)).scalar_one()
        self.assertFalse(self.store._path(body).exists())
        self.assertIn(b"OTHER_BRANCH_KEEP", self.store._path(kept).read_bytes())
        self.assertEqual(self.lifecycle.process(request["id"])["status"], "completed")

    def test_failed_remote_keeps_retry_metadata_and_blocks_completion(self):
        cid, run = self.create_mail()
        request = self.request_delete(cid)
        with patch("globalmail_agent.observability.purge.PurgeService.purge_runs",
                side_effect=ServiceError("observability_purge_unconfirmed", 503)):
            result = self.lifecycle.process(request["id"])
        self.assertEqual(result["status"], "cleanup_failed")
        self.assertEqual(result["error_code"], "observability_purge_unconfirmed")
        with patch("globalmail_agent.observability.purge.PurgeService.purge_runs", return_value=True):
            self.assertEqual(self.lifecycle.process(request["id"])["status"], "completed")

    def test_stale_confirmation_does_not_append_tombstones(self):
        cid, _ = self.create_mail()
        with self.assertRaises(ServiceError):
            self.lifecycle.request("conversation", cid, -1)
        self.assertEqual(self.count(deletion_requests), 0)
        self.assertEqual(self.count(deletion_journal), 0)

    def test_reset_creates_one_fresh_empty_branch_and_preserves_source(self):
        cid, _ = self.create_mail()
        preview = self.lifecycle.preview("conversation", cid)
        request = self.lifecycle.request("conversation", cid, preview["expected_version"], action="reset")
        with patch("globalmail_agent.observability.purge.PurgeService.purge_runs", return_value=True):
            result = self.lifecycle.process(request["id"])
        self.assertEqual(result["status"], "completed", result)
        fresh = UUID(result["new_conversation_id"])
        self.assertNotEqual(fresh, cid)
        old_row = self.row(c.conversations, c.conversations.c.id == cid)
        new_row = self.row(c.conversations, c.conversations.c.id == fresh)
        self.assertEqual(new_row["lifecycle"], "open")
        self.assertNotEqual(new_row["branch_id"], old_row["branch_id"])
        self.assertEqual(self.lifecycle.process(request["id"])["new_conversation_id"], str(fresh))

    def test_purges_checkpoint_rows_and_inline_holders(self):
        cid, run = self.create_mail()
        with self.engine.begin() as conn:
            conn.execute(sa.text("INSERT INTO checkpoints (thread_id,checkpoint_ns,checkpoint_id,checkpoint,metadata) "
                "VALUES (:id,'','delete-test','{\"private\":\"PRIVATE_CHECKPOINT\"}','{}')"), {"id": str(run)})
            conn.execute(c.domain_events.update().where(c.domain_events.c.conversation_id == cid)
                .values(payload={"body": "PRIVATE_EVENT"}))
        request = self.request_delete(cid)
        with patch("globalmail_agent.observability.purge.PurgeService.purge_runs", return_value=True):
            result = self.lifecycle.process(request["id"])
        self.assertEqual(result["status"], "completed", result)
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(sa.text("SELECT count(*) FROM checkpoints")).scalar_one(), 0)
            self.assertTrue(all(v == {} for v in conn.execute(sa.select(c.domain_events.c.payload)
                .where(c.domain_events.c.conversation_id == cid)).scalars()))

    def test_late_checkpoint_and_object_registration_cannot_resurrect_deleted_content(self):
        from langgraph.checkpoint.base import empty_checkpoint
        from globalmail_agent.adapters.checkpoint_repository import CheckpointRepository
        from globalmail_agent.adapters.object_store import Scope, Source
        from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
        from globalmail_agent.agent.context import load_context
        cid, run = self.create_mail()
        job = self.claimed()
        load_context(self.engine, self.store, DEFAULT_WORKSPACE_ID, job)
        repository = CheckpointRepository(self.engine, DEFAULT_WORKSPACE_ID, job)
        with self.engine.connect() as conn:
            source = conn.execute(sa.select(objects).join(c.messages, c.messages.c.body_object_id == objects.c.id)
                .where(c.messages.c.conversation_id == cid)).mappings().one()
        request = self.request_delete(cid)
        checkpoint = empty_checkpoint()
        checkpoint["channel_values"] = {"state": {"body": "LATE_PRIVATE"}}
        with self.assertRaises(ServiceError):
            repository.put({"configurable": {"thread_id": str(run), "checkpoint_ns": ""}}, checkpoint, {}, {})
        with self.assertRaises((ServiceError, ValueError, LookupError)):
            self.store.put(b"LATE_PRIVATE", Scope(**{key: source[key] for key in
                ("workspace_id", "mode", "branch_id", "customer_id", "purpose")}),
                Source(kind="late", reference="test"), derived_from=(source["id"],))
