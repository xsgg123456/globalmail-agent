"""Real PG text-cycle effects. Synthetic model outputs verify protocol, not quality."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4
from fastapi.testclient import TestClient
from agent_fixture import AgentFixture, ScriptedModel, understanding, terminal, draft, call
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import human_reviews, jobs
from globalmail_agent.application.commit_outcome import commit_outcome
from globalmail_agent.domain.conversation import Command, HumanReply, Takeover, ImportCase
from globalmail_agent.api.conversations import EXAMPLE
from globalmail_agent.main import create_app
from globalmail_agent.settings import Settings


class AgentOutcomeTests(AgentFixture):
    def test_missing_order_full_graph_sends_one_mail_and_persists_process_records(self):
        cid, rid = self.create_mail()
        model = ScriptedModel(understanding, terminal())
        output, job = self.execute(model)
        self.assertEqual(output["outcome"], "reply_and_wait", output)
        self.assertEqual(len(self.outbound(cid)), 1)
        state = self.conversation(cid)
        self.assertEqual(state["lifecycle"], "open")
        self.assertEqual(state["scheduling_state"], "waiting_customer")
        self.assertEqual(self.controls.get(rid)["run"]["status"], "completed")
        self.assertEqual(self.budget_row(job)["model_requests"], 3)
        self.assertEqual(self.count(a.understanding_results), 1)
        self.assertEqual(self.count(a.tool_commands), 1)
        self.assertEqual(self.count(a.reply_artifacts), 1)
        self.assertEqual(self.count(a.trace_correlations), 1)
        self.assertEqual(self.count(a.wait_conditions), 1)
        self.assertEqual(self.count(human_reviews), 0)

    def test_same_terminal_and_reexecuted_job_read_original_receipt(self):
        cid, _ = self.create_mail()
        job, context, _, _ = self.components()
        value = understanding([])
        proposal = {"kind": "reply", "data": draft()}
        self.approve_fixture_draft(context, job, proposal["data"])
        first = commit_outcome(self.engine, self.store, context, job, value, proposal)
        repeated = commit_outcome(self.engine, self.store, context, job, value, proposal)
        self.assertEqual(str(repeated.get("id", repeated.get("artifact_id"))), first["artifact_id"])
        model = ScriptedModel()
        resumed, _ = self.execute(model, job)
        self.assertEqual(str(resumed.get("id", resumed.get("artifact_id"))), first["artifact_id"])
        self.assertEqual(model.requests, [])
        self.assertEqual(len(self.outbound(cid)), 1)
        self.assertEqual(self.count(a.reply_artifacts), 1)

    def test_commit_response_loss_and_restart_do_not_recreate_effect(self):
        cid, rid = self.create_mail()
        from globalmail_agent.application.commit_outcome import commit_outcome as real_commit
        def lost_response(*args, **kwargs):
            real_commit(*args, **kwargs)
            raise RuntimeError("Explicit post-commit process failure")
        model = ScriptedModel(understanding, terminal())
        with patch("globalmail_agent.worker.agent_runner.commit_outcome", side_effect=lost_response):
            _, job = self.execute(model)
        self.assertEqual(self.controls.get(rid)["run"]["status"], "completed")
        self.assertEqual(self.leases.recover_expired(restart=True), [])
        self.assertIsNone(self.leases.claim("restart_must_not_replay"))
        repeated, _ = self.execute(ScriptedModel(), job)
        self.assertNotIn("error_code", repeated)
        self.assertEqual(len(self.outbound(cid)), 1)
        self.assertEqual(self.count(a.reply_artifacts), 1)
        state = self.conversation(cid)
        self.assert_error("retry_not_allowed", lambda: self.controls.control(rid, "retry",
            Command(expected_version=state["row_version"]), uuid4().hex))

    def test_handoff_new_mail_is_suppressed_and_human_reply_next_mail_starts_new_run(self):
        cid, first = self.create_mail()
        handoff = {"reason": "no_applicable_evidence", "summary": "No verified model-specific next step.",
            "gaps": ["Need an applicable troubleshooting document."], "draft": "Unsent draft."}
        model = ScriptedModel(understanding, {"calls": [call("request_human_review", handoff)]})
        output, _ = self.execute(model)
        self.assertEqual(output["outcome"], "handoff", output)
        self.assertEqual(self.outbound(cid), [])
        queued = self.count(jobs)
        self.append_mail(cid, "One more detail while awaiting human review.")
        self.assertEqual(self.count(jobs), queued)
        self.assertIsNone(self.leases.claim("no_autonomous_human_review"))
        state = self.conversation(cid)
        self.service.human_reply(cid, HumanReply(expected_version=state["row_version"],
            expected_input_revision=state["input_revision"], body="Human confirmed the serial number.",
            note="HUMAN_NOTE_SENTINEL: customer already tried pairing."), uuid4().hex)
        self.assertEqual(self.count(jobs), queued)
        self.assertIsNone(self.leases.claim("human_reply_is_not_a_trigger"))
        new = self.append_mail(cid, "Thanks, the replacement battery also did not help.")
        next_model = ScriptedModel(understanding, terminal("Please describe the new symptoms."))
        output, job = self.execute(next_model)
        self.assertNotEqual(job["run_id"], first)
        self.assertEqual(str(job["run_id"]), new["run_id"])
        self.assertEqual(output["outcome"], "reply_and_wait", output)
        payload = json.loads(next_model.requests[0]["messages"][-1]["content"])
        self.assertIn("HUMAN_NOTE_SENTINEL", str(payload["human_notes"]))
        self.assertIn("Human confirmed the serial number.", str(payload["messages"]))
        self.assertEqual(len(self.outbound(cid)), 1)

    def test_safety_risk_handoffs_without_decision_request(self):
        cid, rid = self.create_mail("The plug sparked and I felt an electric shock.")
        def risk(messages):
            payload = json.loads(messages[-1]["content"])
            source = payload["messages"][-1]
            return understanding(messages, risk_flags=[{"kind": "electric_shock", "sources": [
                {"message_id": source["message_id"], "quote": "electric shock"}]}])
        model = ScriptedModel(risk)
        output, job = self.execute(model)
        self.assertEqual(output["outcome"], "handoff", output)
        self.assertEqual(len(model.requests), 1)
        self.assertEqual(self.budget_row(job)["model_requests"], 1)
        self.assertEqual(self.count(a.tool_commands), 0)
        self.assertEqual(self.count(human_reviews), 1)
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.controls.get(rid)["run"]["status"], "handed_off")

    def test_next_input_reads_prior_simulated_outbound_and_customer_failure(self):
        cid, _ = self.create_mail()
        self.execute(ScriptedModel(understanding, terminal("Please share your order number.")))
        self.append_mail(cid, "The earlier pairing attempt failed. My order is ORDER-NEW.")
        model = ScriptedModel(understanding, terminal("Which item in the order is affected?"))
        output, _ = self.execute(model)
        self.assertEqual(output["outcome"], "reply_and_wait", output)
        payload = json.loads(model.requests[0]["messages"][-1]["content"])
        self.assertEqual([row["sender"] for row in payload["messages"]], ["customer", "simulated_agent", "customer"])
        self.assertIn("earlier pairing attempt failed", payload["messages"][-1]["body"])
        self.assertEqual(len(self.outbound(cid)), 2)

    def test_historical_next_context_ignores_ai_human_comparison_and_future_messages(self):
        package = deepcopy(EXAMPLE)
        package["messages"].extend([
            {"source_message_id": "staff-future", "sender": "historical_staff", "sent_at": "2026-10-03T08:00:00Z",
                "subject": "", "body": "FUTURE_STAFF_SENTINEL"},
            {"source_message_id": "mail-future", "sender": "customer", "sent_at": "2026-10-04T08:00:00Z",
                "subject": "", "body": "FUTURE_CUSTOMER_SENTINEL"}])
        cid = UUID(self.service.import_case(ImportCase.model_validate(package), uuid4().hex)["conversation_id"])
        first = ScriptedModel(understanding, terminal("AI_COMPARISON_SENTINEL"))
        output, _ = self.execute(first)
        self.assertEqual(output["outcome"], "historical_comparison", output)
        state = self.conversation(cid)
        self.service.takeover(cid, Takeover(expected_version=state["row_version"]), uuid4().hex)
        state = self.conversation(cid)
        self.service.human_reply(cid, HumanReply(expected_version=state["row_version"],
            expected_input_revision=state["input_revision"], body="HUMAN_COMPARISON_SENTINEL",
            note="FINAL_NOTE_SENTINEL"), uuid4().hex)
        self.service.next(cid, Command(expected_version=self.conversation(cid)["row_version"]), uuid4().hex)
        model = ScriptedModel(understanding, terminal("Please confirm which item is affected."))
        output, _ = self.execute(model)
        self.assertEqual(output["outcome"], "historical_comparison", output)
        serialized = json.dumps(model.requests, ensure_ascii=False)
        for sentinel in ("AI_COMPARISON_SENTINEL", "HUMAN_COMPARISON_SENTINEL", "FINAL_NOTE_SENTINEL",
                "FUTURE_STAFF_SENTINEL", "FUTURE_CUSTOMER_SENTINEL"):
            self.assertNotIn(sentinel, serialized)
        self.assertIn(package["messages"][1]["body"], serialized)
        self.assertEqual(len(self.service.detail(cid)["messages"]), 3)
        self.assertEqual(self.outbound(cid), [])

    def test_get_run_restores_understanding_tools_artifacts_usage_without_model_calls(self):
        cid, rid = self.create_mail()
        model = ScriptedModel(understanding, terminal())
        self.execute(model)
        with TestClient(create_app(Settings(object_root=Path(self.temp.name)), engine=self.engine,
                start_worker=False), base_url="http://127.0.0.1:18080") as client:
            for _ in range(2):
                response = client.get(f"/api/v1/runs/{rid}")
                self.assertEqual(response.status_code, 200, response.text)
                restored = response.json()["data"]
                self.assertEqual(restored["understanding"]["language"], "en")
                self.assertEqual(restored["tools"][0]["name"], "create_reply_draft")
                self.assertEqual(len(restored["artifacts"]), 1)
                self.assertEqual(restored["usage"]["model_requests"], 3)
                self.assertIsNone(restored["usage"]["cost"])
                self.assertEqual(restored["waits"][0]["condition_type"], "customer_information")
        self.assertEqual(len(model.requests), 3)
        self.assertEqual(len(self.outbound(cid)), 1)
