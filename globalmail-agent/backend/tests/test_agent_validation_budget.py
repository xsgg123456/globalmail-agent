"""Authorized validator capacity against the real cycle ledger and effect gates."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch
from uuid import uuid4
import sqlalchemy as sa
from agent_fixture import AgentFixture, ScriptedModel, understanding, terminal
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import agent_slots
from globalmail_agent.agent.budget import Budget, input_estimate
from globalmail_agent.agent.graph import AgentGraph
from globalmail_agent.domain.conversation import Command, Takeover


class ReviewUsageModel(ScriptedModel):
    def __init__(self, completion=4000, finish="stop", barrier=None):
        super().__init__(understanding, terminal())
        self.completion, self.finish, self.barrier = completion, finish, barrier

    def request(self, messages, **options):
        output = super().request(messages, **options)
        if (options.get("schema") or {}).get("title") == "OutcomeReview":
            if self.barrier:
                self.barrier()
            output.update(usage={"prompt_tokens": 20, "completion_tokens": self.completion,
                "completion_tokens_details": {"reasoning_tokens": 2048}}, finish_reason=self.finish)
        return output


class ValidationBudgetTests(AgentFixture):
    def test_unknown_validation_retains_full_reservation_and_late_settlement_is_idempotent(self):
        self.create_mail()
        job, _, budget, _ = self.components()
        messages = [{"role": "user", "content": "Complete source"}]
        key = budget.reserve(messages, "validation", "qwen3.7-plus")
        expected = input_estimate(messages) + 4000
        self.assertEqual(self.budget_row(job)["reserved_tokens"], expected)
        budget.settle(key, None)
        budget.settle(key, {"prompt_tokens": 20, "completion_tokens": 3000})
        row = self.budget_row(job)
        self.assertEqual((row["reserved_tokens"], row["unknown_requests"], row["output_tokens"]), (expected, 1, 0))

    def test_validation_4000_including_reasoning_is_accepted_and_settled_once(self):
        cid, _ = self.create_mail()
        model = ReviewUsageModel()
        output, job = self.execute(model)
        self.assertEqual(output.get("outcome"), "reply_and_wait", output)
        ledger = self.budget_row(job)
        self.assertEqual((ledger["output_tokens"], ledger["reserved_tokens"]), (4020, 4080))
        review = self.row(a.usage_records, (a.usage_records.c.run_id == job["run_id"]) &
            (a.usage_records.c.stage == "validation"))
        budget = Budget.__new__(Budget)
        budget.engine, budget.job = self.engine, job
        budget.active_ms = lambda: ledger["active_ms"]
        budget.settle(review["request_key"], {"prompt_tokens": 20, "completion_tokens": 4000})
        self.assertEqual(self.budget_row(job)["reserved_tokens"], 4080)
        self.assertEqual(len(self.outbound(cid)), 1)
        self.assertEqual([r["timeout"] for r in model.requests], [30, 30, 60])

    def test_validator_overrun_or_truncation_preserves_usage_and_sends_nothing(self):
        for completion, finish, code in ((4001, "stop", "provider_usage_exceeded"),
                (4000, "length", "model_output_incomplete")):
            with self.subTest(completion=completion, finish=finish):
                cid, _ = self.create_mail(email=finish + "@example.test")
                output, job = self.execute(ReviewUsageModel(completion, finish))
                self.assertEqual(output.get("error_code"), code, output)
                self.assertEqual(self.budget_row(job)["output_tokens"], 20 + completion)
                self.assertEqual(self.outbound(cid), [])

    def test_total_tokens_and_input_limit_still_reject_before_network(self):
        self.create_mail()
        job, _, budget, _ = self.components()
        with self.engine.begin() as conn:
            conn.execute(a.cycle_budgets.update().where(a.cycle_budgets.c.cycle_id == job["cycle_id"])
                .values(reserved_tokens=77000))
        self.assert_error("budget_exhausted", lambda: budget.reserve([], "validation", "qwen3.7-plus"))
        with patch("globalmail_agent.agent.budget.input_estimate", return_value=16001):
            self.assert_error("input_budget_exceeded", lambda: budget.reserve([], "validation", "qwen3.7-plus"))
        self.assertEqual(self.budget_row(job)["model_requests"], 0)

    def test_network_wait_never_exceeds_remaining_cycle_time(self):
        self.create_mail()
        job, _, budget, _ = self.components()
        model = ScriptedModel({})
        graph = AgentGraph.__new__(AgentGraph)
        graph.budget, graph.model = budget, model
        with patch.object(budget, "active_ms", return_value=117500):
            graph.request([], "validation")
        self.assertEqual(model.requests[0]["timeout"], 2.5)
        with patch.object(budget, "active_ms", return_value=120000):
            self.assert_error("budget_exhausted", lambda: graph.request([], "validation"))
        self.assertEqual(len(model.requests), 1)

    def test_late_validation_cannot_commit_after_stop_new_input_takeover_or_expired_lease(self):
        for fault in ("stop", "new_input", "takeover", "lease_expired", "active_budget"):
            with self.subTest(fault=fault):
                cid, rid = self.create_mail(email=fault + "@example.test")
                job = self.claimed("validation_" + fault)
                entered, release = Event(), Event()
                def barrier():
                    entered.set()
                    if not release.wait(10):
                        raise AssertionError("Validator barrier was never released")
                model = ReviewUsageModel(barrier=barrier)
                actual_active_ms = Budget.active_ms
                def active_ms(budget):
                    return 120000 if fault == "active_budget" and release.is_set() else actual_active_ms(budget)
                with patch.object(Budget, "active_ms", new=active_ms), ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(self.execute, model, job)
                    self.assertTrue(entered.wait(10))
                    try:
                        version = self.conversation(cid)["row_version"]
                        if fault == "stop":
                            self.controls.control(rid, "stop", Command(expected_version=version), uuid4().hex)
                        elif fault == "new_input":
                            self.append_mail(cid, "New customer evidence.")
                        elif fault == "takeover":
                            self.service.takeover(cid, Takeover(expected_version=version), uuid4().hex)
                        elif fault == "lease_expired":
                            with self.engine.begin() as conn:
                                conn.execute(agent_slots.update().where(agent_slots.c.job_id == job["id"])
                                    .values(lease_expires_at=sa.func.now() - sa.text("interval '1 second'")))
                            self.leases.recover_expired()
                    finally:
                        release.set()
                    output, _ = future.result(timeout=10)
                self.assertIn(output.get("error_code"), {"lease_expired", "run_superseded", "budget_exhausted"}, output)
                self.assertEqual(self.outbound(cid), [])
                self.assertEqual(self.budget_row(job)["output_tokens"], 4020)
                if fault == "new_input":
                    # Consume the intentional successor before the next isolated subcase.
                    self.execute(ScriptedModel(understanding, terminal()))
