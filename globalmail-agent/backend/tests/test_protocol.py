"""Real PostgreSQL deterministic barriers for Phase 3; never production state."""
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic, sleep
from unittest.mock import patch
from pathlib import Path
from uuid import UUID, uuid4

from alembic import command
from alembic.config import Config
import sqlalchemy as sa

from globalmail_agent.adapters.object_store import ObjectStore
from globalmail_agent.adapters.conversation_schema import (
    agent_slots, agent_runs, conversations, domain_events, jobs, processing_cycles,
)
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.application.conversations import ConversationService
from globalmail_agent.domain.conversation import CreateConversation, Command, AppendMessage, Takeover
from globalmail_agent.worker.jobs import JobService
from globalmail_agent.worker.leases import LeaseService
from globalmail_agent.worker.protocol import complete_protocol
from globalmail_agent.worker.leases import slot_for_update


@unittest.skipUnless(os.getenv("GLOBALMAIL_TEST_DATABASE_URL"), "requires isolated PostgreSQL")
class ProtocolFixture(unittest.TestCase):
    def setUp(self):
        url = os.environ["GLOBALMAIL_TEST_DATABASE_URL"]
        self.schema = "test_protocol_" + uuid4().hex
        self.admin = sa.create_engine(url, hide_parameters=True)
        with self.admin.begin() as connection:
            connection.execute(sa.text(f'CREATE SCHEMA "{self.schema}"'))
        self.addCleanup(self.cleanup_schema)
        self.engine = sa.create_engine(url, hide_parameters=True,
            connect_args={"options": f"-csearch_path={self.schema}"})
        self.addCleanup(self.engine.dispose)
        self.temp = tempfile.TemporaryDirectory(prefix="globalmail_protocol_")
        self.addCleanup(self.temp.cleanup)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with self.engine.begin() as connection:
            config.attributes["connection"] = connection
            command.upgrade(config, "head")
        self.service = ConversationService(self.engine, ObjectStore(Path(self.temp.name), self.engine))
        self.leases = LeaseService(self.engine, DEFAULT_WORKSPACE_ID)
        self.controls = JobService(self.engine)

    def cleanup_schema(self):
        with self.admin.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        self.admin.dispose()

    def create(self, email="customer@example.test"):
        result = self.service.create(CreateConversation(expected_version=0, sender_email=email,
                                     body="My lamp has stopped working."), uuid4().hex)
        return UUID(result["conversation_id"]), UUID(result["run_id"])

    def conversation(self, conversation_id):
        return self.service.detail(conversation_id)["conversation"]

    def count(self, table):
        with self.engine.connect() as connection:
            return connection.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()


