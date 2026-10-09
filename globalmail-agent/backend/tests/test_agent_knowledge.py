"""Actual PG publication/search/dependencies; explicit vectors do not measure relevance."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from time import monotonic
from unittest.mock import patch
import json
from uuid import UUID, uuid4
import sqlalchemy as sa
from agent_fixture import AgentSupport, ScriptedModel, understanding, terminal, draft, call
from index_helpers import IndexFixture
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.application.business_queries import BusinessQueries
from globalmail_agent.application.commit_outcome import commit_outcome
from globalmail_agent.application.run_records import RunRecords
from globalmail_agent.knowledge.index_commands import WithdrawCommand
from globalmail_agent.knowledge.commands import VersionCommand, ReviewCommand


class AgentKnowledgeTests(AgentSupport, IndexFixture):
    def prepare_release(self, text, did=None):
        content = "# 合成协议资料\n" + text
        if did is None:
            did, vid, _ = self.reviewed_markdown(content)
        else:
            state = self.queries.detail(did)["document"]
            changed = self.docs.revise(did, VersionCommand(expected_version=state["row_version"], content=content,
                applicabilities=[{"section_id": "document", "sku": "H-CTD16-US-BK", "basis": "明确合成协议适配"}]), uuid4().hex)
            vid = UUID(changed["version_id"])
            parsing = self.start_parse(vid)
            self.runner.owner = parsing["lease_owner"]
            self.runner.execute(parsing)
            self.reviews.review(vid, ReviewCommand.model_validate(self.review_payload(vid)), uuid4().hex)
        return did, self.build(vid)

    def scenario_line(self):
        cid, rid = self.scene()
        data = BusinessQueries(self.engine).detail(cid)["data"]
        return cid, rid, data["orders"][0]["lines"][0]["line_id"]

    @staticmethod
    def search_call(line, key=None):
        return {"calls": [call("search_reference", {"order_line_id": line,
            "query": "appropriate procedure", "types": ["troubleshooting_md"]}, key)]}

    @staticmethod
    def order_candidate(messages):
        payload = json.loads(messages[-1]["content"])
        mail = payload["messages"][-1]
        number = mail["body"].split("Amazon order number: ", 1)[1].splitlines()[0]
        source = {"message_id": mail["message_id"], "quote": number}
        return understanding([], order_candidates=[{"value": number, "sources": [source]}])

    @staticmethod
    def cited_reply(messages):
        observation = json.loads(next(message["content"] for message in reversed(messages) if message["role"] == "tool"))
        ref = observation["data"]["evidence"][0]["evidence_id"]
        body = "Please follow the applicable documented procedure."
        return terminal(body, claims=[{"kind": "product_step", "text": body, "source_ids": [ref]}],
            citation_ids=[ref], waiting_for="customer_feedback")

    def test_withdraw_after_exposure_blocks_unreferenced_dependency_and_late_commit(self):
        did, build = self.prepare_release("WITHDRAWN_KNOWLEDGE_SENTINEL")
        self.publish([build])
        cid, rid, line = self.scenario_line()
        job, context, budget, gateway = self.components(embedding=self.gateway)
        _, observation = gateway.call(self.search_call(line)["calls"][0])
        self.assertEqual(observation["status"], "ok")
        self.assertIn("WITHDRAWN_KNOWLEDGE_SENTINEL", str(observation["data"]))
        self.assertEqual(self.count(a.agent_run_dependencies), 1)
        current = self.releases.listing()["head"]
        self.releases.withdraw(did, WithdrawCommand(expected_version=1,
            expected_release_epoch=current["epoch"]), uuid4().hex)
        # Even a final reply without a citation has already seen the revoked body.
        self.assert_error("stale_release", lambda: commit_outcome(self.engine, self.store, context, job,
            understanding([]), {"kind": "reply", "data": draft()}))
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.count(a.reply_artifacts), 0)
        linked = RunRecords(self.engine, self.store).get(rid)["references"]
        self.assertFalse(linked[0]["eligible"])
        self.assertEqual(linked[0]["reason"], "document_withdrawn")

    def test_release_switch_rebuilds_once_clears_old_knowledge_and_keeps_cycle_budget(self):
        did, old = self.prepare_release("OLD_KNOWLEDGE_SENTINEL")
        _, new = self.prepare_release("NEW_KNOWLEDGE_SENTINEL", did)
        self.publish([old], replace_all=True)
        cid, rid, line = self.scenario_line()
        entered, release = Event(), Event()
        def blocked(messages):
            self.assertIn("OLD_KNOWLEDGE_SENTINEL", str(messages))
            entered.set()
            if not release.wait(10):
                raise AssertionError("Publication barrier was never released")
            return self.cited_reply(messages)
        model = ScriptedModel(self.order_candidate, self.search_call(line), blocked,
            self.search_call(line), self.cited_reply)
        job = self.claimed()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.execute, model, job, self.gateway)
            self.assertTrue(entered.wait(10))
            try:
                switched = self.publish([new], replace_all=True)
                before = self.budget_row(job)
                self.assertEqual(before["model_requests"], 3)
            finally:
                release.set()
            output, _ = future.result(timeout=15)
        self.assertEqual(output.get("outcome"), "reply_and_wait", output)
        self.assertEqual(len(model.requests), 6)
        self.assertNotIn("OLD_KNOWLEDGE_SENTINEL", str(model.requests[3:]))
        self.assertIn("NEW_KNOWLEDGE_SENTINEL", str(model.requests[-1]))
        context = self.row(a.agent_run_contexts, a.agent_run_contexts.c.run_id == rid)
        self.assertEqual(context["rebuild_count"], 1)
        self.assertEqual(str(context["release_id"]), switched["head"]["release_id"])
        self.assertEqual(self.budget_row(job)["model_requests"], 6)
        self.assertEqual(self.budget_row(job)["tool_calls"], 3)
        self.assertEqual(len(self.outbound(cid)), 1)
        with self.engine.connect() as conn:
            dependencies = list(conn.execute(sa.select(a.agent_run_dependencies).where(
                a.agent_run_dependencies.c.run_id == rid)).mappings())
        self.assertEqual(sum(row["active"] for row in dependencies), 1)
        self.assertEqual(len(dependencies), 2)

    def test_second_release_switch_handoffs_without_second_rebuild_or_outbound(self):
        did, old = self.prepare_release("RELEASE_0_SENTINEL")
        builds = [old, *[self.prepare_release(f"RELEASE_{i}_SENTINEL", did)[1] for i in range(1, 3)]]
        self.publish([builds[0]], replace_all=True)
        cid, rid, line = self.scenario_line()
        entered = [Event(), Event()]
        release = [Event(), Event()]
        def block(index):
            def response(messages):
                entered[index].set()
                if not release[index].wait(10):
                    raise AssertionError("Second publication barrier was never released")
                return self.cited_reply(messages)
            return response
        model = ScriptedModel(self.order_candidate, self.search_call(line), block(0),
            self.search_call(line), block(1))
        job = self.claimed()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.execute, model, job, self.gateway)
            try:
                for index in range(2):
                    self.assertTrue(entered[index].wait(10))
                    self.publish([builds[index + 1]], replace_all=True)
                    release[index].set()
                output, _ = future.result(timeout=15)
            finally:
                for barrier in release:
                    barrier.set()
        self.assertEqual(output["outcome"], "handoff", output)
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.row(a.agent_run_contexts, a.agent_run_contexts.c.run_id == rid)["rebuild_count"], 1)
        self.assertEqual(self.budget_row(job)["model_requests"], 5)
        self.assertEqual(self.conversation(cid)["processing_owner"], "human_review")

    def test_query_embedding_head_switch_registers_no_old_evidence(self):
        did, old = self.prepare_release("OLD_EMBED_QUERY_SENTINEL")
        _, new = self.prepare_release("NEW_EMBED_QUERY_SENTINEL", did)
        self.publish([old], replace_all=True)
        cid, rid, line = self.scenario_line()
        job, context, _, gateway = self.components(embedding=self.gateway)
        entered, release = Event(), Event()
        def blocked():
            entered.set()
            if not release.wait(10):
                raise AssertionError("Embedding barrier was never released")
        self.gateway.hook = blocked
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(gateway.call, self.search_call(line)["calls"][0])
            self.assertTrue(entered.wait(10))
            try:
                self.publish([new], replace_all=True)
            finally:
                release.set()
            self.assert_error("stale_release", lambda: future.result(timeout=10))
        self.assertEqual(self.count(a.agent_run_dependencies), 0)
        self.assertEqual(self.outbound(cid), [])

    def test_final_commit_holds_head_lock_until_effect_then_withdraw_can_commit(self):
        did, build = self.prepare_release("COMMIT_FIRST_EVIDENCE_SENTINEL")
        self.publish([build])
        cid, rid, line = self.scenario_line()
        job, context, _, gateway = self.components(embedding=self.gateway)
        _, observation = gateway.call(self.search_call(line)["calls"][0])
        ref = observation["data"]["evidence"][0]["evidence_id"]
        body = "Please use the applicable documented procedure."
        proposal = {"kind": "reply", "data": draft(body, claims=[{"kind": "product_step", "text": body,
            "source_ids": [ref]}], citation_ids=[ref])}
        self.approve_fixture_draft(context, job, proposal["data"])
        acquired, release, withdrawal_started = Event(), Event(), Event()
        held_pid = []
        from globalmail_agent.application.commit_outcome import validate_draft as actual_validation
        def hold(conn, *args):
            output = actual_validation(conn, *args)
            held_pid.append(conn.execute(sa.text("SELECT pg_backend_pid()")).scalar_one())
            acquired.set()
            if not release.wait(10):
                raise AssertionError("Final transaction barrier was never released")
            return output
        epoch = self.releases.listing()["head"]["epoch"]
        def withdraw():
            withdrawal_started.set()
            return self.releases.withdraw(did, WithdrawCommand(expected_version=1,
                expected_release_epoch=epoch), uuid4().hex)
        with patch("globalmail_agent.application.commit_outcome.validate_draft", side_effect=hold):
            with ThreadPoolExecutor(max_workers=2) as pool:
                final = pool.submit(commit_outcome, self.engine, self.store, context, job, understanding([]), proposal)
                self.assertTrue(acquired.wait(10))
                revoking = pool.submit(withdraw)
                self.assertTrue(withdrawal_started.wait(10))
                try:
                    blocked = False
                    deadline = monotonic() + 3
                    while monotonic() < deadline:
                        with self.engine.connect() as conn:
                            blocked = conn.execute(sa.text("SELECT EXISTS (SELECT 1 FROM pg_stat_activity "
                                "WHERE :pid = ANY(pg_blocking_pids(pid)))"), {"pid": held_pid[0]}).scalar_one()
                        if blocked:
                            break
                    self.assertTrue(blocked, "Withdrawal must wait on final commit's knowledge head lock")
                    self.assertEqual(self.outbound(cid), [])
                finally:
                    release.set()
                self.assertEqual(final.result(timeout=10)["outcome"], "reply_and_wait")
                self.assertTrue(revoking.result(timeout=10)["withdrawn"])
        self.assertEqual(len(self.outbound(cid)), 1)
        self.assertFalse(RunRecords(self.engine, self.store).get(rid)["references"][0]["eligible"])
