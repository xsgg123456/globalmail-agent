"""Human barrier permutations for the internal Phase 3 event transport."""
from uuid import uuid4
import sqlalchemy as sa

from globalmail_agent.adapters.conversation_schema import domain_events, jobs
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.application.event_store import record_business_notification
from globalmail_agent.domain.conversation import AppendMessage, Close, HumanReply, ReviewDraft, Takeover
from test_protocol import ProtocolFixture


class HumanEventTests(ProtocolFixture):
    def test_closed_conversation_rejects_takeover_and_new_input_reopens_without_review(self):
        cid, _ = self.create()
        state = self.conversation(cid)
        self.service.close(cid, Close(expected_version=state["row_version"]), uuid4().hex)
        closed = self.service.detail(cid)
        with self.assertRaises(ServiceError) as error:
            self.service.takeover(cid, Takeover(expected_version=closed["conversation"]["row_version"]), uuid4().hex)
        self.assertEqual(error.exception.code, "conversation_not_open")
        self.assertEqual(self.service.detail(cid)["conversation"], closed["conversation"])
        self.assertIsNone(self.service.detail(cid)["review"])
        self.service.append(cid, AppendMessage(expected_version=closed["conversation"]["row_version"],
            body="Customer returns after closure."), uuid4().hex)
        reopened = self.service.detail(cid)
        self.assertEqual(reopened["conversation"]["lifecycle"], "open")
        self.assertEqual(reopened["conversation"]["processing_owner"], "agent")
        self.assertIsNone(reopened["review"])
        self.assertIsNotNone(self.leases.claim("reopened_without_stale_review"))

    def test_saving_stale_draft_and_reloading_does_not_acknowledge_new_input(self):
        cid, _ = self.create()
        state = self.conversation(cid)
        self.service.takeover(cid, Takeover(expected_version=state["row_version"]), uuid4().hex)
        original = self.service.detail(cid)
        self.service.append(cid, AppendMessage(expected_version=original["conversation"]["row_version"],
            body="New information invalidates the old draft."), uuid4().hex)
        self.service.save_review(original["review"]["id"], ReviewDraft(
            expected_version=original["review"]["version"],
            expected_input_revision=original["conversation"]["input_revision"],
            draft="Reply written before new input."), uuid4().hex)
        reloaded = self.service.detail(cid)
        self.assertEqual(reloaded["review"]["draft"], "Reply written before new input.")
        self.assertLess(reloaded["review"]["input_revision"], reloaded["conversation"]["input_revision"])
        with self.assertRaises(ServiceError) as error:
            self.service.human_reply(cid, HumanReply(expected_version=reloaded["conversation"]["row_version"],
                expected_input_revision=reloaded["review"]["input_revision"],
                body=reloaded["review"]["draft"]), uuid4().hex)
        self.assertEqual(error.exception.code, "stale_input_revision")
        self.assertEqual(len(self.service.detail(cid)["messages"]), 2)
        self.service.save_review(reloaded["review"]["id"], ReviewDraft(
            expected_version=reloaded["review"]["version"],
            expected_input_revision=reloaded["conversation"]["input_revision"],
            draft="Reply after explicitly reviewing the new message."), uuid4().hex)
        acknowledged = self.service.detail(cid)
        self.assertEqual(acknowledged["review"]["input_revision"], acknowledged["conversation"]["input_revision"])

    def test_business_notification_before_reply_conflicts_until_rechecked(self):
        cid, _ = self.create()
        state = self.conversation(cid)
        self.service.takeover(cid, Takeover(expected_version=state["row_version"]), uuid4().hex)
        state = self.conversation(cid)
        old_form = HumanReply(expected_version=state["row_version"],
                             expected_input_revision=state["input_revision"], body="We will follow up.")
        with self.engine.begin() as connection:
            event = record_business_notification(connection, state, "business-before-reply")
        self.assertEqual(event["status"], "suppressed_by_human")
        with self.assertRaises(ServiceError):
            self.service.human_reply(cid, old_form, uuid4().hex)
        updated = self.conversation(cid)
        self.service.human_reply(cid, old_form.model_copy(update={
            "expected_version": updated["row_version"], "expected_input_revision": updated["input_revision"]}), uuid4().hex)
        self.assertEqual(self.conversation(cid)["processing_owner"], "human_wait_customer")
        self.assertEqual(self.count(jobs), 1)
        self.assertIsNone(self.leases.claim("must_wait_for_customer"))

    def test_reply_before_business_notification_does_not_resume_and_duplicates_do_not_queue(self):
        cid, _ = self.create()
        state = self.conversation(cid)
        self.service.takeover(cid, Takeover(expected_version=state["row_version"]), uuid4().hex)
        state = self.conversation(cid)
        self.service.human_reply(cid, HumanReply(expected_version=state["row_version"],
            expected_input_revision=state["input_revision"], body="Please reply when ready."), uuid4().hex)
        state = self.conversation(cid)
        with self.engine.begin() as connection:
            first = record_business_notification(connection, state, "business-after-reply")
        revision = self.conversation(cid)["input_revision"]
        with self.engine.begin() as connection:
            repeated = record_business_notification(connection, state, "business-after-reply")
        self.assertEqual(first["id"], repeated["id"])
        self.assertEqual(first["status"], "suppressed_by_human")
        self.assertEqual(self.conversation(cid)["input_revision"], revision)
        self.assertEqual(self.count(jobs), 1)
        self.assertIsNone(self.leases.claim("business_must_not_resume"))
        updated = self.conversation(cid)
        self.service.append(cid, AppendMessage(expected_version=updated["row_version"],
                             body="Customer reply after the human barrier."), uuid4().hex)
        self.assertEqual(self.conversation(cid)["processing_owner"], "agent")
        self.assertEqual(self.count(jobs), 2)
        self.assertIsNotNone(self.leases.claim("new_customer_input"))
        with self.engine.connect() as connection:
            saved = connection.execute(sa.select(domain_events).where(
                domain_events.c.source == "business_notification")).mappings().one()
        self.assertEqual(saved["status"], "suppressed_by_human")