class ProtocolTests(ProtocolFixture):
    def test_knowledge_completion_and_new_input_keep_slot_before_conversation_lock_order(self):
        cid, run_id = self.create()
        with self.engine.begin() as connection:
            connection.execute(jobs.update().where(jobs.c.run_id == run_id).values(kind="knowledge"))
        job = self.leases.claim("knowledge_lock_barrier", "knowledge")
        state = self.conversation(cid)
        acquired, resume = Event(), Event()
        holder_pid = []

        def hold_slot(connection, workspace_id, slot_key):
            slot = slot_for_update(connection, workspace_id, slot_key)
            holder_pid.append(connection.execute(sa.text("SELECT pg_backend_pid()")).scalar_one())
            acquired.set()
            if not resume.wait(5):
                raise AssertionError("Knowledge barrier was not released")
            return slot

        with patch("globalmail_agent.worker.protocol.slot_for_update", side_effect=hold_slot):
            with ThreadPoolExecutor(max_workers=2) as pool:
                completion = pool.submit(complete_protocol, self.engine, DEFAULT_WORKSPACE_ID, job)
                self.assertTrue(acquired.wait(5))
                incoming = pool.submit(self.service.append, cid, AppendMessage(
                    expected_version=state["row_version"], body="New input races with knowledge completion."), uuid4().hex)
                try:
                    deadline, blocked = monotonic() + 3, False
                    while monotonic() < deadline:
                        with self.engine.connect() as connection:
                            blocked = connection.execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                                "WHERE :pid = ANY(pg_blocking_pids(pid)))"), {"pid": holder_pid[0]}).scalar_one()
                        if blocked:
                            break
                        sleep(0.01)
                    self.assertTrue(blocked, "Incoming mutation never waited on the knowledge slot")
                    # The incoming transaction must not hold Conversation while waiting for KnowledgeSlot.
                    with self.engine.begin() as connection:
                        connection.execute(sa.select(conversations.c.id).where(conversations.c.id == cid)
                            .with_for_update(nowait=True)).one()
                finally:
                    resume.set()
                self.assertTrue(completion.result(timeout=5))
                with self.assertRaises(ServiceError) as error:
                    incoming.result(timeout=5)
                self.assertEqual(error.exception.code, "stale_version")
        latest = self.conversation(cid)
        self.service.append(cid, AppendMessage(expected_version=latest["row_version"],
            body="Customer input after refreshing the committed completion."), uuid4().hex)
        self.assertEqual(len(self.service.detail(cid)["messages"]), 2)

    def test_single_slot_concurrent_claim_and_read_only_refresh(self):
        first, _ = self.create()
        self.create("another@example.test")
        before = self.count(jobs)
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(self.leases.claim, ("worker_a", "worker_b")))
        claimed = [job for job in results if job]
        self.assertEqual(len(claimed), 1)
        for _ in range(3):
            self.service.detail(first)
            self.service.list()
        self.assertEqual(self.count(jobs), before)
        self.assertTrue(complete_protocol(self.engine, DEFAULT_WORKSPACE_ID, claimed[0]))
        next_job = self.leases.claim("worker_b")
        self.assertIsNotNone(next_job)
        self.assertGreater(next_job["slot_fence"], claimed[0]["slot_fence"])

    def test_lease_expiration_blocks_old_commit_and_requires_explicit_retry(self):
        conversation_id, run_id = self.create()
        job = self.leases.claim("old_worker")
        with self.engine.begin() as connection:
            connection.execute(agent_slots.update().where(agent_slots.c.job_id == job["id"])
                .values(lease_expires_at=sa.func.now() - sa.text("interval '1 second'")))
        self.assertFalse(self.leases.heartbeat(job["id"], "old_worker", job["slot_fence"]))
        self.assertFalse(complete_protocol(self.engine, DEFAULT_WORKSPACE_ID, job))
        self.assertEqual(self.leases.recover_expired(), [run_id])
        self.assertIsNone(self.leases.claim("new_worker"))
        conversation = self.conversation(conversation_id)
        self.assertEqual(conversation["auto_run_gate"], "manual_retry_required")
        retry_command = Command(expected_version=conversation["row_version"])
        key = uuid4().hex
        retried = self.controls.control(run_id, "retry", retry_command, key)
        self.assertEqual(self.controls.control(run_id, "retry", retry_command, key), retried)
        self.assertEqual(retried["processing_cycle_id"], str(job["cycle_id"]))
        self.assertEqual(self.count(processing_cycles), 1)
        replacement = self.leases.claim("new_worker")
        self.assertTrue(complete_protocol(self.engine, DEFAULT_WORKSPACE_ID, replacement))
        self.assertFalse(complete_protocol(self.engine, DEFAULT_WORKSPACE_ID, job))
        self.assertEqual(len(self.service.detail(conversation_id)["messages"]), 1)

    def test_stop_retry_retains_cycle_and_late_result_has_no_effect(self):
        conversation_id, run_id = self.create()
        job = self.leases.claim("stopped_worker")
        conversation = self.conversation(conversation_id)
        stopped = self.controls.control(run_id, "stop", Command(expected_version=conversation["row_version"]),
                                        uuid4().hex)
        self.assertFalse(complete_protocol(self.engine, DEFAULT_WORKSPACE_ID, job))
        self.assertIsNone(self.leases.claim("automatic_retry_forbidden"))
        retried = self.controls.control(run_id, "retry", Command(expected_version=stopped["version"]),
                                        uuid4().hex)
        self.assertEqual(retried["processing_cycle_id"], str(job["cycle_id"]))
        replacement = self.leases.claim("explicit_retry")
        self.assertTrue(complete_protocol(self.engine, DEFAULT_WORKSPACE_ID, replacement))
        with self.assertRaises(ServiceError):
            self.controls.control(UUID(retried["run_id"]), "retry",
                Command(expected_version=self.conversation(conversation_id)["row_version"]), uuid4().hex)
        self.assertEqual(self.count(processing_cycles), 1)

    def test_takeover_and_new_input_barriers(self):
        conversation_id, run_id = self.create()
        job = self.leases.claim("old_model_barrier")
        conversation = self.conversation(conversation_id)
        self.service.takeover(conversation_id, Takeover(expected_version=conversation["row_version"]), uuid4().hex)
        self.assertFalse(complete_protocol(self.engine, DEFAULT_WORKSPACE_ID, job))
        conversation = self.conversation(conversation_id)
        self.service.append(conversation_id, AppendMessage(expected_version=conversation["row_version"],
            body="This is another message during human review."), uuid4().hex)
        self.assertIsNone(self.leases.claim("must_not_reply"))
        self.assertEqual(self.controls.get(run_id)["run"]["status"], "superseded")
        self.assertEqual(len(self.service.detail(conversation_id)["messages"]), 2)
        self.assertEqual(self.count(jobs), 1)

    def test_new_message_supersedes_running_and_queues_latest_context(self):
        conversation_id, _ = self.create()
        old = self.leases.claim("old_input_barrier")
        conversation = self.conversation(conversation_id)
        appended = self.service.append(conversation_id,
            AppendMessage(expected_version=conversation["row_version"], body="Additional information."), uuid4().hex)
        self.assertFalse(complete_protocol(self.engine, DEFAULT_WORKSPACE_ID, old))
        replacement = self.leases.claim("latest_context")
        self.assertEqual(str(replacement["run_id"]), appended["run_id"])
        self.assertTrue(complete_protocol(self.engine, DEFAULT_WORKSPACE_ID, replacement))
        with self.engine.connect() as connection:
            self.assertEqual(set(connection.execute(sa.select(domain_events.c.status)).scalars()), {"processed"})
        self.assertEqual(len(self.service.detail(conversation_id)["messages"]), 2)

    def test_restart_interrupts_active_but_preserves_unclaimed_queue(self):
        conversation_id, run_id = self.create()
        active = self.leases.claim("process_that_exited")
        _, queued_id = self.create("queued@example.test")
        restarted = LeaseService(self.engine, DEFAULT_WORKSPACE_ID)
        self.assertEqual(restarted.recover_expired(restart=True), [run_id])
        self.assertFalse(complete_protocol(self.engine, DEFAULT_WORKSPACE_ID, active))
        self.assertEqual(self.controls.get(queued_id)["run"]["status"], "queued")
        next_job = restarted.claim("new_process")
        self.assertEqual(next_job["run_id"], queued_id)
        self.assertTrue(complete_protocol(self.engine, DEFAULT_WORKSPACE_ID, next_job))
        self.assertEqual(self.conversation(conversation_id)["auto_run_gate"], "manual_retry_required")

    def test_knowledge_slot_does_not_occupy_agent_slot(self):
        self.create()
        _, other_run = self.create("knowledge-protocol@example.test")
        with self.engine.begin() as connection:
            connection.execute(jobs.update().where(jobs.c.run_id == other_run).values(kind="knowledge"))
        agent_job = self.leases.claim("agent_owner")
        knowledge_job = self.leases.claim("knowledge_owner", "knowledge")
        self.assertIsNotNone(agent_job)
        self.assertIsNotNone(knowledge_job)
        self.assertNotEqual(agent_job["id"], knowledge_job["id"])
        self.assertTrue(self.leases.heartbeat(knowledge_job["id"], "knowledge_owner",
                                           knowledge_job["slot_fence"], "knowledge"))
        self.assertTrue(complete_protocol(self.engine, DEFAULT_WORKSPACE_ID, knowledge_job))
        self.assertTrue(complete_protocol(self.engine, DEFAULT_WORKSPACE_ID, agent_job))
