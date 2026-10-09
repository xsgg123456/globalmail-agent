"""Frozen model faults and deterministic Event barriers against real business gates."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch
import json
from uuid import uuid4
import sqlalchemy as sa
from agent_fixture import AgentFixture, ScriptedModel, understanding, terminal, call
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import agent_slots, processing_cycles
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.domain.conversation import Command, Takeover


class AgentFaultTests(AgentFixture):
    def test_schema_failure_repair_uses_two_requests_then_stops_without_default_business(self):
        cid, rid = self.create_mail()
        model = ScriptedModel({"content": "not JSON"}, {"content": "{\"language\":\"en\"}"})
        output, job = self.execute(model)
        self.assertEqual(output["error_code"], "understanding_schema_invalid", output)
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(self.budget_row(job)["model_requests"], 2)
        self.assertEqual(self.count(a.tool_commands), 0)
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.controls.get(rid)["run"]["status"], "failed")

    def test_authentication_failure_is_one_request_and_preserves_unknown_cost(self):
        cid, rid = self.create_mail()
        model = ScriptedModel(ServiceError("model_authentication_failed", 503))
        output, job = self.execute(model)
        self.assertEqual(output["error_code"], "model_authentication_failed", output)
        self.assertEqual(len(model.requests), 1)
        ledger = self.budget_row(job)
        self.assertEqual(ledger["unknown_requests"], 1)
        self.assertGreater(ledger["reserved_tokens"], 2000)
        self.assertEqual(self.outbound(cid), [])

    def test_timeout_has_only_one_extra_attempt_with_conservative_reservations(self):
        cid, rid = self.create_mail()
        model = ScriptedModel(ServiceError("model_timeout", 503), ServiceError("model_timeout", 503))
        output, job = self.execute(model)
        self.assertEqual(output["error_code"], "model_timeout", output)
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(self.budget_row(job)["model_requests"], 2)
        self.assertEqual(self.budget_row(job)["unknown_requests"], 2)
        self.assertEqual(self.outbound(cid), [])

    def test_transient_network_retry_success_consumes_request_and_keeps_unknown_first_charge(self):
        cid, _ = self.create_mail()
        model = ScriptedModel(ServiceError("model_rate_limited", 503), understanding, terminal())
        output, job = self.execute(model)
        self.assertEqual(output.get("outcome"), "reply_and_wait", output)
        self.assertEqual(len(model.requests), 4)
        ledger = self.budget_row(job)
        self.assertEqual(ledger["model_requests"], 4)
        self.assertEqual(ledger["unknown_requests"], 1)
        self.assertGreater(ledger["reserved_tokens"], 2090)
        self.assertEqual(len(self.outbound(cid)), 1)

    def test_provider_usage_beyond_output_budget_is_preserved_and_no_mail_is_sent(self):
        cid, rid = self.create_mail()
        model = ScriptedModel({"content": "{}", "usage": {"prompt_tokens": 20, "completion_tokens": 2001}})
        output, job = self.execute(model)
        self.assertEqual(output["error_code"], "provider_usage_exceeded", output)
        self.assertEqual(self.budget_row(job)["output_tokens"], 2001)
        self.assertEqual(self.controls.get(rid)["run"]["status"], "budget_exhausted")
        self.assertEqual(self.outbound(cid), [])

    def test_unknown_usage_keeps_full_reserved_budget_and_settlement_is_idempotent(self):
        self.create_mail()
        job, _, budget, _ = self.components()
        key = budget.reserve([{"role": "user", "content": "Hello"}], "understanding", "qwen3.7-plus")
        reserved = self.budget_row(job)["reserved_tokens"]
        budget.settle(key, None, "missing-usage")
        budget.settle(key, {"prompt_tokens": 20, "completion_tokens": 10}, "duplicate-late-usage")
        value = self.budget_row(job)
        self.assertEqual(value["reserved_tokens"], reserved)
        self.assertEqual(value["unknown_requests"], 1)
        self.assertEqual(value["input_tokens"], 0)
        self.assertEqual(self.row(a.usage_records, a.usage_records.c.request_key == key)["status"], "unknown")

    def test_known_usage_duplicate_settlement_counts_actual_tokens_once(self):
        self.create_mail()
        job, _, budget, _ = self.components()
        key = budget.reserve([{"role": "user", "content": "Hello"}], "understanding", "qwen3.7-plus")
        for _ in range(2):
            budget.settle(key, {"prompt_tokens": 20, "completion_tokens": 10,
                "completion_tokens_details": {"reasoning_tokens": 4}}, "known-request")
        value = self.budget_row(job)
        self.assertEqual(value["model_requests"], 1)
        self.assertEqual(value["input_tokens"], 20)
        self.assertEqual(value["output_tokens"], 10)
        self.assertEqual(value["reserved_tokens"], 30)
        self.assertEqual(value["unknown_requests"], 0)

    def test_retry_retains_cycle_consumption_and_cannot_buy_seventh_model_request(self):
        cid, rid = self.create_mail()
        job, _, budget, _ = self.components()
        for _ in range(5):
            key = budget.reserve([{"role": "user", "content": "bounded"}], "decision", "qwen3.7-plus")
            budget.settle(key, {"prompt_tokens": 20, "completion_tokens": 10})
        self.controls.control(rid, "stop", Command(expected_version=self.conversation(cid)["row_version"]), uuid4().hex)
        stopped = self.budget_row(job)
        retried = self.controls.control(rid, "retry", Command(expected_version=self.conversation(cid)["row_version"]), uuid4().hex)
        model = ScriptedModel(understanding, terminal())
        output, replacement = self.execute(model)
        self.assertEqual(replacement["cycle_id"], job["cycle_id"])
        self.assertEqual(str(replacement["run_id"]), retried["run_id"])
        self.assertEqual(output["error_code"], "budget_exhausted", output)
        self.assertEqual(len(model.requests), 1)
        ledger = self.budget_row(replacement)
        self.assertEqual(ledger["model_requests"], 6)
        self.assertGreaterEqual(ledger["reserved_tokens"], stopped["reserved_tokens"])
        self.assertEqual(self.count(processing_cycles), 1)
        self.assertEqual(self.outbound(cid), [])

    def test_no_progress_dynamic_loop_stops_after_two_identical_tools(self):
        cid, rid = self.create_mail()
        model = ScriptedModel(understanding, {"calls": [call("get_case_context", {})]},
            {"calls": [call("get_case_context", {})]})
        output, job = self.execute(model)
        self.assertEqual(output["error_code"], "no_progress", output)
        self.assertEqual(len(model.requests), 3)
        self.assertEqual(self.budget_row(job)["tool_calls"], 2)
        self.assertEqual(self.outbound(cid), [])

    def test_event_barriers_stop_new_input_takeover_and_lease_expiry_reject_late_draft(self):
        # Separate conversations/schema effects are compared per cid, never timing sleeps.
        for fault in ("stop", "new_input", "takeover", "lease_expired"):
            with self.subTest(fault=fault):
                cid, rid = self.create_mail(email=fault + "@example.test")
                job = self.claimed("barrier_" + fault)
                entered, release = Event(), Event()
                def blocked(messages):
                    entered.set()
                    if not release.wait(10):
                        raise AssertionError("Model barrier was never released")
                    return terminal("LATE_DRAFT_SENTINEL")
                model = ScriptedModel(understanding, blocked)
                with ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self.execute, model, job)
                    self.assertTrue(entered.wait(10))
                    try:
                        state = self.conversation(cid)
                        if fault == "stop":
                            self.controls.control(rid, "stop", Command(expected_version=state["row_version"]), uuid4().hex)
                        elif fault == "new_input":
                            self.append_mail(cid, "Fresh input supersedes the paused result.")
                        elif fault == "takeover":
                            self.service.takeover(cid, Takeover(expected_version=state["row_version"]), uuid4().hex)
                        else:
                            with self.engine.begin() as conn:
                                conn.execute(agent_slots.update().where(agent_slots.c.job_id == job["id"])
                                    .values(lease_expires_at=sa.func.now() - sa.text("interval '1 second'")))
                            self.leases.recover_expired()
                    finally:
                        release.set()
                    output, _ = future.result(timeout=10)
                self.assertIn(output.get("error_code"), {"lease_expired", "run_superseded"}, output)
                self.assertEqual(self.outbound(cid), [])
                run = self.controls.get(rid)["run"]
                self.assertIn(run["status"], {"stopped", "superseded", "interrupted"})
                if fault == "new_input":
                    # Consume only the deliberately queued successor; no old effect is replayed.
                    result, _ = self.execute(ScriptedModel(understanding, terminal("Fresh input received.")))
                    self.assertEqual(result["outcome"], "reply_and_wait", result)
                elif fault == "takeover":
                    self.assertEqual(self.conversation(cid)["processing_owner"], "human_review")

    def test_terminal_proposal_followed_by_another_tool_has_no_effect(self):
        cid, _ = self.create_mail()
        first = terminal()["calls"][0]
        model = ScriptedModel(understanding, {"calls": [first, call("get_case_context", {})]})
        output, _ = self.execute(model)
        self.assertEqual(output["error_code"], "tool_after_terminal_proposal", output)
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.count(a.reply_artifacts), 0)

    def test_valid_safety_understanding_checkpoint_failure_handoffs_at_last_request_budget(self):
        cid, rid = self.create_mail("There are sparks from the plug.")
        job, _, budget, _ = self.components()
        for _ in range(5):
            request = budget.reserve([{"role": "user", "content": "prior bounded activity"}], "decision", "qwen3.7-plus")
            budget.settle(request, {"prompt_tokens": 20, "completion_tokens": 10})
        def safety(messages):
            payload = json.loads(messages[-1]["content"])
            return understanding(messages, risk_flags=[{"kind": "fire", "sources": [{
                "message_id": payload["messages"][-1]["message_id"], "quote": "sparks from the plug"}]}])
        from globalmail_agent.adapters.checkpoint_repository import CheckpointRepository
        actual_put_writes = CheckpointRepository.put_writes
        injected = []
        def fail_after_understanding(repo, config, writes, task_id, task_path=""):
            if any(channel == "understanding" and isinstance(value, dict) and value.get("risk_flags")
                    for channel, value in writes):
                injected.append(task_id)
                raise ServiceError("checkpoint_persistence_failed", 503)
            return actual_put_writes(repo, config, writes, task_id, task_path)
        model = ScriptedModel(safety)
        with patch.object(CheckpointRepository, "put_writes", new=fail_after_understanding):
            output, _ = self.execute(model, job)
        self.assertEqual(output.get("outcome"), "handoff", output)
        self.assertTrue(injected)
        self.assertEqual(len(model.requests), 1)
        self.assertEqual(self.budget_row(job)["model_requests"], 6)
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.conversation(cid)["processing_owner"], "human_review")
        self.assertEqual(self.controls.get(rid)["run"]["status"], "handed_off")
