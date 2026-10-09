"""Human reply/business notification races stop at the persisted human barrier."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch
from uuid import uuid4
import sqlalchemy as sa
from agent_fixture import AgentFixture, ScriptedModel, understanding, terminal, call
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import jobs, domain_events
from globalmail_agent.application.conversation_lock import lock_conversation, ServiceError
from globalmail_agent.application.event_store import record_business_notification
from globalmail_agent.domain.conversation import HumanReply


class AgentHumanTests(AgentFixture):
    def test_reply_notification_commit_orders_preserve_pause_until_new_customer_input(self):
        for first in ("notification", "human_reply"):
            with self.subTest(first=first):
                cid, old_run = self.create_mail(email=first + "@example.test")
                model = ScriptedModel(understanding, {"calls": [call("request_human_review", {
                    "reason": "cannot_decide", "summary": "Need human inspection.", "gaps": ["Unknown cause."], "draft": ""})]})
                output, _ = self.execute(model)
                self.assertEqual(output.get("outcome"), "handoff", output)
                state = self.conversation(cid)
                form = HumanReply(expected_version=state["row_version"], expected_input_revision=state["input_revision"],
                    body="Human decision applied.", note="LATEST_HUMAN_DECISION_SENTINEL")
                acquired, release, second_started = Event(), Event(), Event()
                def notification(block=False):
                    if not block:
                        second_started.set()
                    with self.engine.begin() as conn:
                        conv = lock_conversation(conn, cid, self.service.workspace_id)
                        if block:
                            acquired.set()
                            if not release.wait(10):
                                raise AssertionError("Notification transaction barrier was not released")
                        return record_business_notification(conn, conv, "race-" + first)
                original_lock = self.service.lock
                def human_lock(*args, **kwargs):
                    conv = original_lock(*args, **kwargs)
                    acquired.set()
                    if not release.wait(10):
                        raise AssertionError("Human reply transaction barrier was not released")
                    return conv
                def human_reply():
                    second_started.set()
                    return self.service.human_reply(cid, form, uuid4().hex)
                with ThreadPoolExecutor(max_workers=2) as pool:
                    if first == "notification":
                        earlier = pool.submit(notification, True)
                        self.assertTrue(acquired.wait(10))
                        later = pool.submit(human_reply)
                        self.assertTrue(second_started.wait(10))
                        release.set()
                        event = earlier.result(timeout=10)
                        with self.assertRaises(ServiceError):
                            later.result(timeout=10)
                        refreshed = self.conversation(cid)
                        self.service.human_reply(cid, form.model_copy(update={"expected_version": refreshed["row_version"],
                            "expected_input_revision": refreshed["input_revision"]}), uuid4().hex)
                    else:
                        with patch.object(self.service, "lock", side_effect=human_lock):
                            earlier = pool.submit(human_reply)
                            self.assertTrue(acquired.wait(10))
                            later = pool.submit(notification)
                            self.assertTrue(second_started.wait(10))
                            release.set()
                            earlier.result(timeout=10)
                            event = later.result(timeout=10)
                self.assertEqual(event["status"], "suppressed_by_human")
                self.assertEqual(self.conversation(cid)["processing_owner"], "human_wait_customer")
                self.assertIsNone(self.leases.claim("business_is_not_resume"))
                self.assertEqual(self.outbound(cid), [])
                before = self.count(jobs)
                self.append_mail(cid, "Customer input accepted after the human reply barrier.")
                self.assertEqual(self.count(jobs), before + 1)
                resumed = ScriptedModel(understanding, terminal("We received the new information."))
                output, current = self.execute(resumed)
                self.assertEqual(output.get("outcome"), "reply_and_wait", output)
                self.assertNotEqual(current["run_id"], old_run)
                self.assertIn("LATEST_HUMAN_DECISION_SENTINEL", str(resumed.requests))
                with self.engine.connect() as conn:
                    traces = list(conn.execute(sa.select(a.trace_correlations.c.trace_id).where(
                        a.trace_correlations.c.run_id.in_([old_run, current["run_id"]]))).scalars())
                self.assertEqual(len(set(traces)), 2)
                self.assertEqual(len(self.outbound(cid)), 1)
