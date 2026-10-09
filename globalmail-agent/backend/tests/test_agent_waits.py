"""PG controlled wait receiver; full simulated result progression remains Phase 10."""
from copy import deepcopy
import sqlalchemy as sa
from agent_fixture import AgentFixture, understanding, draft
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import jobs
from globalmail_agent.adapters.fixture_loader import FixturePackage
from globalmail_agent.application.commit_outcome import commit_outcome
from globalmail_agent.application.waits import record_wake, register_wait
from globalmail_agent.application.conversation_lock import lock_conversation, DEFAULT_WORKSPACE_ID
from globalmail_agent.application.business_queries import BusinessQueries
from globalmail_agent.domain.conversation import Takeover, HumanReply
from uuid import uuid4


class AgentWaitTests(AgentFixture):
    def operation_case(self):
        cid, rid = self.scene("SCN-027")  # Existing spare-part operation awaits manual execution.
        data = BusinessQueries(self.engine).detail(cid)["data"]
        operation = data["operations"][0]["operation_id"]
        return cid, rid, operation

    def wake(self, cid, key, version):
        with self.engine.begin() as conn:
            conv = lock_conversation(conn, cid, DEFAULT_WORKSPACE_ID)
            return record_wake(conn, conv, key, version)

    def pending(self, cid, key):
        return self.row(a.wake_pending, sa.and_(a.wake_pending.c.conversation_id == cid,
            a.wake_pending.c.condition_key == key))

    def test_wake_arriving_after_context_is_not_consumed_by_unobserving_terminal(self):
        cid, rid, operation = self.operation_case()
        job, context, _, _ = self.components()
        key = "manual_execution:" + operation
        self.approve_fixture_draft(context, job, draft())
        self.wake(cid, key, 1)
        from globalmail_agent.application.conversation_lock import ServiceError
        try:
            commit_outcome(self.engine, self.store, context, job, understanding([]),
                {"kind": "reply", "data": draft()})
        except ServiceError as error:
            self.assertIn(error.code, {"stale_business_context", "run_superseded", "lease_expired"})
        pending = self.pending(cid, key)
        self.assertEqual(pending["status"], "pending")
        self.assertIsNone(pending["observed_run_id"])

    def test_wake_is_loaded_and_only_observed_version_is_consumed_by_commit(self):
        cid, rid, operation = self.operation_case()
        key = "manual_execution:" + operation
        self.wake(cid, key, 1)
        job, context, _, _ = self.components()
        self.assertIn(key, str(context.payload), "Pending business facts must be visible to the new run")
        self.approve_fixture_draft(context, job, draft())
        commit_outcome(self.engine, self.store, context, job, understanding([]), {"kind": "reply", "data": draft()})
        pending = self.pending(cid, key)
        self.assertEqual(pending["status"], "processed")
        self.assertEqual(pending["observed_run_id"], job["run_id"])

    def test_early_business_version_rejects_old_wait_and_keeps_durable_wake(self):
        cid, rid, operation = self.operation_case()
        key = "manual_execution:" + operation
        self.wake(cid, key, 2)
        job, _, _, _ = self.components()
        rid = job["run_id"]
        self.assert_error("stale_business_context", lambda: self._register(cid, rid, operation, 1))
        self.assertEqual(self.pending(cid, key)["business_version"], 2)
        self.assertEqual(self.pending(cid, key)["status"], "pending")
        self.assertEqual(self.count(a.wait_conditions), 0)
        self._register(cid, rid, operation, 2)
        self.assertEqual(self.count(a.wait_conditions), 1)

    def test_newer_wake_version_remains_pending_even_when_older_version_was_observed(self):
        cid, rid, operation = self.operation_case()
        key = "manual_execution:" + operation
        self.wake(cid, key, 1)
        job, context, _, _ = self.components()
        self.assertIn(key, str(context.payload))
        self.approve_fixture_draft(context, job, draft())
        self.wake(cid, key, 2)
        self.assert_error("lease_expired", lambda: commit_outcome(self.engine, self.store, context, job,
            understanding([]), {"kind": "reply", "data": draft()}))
        pending = self.pending(cid, key)
        self.assertEqual(pending["status"], "pending")
        self.assertEqual(pending["business_version"], 2)
        self.assertIsNone(pending["observed_run_id"])

    def _register(self, cid, rid, operation, observed):
        with self.engine.begin() as conn:
            conv = lock_conversation(conn, cid, DEFAULT_WORKSPACE_ID)
            return register_wait(conn, conv, rid, "manual_execution", operation, observed)

    def test_business_wait_only_terminal_releases_slot_without_outbound(self):
        cid, rid, operation = self.operation_case()
        job, context, _, _ = self.components()
        data = draft("", claims=[], waiting_for="manual_execution", waiting_operation_id=operation)
        self.approve_fixture_draft(context, job, data)
        output = commit_outcome(self.engine, self.store, context, job, understanding([]), {"kind": "reply", "data": data})
        self.assertEqual(output["outcome"], "wait_business")
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.conversation(cid)["scheduling_state"], "waiting_business")
        self.assertIsNone(self.leases.claim("normal_wait_does_not_keep_running"))
        self.assertEqual(self.count(a.reply_artifacts), 1)
        self.assertEqual(self.count(a.wait_conditions), 1)

    def test_early_result_registers_one_successor_in_same_commit_and_no_old_reply(self):
        package = FixturePackage()
        scene = deepcopy(package.scenarios["SCN-027"])
        scene["scenario_id"] = "AGENT-EARLY-MANUAL-VERSION"
        scene["initial_state"]["operations"][0]["version"] = 2
        package.scenarios[scene["scenario_id"]] = scene
        cid, rid = self.scene(scene["scenario_id"], package)
        operation = scene["initial_state"]["operations"][0]["operation_id"]
        job, context, _, _ = self.components()
        key = "manual_execution:" + operation
        data = draft("", claims=[], waiting_for="manual_execution", waiting_operation_id=operation,
            observed_business_version=1)
        self.approve_fixture_draft(context, job, data)
        output = commit_outcome(self.engine, self.store, context, job, understanding([]), {"kind": "reply", "data": data})
        self.assertEqual(output["outcome"], "superseded")
        self.assertEqual(output["reason_code"], "stale_business_context")
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.count(a.reply_artifacts), 0)
        self.assertEqual(self.count(a.wait_conditions), 0)
        self.assertEqual(self.pending(cid, key)["business_version"], 2)
        self.assertEqual(self.pending(cid, key)["status"], "pending")
        before = self.count(jobs)
        for version in (2, 1):  # Duplicate and older delivery both keep the newer durable trigger.
            duplicate = self.wake(cid, key, version)
            self.assertFalse(duplicate["changed"])
            self.assertEqual(self.count(jobs), before)
        replacement, newest, _, _ = self.components()
        self.assertNotEqual(replacement["run_id"], rid)
        self.assertEqual(self.pending(cid, key)["status"], "pending", "Queueing is not consumption")
        latest = draft("", claims=[], waiting_for="manual_execution", waiting_operation_id=operation,
            observed_business_version=2)
        self.approve_fixture_draft(newest, replacement, latest)
        committed = commit_outcome(self.engine, self.store, newest, replacement, understanding([]),
            {"kind": "reply", "data": latest})
        self.assertEqual(committed["outcome"], "wait_business")
        self.assertEqual(self.pending(cid, key)["status"], "processed")
        self.assertEqual(self.pending(cid, key)["observed_run_id"], replacement["run_id"])

    def test_unrelated_operation_wake_is_rejected_without_input_revision_or_job_change(self):
        cid, _, _ = self.operation_case()
        other, _ = self.scene("SCN-023")
        foreign = BusinessQueries(self.engine).detail(other)["data"]["operations"][0]["operation_id"]
        before, job_count = self.conversation(cid), self.count(jobs)
        for operation in ("OTHER-OPERATION", foreign):
            self.assert_error("operation_out_of_scope", lambda: self.wake(cid, "manual_execution:" + operation, 1))
        self.assertEqual(self.conversation(cid)["input_revision"], before["input_revision"])
        self.assertEqual(self.count(jobs), job_count)
        self.assertEqual(self.count(a.wake_pending), 0)

    def test_human_suppressed_wakes_are_observed_only_after_next_customer_input(self):
        cid, rid, operation = self.operation_case()
        state = self.conversation(cid)
        self.service.takeover(cid, Takeover(expected_version=state["row_version"]), uuid4().hex)
        before = self.count(jobs)
        key = "manual_execution:" + operation
        first = self.wake(cid, key, 1)
        self.assertEqual(first["status"], "suppressed_by_human")
        self.assertEqual(self.count(jobs), before)
        state = self.conversation(cid)
        self.service.human_reply(cid, HumanReply(expected_version=state["row_version"],
            expected_input_revision=state["input_revision"], body="Human confirmed the request details."), uuid4().hex)
        self.assertEqual(self.wake(cid, key, 2)["status"], "suppressed_by_human")
        self.assertEqual(self.count(jobs), before)
        self.assertIsNone(self.leases.claim("human_gate_must_keep_business_pending"))
        self.append_mail(cid, "Customer replies after the human barrier.")
        job, context, _, _ = self.components()
        self.assertIn(key, str(context.payload))
        self.assertEqual(self.pending(cid, key)["status"], "suppressed_by_human")
        data = draft("We received your update.", waiting_for="customer_feedback")
        self.approve_fixture_draft(context, job, data)
        commit_outcome(self.engine, self.store, context, job, understanding([]), {"kind": "reply", "data": data})
        self.assertEqual(self.pending(cid, key)["status"], "processed")
        self.assertEqual(self.pending(cid, key)["observed_run_id"], job["run_id"])
