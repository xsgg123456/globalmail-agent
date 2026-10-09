"""Source-backed candidate revisions never acquire business authority or invalidate input."""
from uuid import uuid4
from agent_fixture import AgentFixture, understanding, draft, call
from globalmail_agent.adapters.conversation_schema import case_facts, case_revisions
from globalmail_agent.application.commit_outcome import commit_outcome


class AgentMemoryTests(AgentFixture):
    def test_verified_message_candidate_survives_new_run_without_self_superseding(self):
        cid, rid = self.create_mail("I already tried pairing without success.")
        job, context, _, gateway = self.components()
        before = self.conversation(cid)
        message = context.payload["messages"][0]
        fact = {"key": "failed_steps", "value": "pairing failed", "kind": "customer_report", "sources": [
            {"message_id": message["message_id"], "quote": "already tried pairing without success"}]}
        _, updated = gateway.call(call("update_case_state", {"facts": [fact],
            "expected_case_revision": before["case_revision"]}))
        self.assertEqual(updated["status"], "ok")
        current = self.conversation(cid)
        self.assertEqual(current["input_revision"], before["input_revision"])
        self.assertEqual(current["authority_epoch"], before["authority_epoch"])
        self.assertEqual(current["case_revision"], before["case_revision"] + 1)
        self.approve_fixture_draft(context, job, draft())
        output = commit_outcome(self.engine, self.store, context, job, understanding([]), {"kind": "reply", "data": draft()})
        self.assertEqual(output["outcome"], "reply_and_wait")
        self.append_mail(cid, "The same symptom is still present.")
        next_job, next_context, _, _ = self.components()
        self.assertNotEqual(next_job["run_id"], rid)
        self.assertIn("pairing failed", str(next_context.payload["case_facts"]))
        self.assertIn(message["message_id"], str(next_context.payload["case_facts"]))

    def test_stale_case_revision_conflicts_and_forged_source_cannot_change_memory(self):
        cid, _ = self.create_mail("Original customer report.")
        job, context, _, gateway = self.components()
        state = self.conversation(cid)
        facts_before, revisions_before = self.count(case_facts), self.count(case_revisions)
        _, output = gateway.call(call("update_case_state", {"facts": [],
            "expected_case_revision": state["case_revision"] + 1}))
        self.assertEqual(output["status"], "conflict")
        self.assertEqual(output["reason_code"], "stale_case_revision")
        spoof = {"key": "refund", "value": "approved", "kind": "human_decision", "sources": [
            {"message_id": context.payload["messages"][0]["message_id"], "quote": "Original customer report."}]}
        self.assert_error("human_source_invalid", lambda: gateway.call(call("update_case_state", {
            "facts": [spoof], "expected_case_revision": state["case_revision"]})))
        self.assertEqual(self.count(case_facts), facts_before)
        self.assertEqual(self.count(case_revisions), revisions_before)
        self.assertEqual(self.conversation(cid)["case_revision"], state["case_revision"])
        self.assertEqual(self.outbound(cid), [])

    def test_model_cannot_use_candidate_update_to_write_tool_fact_or_processing_rights(self):
        cid, _ = self.create_mail("The customer requests a refund.")
        _, context, _, gateway = self.components()
        state = self.conversation(cid)
        request = {"facts": [{"key": "refund_status", "value": "succeeded", "kind": "tool_fact", "sources": [
            {"message_id": context.payload["messages"][0]["message_id"], "quote": "refund"}]}],
            "expected_case_revision": state["case_revision"]}
        self.assert_error("tool_parameters_invalid", lambda: gateway.call(call("update_case_state", request)))
        self.assert_error("tool_parameters_invalid", lambda: gateway.call(call("update_case_state", {
            "facts": [], "expected_case_revision": state["case_revision"], "processing_owner": "agent"})))
        self.assertEqual(self.conversation(cid)["case_revision"], state["case_revision"])
