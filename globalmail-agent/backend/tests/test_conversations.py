"""Real PostgreSQL conversation/replay/review tests with independent schema and files."""
import os
import tempfile
import unittest
from pathlib import Path
from uuid import UUID, uuid4
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from globalmail_agent.adapters.object_store import ObjectStore
from globalmail_agent.adapters.conversation_schema import (
    conversations, messages, jobs, case_facts, case_issues, human_reviews, ui_events)
from globalmail_agent.adapters.schema import content_dependencies, objects
from globalmail_agent.application.conversations import ConversationService
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.application.event_store import append_ui_event, read_events
from globalmail_agent.domain.conversation import (
    CreateConversation, AppendMessage, ImportCase, Command, Takeover, ReviewDraft, HumanReply, Close)
from globalmail_agent.api.conversations import EXAMPLE
from globalmail_agent.api.events import sse_event
from globalmail_agent.main import create_app
from globalmail_agent.settings import Settings
from globalmail_agent.worker.leases import LeaseService
from globalmail_agent.worker.protocol import complete_protocol


@unittest.skipUnless(os.getenv("GLOBALMAIL_TEST_DATABASE_URL"), "requires isolated PostgreSQL")
class ConversationTests(unittest.TestCase):
    def setUp(self):
        url = os.environ["GLOBALMAIL_TEST_DATABASE_URL"]
        self.schema = "test_conversation_" + uuid4().hex
        self.admin = sa.create_engine(url, hide_parameters=True)
        with self.admin.begin() as conn:
            conn.execute(sa.text(f'CREATE SCHEMA "{self.schema}"'))
        self.addCleanup(self.cleanup_schema)
        self.engine = sa.create_engine(url, hide_parameters=True,
            connect_args={"options": f"-csearch_path={self.schema}"})
        self.addCleanup(self.engine.dispose)
        self.temp = tempfile.TemporaryDirectory(prefix="globalmail_conversation_")
        self.addCleanup(self.temp.cleanup)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with self.engine.begin() as conn:
            config.attributes["connection"] = conn
            command.upgrade(config, "head")
        self.store = ObjectStore(Path(self.temp.name), self.engine)
        self.service = ConversationService(self.engine, self.store)
        self.leases = LeaseService(self.engine, DEFAULT_WORKSPACE_ID)

    def cleanup_schema(self):
        with self.admin.begin() as conn:
            conn.execute(sa.text(f'DROP SCHEMA "{self.schema}" CASCADE'))
        self.admin.dispose()

    def create(self, email="customer@example.test", body="My lamp stopped responding."):
        result = self.service.create(CreateConversation(expected_version=0, sender_email=email, body=body), uuid4().hex)
        return UUID(result["conversation_id"])

    def detail(self, cid):
        return self.service.detail(cid)

    def count(self, table):
        with self.engine.connect() as conn:
            return conn.execute(sa.select(sa.func.count()).select_from(table)).scalar_one()

    def finish(self):
        job = self.leases.claim("controlled_worker")
        self.assertIsNotNone(job)
        self.assertTrue(complete_protocol(self.engine, DEFAULT_WORKSPACE_ID, job))

    def takeover(self, cid):
        detail = self.detail(cid)
        self.service.takeover(cid, Takeover(expected_version=detail["conversation"]["row_version"]), uuid4().hex)
        return self.detail(cid)

    def test_manual_identity_grouping_preserves_plus_and_dots(self):
        first = self.create(" A.b+tag@Example.TEST ")
        self.assertEqual(self.create("A.b+tag@example.test"), first)
        self.assertNotEqual(self.create("Ab+tag@example.test"), first)
        self.assertNotEqual(self.create("A.b@example.test"), first)
        self.assertEqual(len(self.detail(first)["messages"]), 2)
        self.assertEqual(self.detail(first)["conversation"]["sender_key"], "A.b+tag@example.test")

    def test_request_replay_same_key_conflict_and_source_duplicate(self):
        cmd = CreateConversation(expected_version=0, sender_email="first@example.test", body="First body")
        key = uuid4().hex
        result = self.service.create(cmd, key)
        self.assertEqual(result, self.service.create(cmd, key))
        with self.assertRaises(ServiceError):
            self.service.create(cmd.model_copy(update={"body": "Changed"}), key)
        self.assertEqual(self.count(messages), 1)
        cid = UUID(result["conversation_id"])
        command_ = AppendMessage(expected_version=result["version"], body="More", source_message_id="source-2")
        self.service.append(cid, command_, uuid4().hex)
        latest = self.detail(cid)["conversation"]["row_version"]
        self.service.append(cid, command_.model_copy(update={"expected_version": latest}), uuid4().hex)
        self.assertEqual(self.count(messages), 2)
        self.assertEqual(self.count(jobs), 2)

    def test_input_before_human_reply_conflicts_and_preserves_draft(self):
        cid = self.create()
        state = self.takeover(cid)
        review = state["review"]
        self.service.save_review(review["id"], ReviewDraft(expected_version=review["version"],
            expected_input_revision=state["conversation"]["input_revision"],
            draft="Please test a different socket.", note="Check the newer message."), uuid4().hex)
        state = self.detail(cid)
        form = HumanReply(expected_version=state["conversation"]["row_version"],
            expected_input_revision=state["conversation"]["input_revision"], body="Old reply")
        self.service.append(cid, AppendMessage(expected_version=form.expected_version, body="New information."), uuid4().hex)
        with self.assertRaises(ServiceError):
            self.service.human_reply(cid, form, uuid4().hex)
        state = self.detail(cid)
        self.assertEqual(state["review"]["draft"], "Please test a different socket.")
        self.assertEqual(state["conversation"]["processing_owner"], "human_review")
        self.assertEqual(self.count(messages), 2)
        self.assertEqual(self.count(jobs), 1)
        with self.assertRaises(ServiceError) as error:
            self.service.human_reply(cid, form.model_copy(update={"expected_version": state["conversation"]["row_version"]}), uuid4().hex)
        self.assertEqual(error.exception.code, "stale_input_revision")

    def test_reply_before_next_input_waits_and_next_local_sequence_resumes(self):
        cid = self.create()
        state = self.takeover(cid)
        self.service.human_reply(cid, HumanReply(expected_version=state["conversation"]["row_version"],
            expected_input_revision=state["conversation"]["input_revision"], body="Try another socket.", note="Local context only."), uuid4().hex)
        state = self.detail(cid)
        self.assertEqual(state["conversation"]["processing_owner"], "human_wait_customer")
        self.assertEqual(self.count(jobs), 1)
        self.assertEqual(state["messages"][-1]["sender"], "simulated_human")
        self.assertEqual(state["human_history"][0]["note"], "Local context only.")
        self.service.append(cid, AppendMessage(expected_version=state["conversation"]["row_version"], body="It still fails."), uuid4().hex)
        state = self.detail(cid)
        self.assertEqual(state["conversation"]["processing_owner"], "agent")
        self.assertEqual(state["conversation"]["auto_run_gate"], "open")
        self.assertEqual(self.count(jobs), 2)
        self.assertEqual(len(state["messages"]), 3)

    def test_close_revokes_and_new_customer_message_only_registers(self):
        cid = self.create()
        state = self.detail(cid)
        self.service.close(cid, Close(expected_version=state["conversation"]["row_version"], note="Confirmed by customer."), uuid4().hex)
        state = self.detail(cid)
        self.assertEqual(state["conversation"]["lifecycle"], "resolved")
        self.assertEqual(state["runs"][0]["status"], "cancelled")
        self.service.append(cid, AppendMessage(expected_version=state["conversation"]["row_version"], body="Another question."), uuid4().hex)
        self.assertEqual(self.detail(cid)["conversation"]["lifecycle"], "resolved")
        self.assertEqual(len(self.detail(cid)["runs"]), len(state["runs"]))

    def test_history_real_prefix_group_id_and_comparison_isolation(self):
        payload = {**EXAMPLE, "group_id": "same-group", "sender_key": "unverified-key"}
        cmd = ImportCase.model_validate(payload)
        result = self.service.import_case(cmd, uuid4().hex)
        cid = UUID(result["conversation_id"])
        duplicate = self.service.import_case(cmd, uuid4().hex)
        self.assertEqual(duplicate["conversation_id"], result["conversation_id"])
        other = self.service.import_case(cmd.model_copy(update={"source_conversation_id": "different-source"}), uuid4().hex)
        self.assertNotEqual(other["conversation_id"], result["conversation_id"])
        state = self.detail(cid)
        self.assertFalse(state["conversation"]["identity_verified"])
        self.assertEqual(len(state["messages"]), 1)
        self.assertNotIn("DEMO-1001", str(state))
        initial_issue = state["issues"][0]["id"]
        state = self.takeover(cid)
        self.service.human_reply(cid, HumanReply(expected_version=state["conversation"]["row_version"],
            expected_input_revision=state["conversation"]["input_revision"], body="AI comparison must not carry into history."), uuid4().hex)
        state = self.detail(cid)
        self.assertEqual(len(state["messages"]), 1)
        self.assertEqual(len(state["comparisons"]), 1)
        self.service.next(cid, Command(expected_version=state["conversation"]["row_version"]), uuid4().hex)
        state = self.detail(cid)
        self.assertEqual([m["sender"] for m in state["messages"]], ["customer", "historical_staff", "customer"])
        self.assertEqual(state["issues"][0]["id"], initial_issue)
        self.assertEqual(len(state["facts"]), 3)
        self.assertTrue(all("AI comparison" not in f["value"] for f in state["facts"]))
        self.assertEqual(state["replay"]["as_of"].isoformat(), "2026-10-02T08:00:00+00:00")
        self.assertEqual(state["conversation"]["lifecycle"], "open")

    def test_history_cannot_advance_active_run_and_import_validates_schema(self):
        cid = UUID(self.service.import_case(ImportCase.model_validate(EXAMPLE), uuid4().hex)["conversation_id"])
        with self.assertRaises(ServiceError):
            self.service.next(cid, Command(expected_version=self.detail(cid)["conversation"]["row_version"]), uuid4().hex)
        self.finish()
        self.service.next(cid, Command(expected_version=self.detail(cid)["conversation"]["row_version"]), uuid4().hex)
        for patch in ({"future_events": []}, {"reference_answers": []}, {"path": "../secret"}, {"identity_verified": True}):
            with self.assertRaises(ValueError):
                ImportCase.model_validate({**EXAMPLE, **patch})
        with self.assertRaises(ServiceError):
            duplicate = {**EXAMPLE, "messages": [EXAMPLE["messages"][0], EXAMPLE["messages"][0]]}
            self.service.import_case(ImportCase.model_validate(duplicate), uuid4().hex)

    def test_scoped_foreign_keys_and_transaction_failure_cleanup(self):
        first, second = self.create(), self.create("second@example.test")
        original = self.detail(first)["messages"][0]
        other = self.detail(second)["conversation"]
        with self.assertRaises(IntegrityError):
            with self.engine.begin() as conn:
                conn.execute(messages.insert().values(id=uuid4(),
                    **{k: other[k] for k in ("workspace_id", "mode", "branch_id", "customer_id", "purpose")},
                    conversation_id=second, seq=99, received_seq=99, source_ref="invalid", source_message_id="invalid",
                    sender="customer", body_object_id=original["body_object_id"], sent_at=sa.func.now()))
        before = set(Path(self.temp.name).iterdir())
        original_accept = self.service.accept
        self.service.accept = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("controlled_failure"))
        with self.assertRaises(RuntimeError):
            self.service.append(first, AppendMessage(expected_version=self.detail(first)["conversation"]["row_version"], body="Rolled back"), uuid4().hex)
        self.service.accept = original_accept
        self.assertEqual(before, set(Path(self.temp.name).iterdir()))
        self.assertEqual(self.count(messages), 2)
        self.assertGreater(self.count(content_dependencies), 0)

    def test_event_commit_order_safety_and_after_cursor_are_read_only(self):
        cid = self.create()
        before = self.count(jobs)
        with self.engine.begin() as conn:
            with self.assertRaises(ValueError):
                append_ui_event(conn, cid, "invalid", {"body": "secret"})
        with self.engine.connect() as conn:
            events = read_events(conn, cid, DEFAULT_WORKSPACE_ID, 0)
            self.assertEqual([e["seq"] for e in events], list(range(1, len(events) + 1)))
            self.assertEqual(read_events(conn, cid, DEFAULT_WORKSPACE_ID, events[-1]["seq"]), [])
            text = sse_event(events[0])
            self.assertIn("event: update", text)
            self.assertNotIn("My lamp", text)
        self.assertEqual(self.count(jobs), before)

    def test_api_errors_and_controls_have_safe_envelopes(self):
        headers = {"Origin": "http://127.0.0.1:15173", "Idempotency-Key": uuid4().hex}
        with TestClient(create_app(Settings(object_root=Path(self.temp.name)), engine=self.engine, start_worker=False),
                        base_url="http://localhost") as client:
            result = client.post("/api/v1/conversations", json={"expected_version": 0,
                "sender_email": "api@example.test", "body": "<script>text only</script>"}, headers=headers)
            self.assertEqual(result.status_code, 202)
            cid = result.json()["data"]["conversation_id"]
            self.assertEqual(client.get("/api/v1/conversations/" + cid).json()["data"]["messages"][0]["body"], "<script>text only</script>")
            self.assertEqual(client.post("/api/v1/imports", json={**EXAMPLE, "reference_answers": []}, headers=headers).status_code, 422)
            self.assertEqual(client.get("/api/v1/conversations/" + cid + "/events?after_seq=999").status_code, 409)
            self.assertEqual(client.get("/api/v1/conversations/" + cid + "/events", headers={"Last-Event-ID": "bad"}).status_code, 422)
            self.assertEqual(client.get("/api/v1/imports/example").status_code, 200)
