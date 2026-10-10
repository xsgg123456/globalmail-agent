"""PG controlled wait receiver; full simulated result progression remains Phase 10."""
from copy import deepcopy
import sqlalchemy as sa
from agent_fixture import AgentFixture, understanding, draft
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import jobs, agent_runs
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

    def test_business_change_records_without_queue_and_invalidates_old_attempt(self):
        cid, rid, operation = self.operation_case()
        job, context, _, _ = self.components()
        key = 'manual_execution:' + operation
        before = self.count(jobs)
        result = self.wake(cid, key, 1)
        self.assertEqual(result['status'], 'suppressed_by_human')
        self.assertEqual(self.count(jobs), before)
        self.assertIsNone(self.leases.claim('business_change_must_not_queue'))
        self.assertEqual(self.row(agent_runs, agent_runs.c.id == rid)['status'], 'superseded')
        self.assert_error('lease_expired', lambda: commit_outcome(self.engine, self.store, context, job,
            understanding([]), {'kind':'reply','data':draft()}))
        self.assertEqual(self.pending(cid,key)['status'], 'suppressed_by_human')
        self.assertIsNone(self.pending(cid,key)['observed_run_id'])
        self.assertEqual(self.outbound(cid), [])

    def test_next_customer_input_loads_and_consumes_only_observed_version(self):
        cid, _, operation = self.operation_case()
        key = 'manual_execution:' + operation
        self.wake(cid,key,1)
        self.append_mail(cid,'Please update me on my earlier request.')
        job, context, _, _ = self.components()
        self.assertIn(key,str(context.payload))
        value=draft()
        self.approve_fixture_draft(context,job,value)
        commit_outcome(self.engine,self.store,context,job,understanding([]),{'kind':'reply','data':value})
        self.assertEqual(self.pending(cid,key)['status'],'processed')
        self.assertEqual(self.pending(cid,key)['observed_run_id'],job['run_id'])

    def test_duplicate_or_older_business_change_keeps_version_without_new_job(self):
        cid, _, operation = self.operation_case()
        key='manual_execution:'+operation
        self.wake(cid,key,2)
        before=self.conversation(cid)
        jobs_before=self.count(jobs)
        for version in (2,1):
            self.assertFalse(self.wake(cid,key,version)['changed'])
        self.assertEqual(self.pending(cid,key)['business_version'],2)
        self.assertEqual(self.conversation(cid)['input_revision'],before['input_revision'])
        self.assertEqual(self.count(jobs),jobs_before)

    def test_new_business_wait_terminal_is_refused_without_reply_or_wait(self):
        cid, _, operation = self.operation_case()
        job, context, _, _ = self.components()
        value=draft('',claims=[],waiting_for='manual_execution',waiting_operation_id=operation)
        self.approve_fixture_draft(context,job,value)
        self.assert_error('business_wait_forbidden',lambda:commit_outcome(self.engine,self.store,context,job,
            understanding([]),{'kind':'reply','data':value}))
        self.assertEqual(self.outbound(cid),[])
        self.assertEqual(self.count(a.wait_conditions),0)
        self.assertEqual(self.count(a.reply_artifacts),0)

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
