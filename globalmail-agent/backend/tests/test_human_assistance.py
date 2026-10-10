"""Actual PG, leases and Graph; scripted model responses are engineering fixtures only."""
from uuid import UUID, uuid4
from agent_fixture import AgentFixture, ScriptedModel, call, understanding, terminal
from globalmail_agent.domain.conversation import HumanReply, Command, Close, Takeover
from globalmail_agent.adapters.conversation_schema import agent_runs, messages
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.application.conversation_lock import ServiceError


def handoff():
    return {"calls": [call("request_human_review", {"reason": "commercial_after_sales",
        "summary": "请客服核对订单和现有记录", "gaps": ["订单状态未核实"],
        "recommendations": ["核实后由客服决定并回复"], "draft": "We are checking your existing records."})]}


class HumanAssistanceTests(AgentFixture):
    def intent(self, kind, payload):
        row = payload[-1]
        return understanding(payload, missing_information=[], intents=[{"business_type": kind,
            "order_number": None, "target_item": None, "condition": None,
            "requested_solution": None, "consent": "none",
            "sources": [{"message_id": row["message_id"], "quote": row["body"]}]}])

    def commercial(self, kind="refund", email="assist@example.test"):
        cid, rid = self.create_mail("I want a " + kind, email=email)
        model = ScriptedModel(lambda m: self.intent(kind, __import__("json").loads(m[1]["content"])["messages"]), handoff())
        result, job = self.execute(model)
        self.assertEqual(result["outcome"], "handoff", result)
        return cid, rid, model

    def reply(self, cid):
        conv = self.conversation(cid)
        return self.service.human_reply(cid, HumanReply(expected_version=conv["row_version"],
            expected_input_revision=conv["input_revision"], body="I am checking this for you."), uuid4().hex)

    def test_four_categories_first_round_and_followup_remain_internal(self):
        for kind in ("refund", "return", "replacement", "parts"):
            with self.subTest(kind=kind):
                cid, rid, model = self.commercial(kind, kind + "@example.test")
                conv = self.conversation(cid)
                self.assertTrue(conv["persistent_human"])
                self.assertFalse(conv["human_claimed"])
                self.assertEqual(conv["processing_owner"], "human_review")
                self.assertEqual(self.row(agent_runs, agent_runs.c.id == rid)["execution_mode"], "human_assist")
                self.assertEqual(self.outbound(cid), [])
                for req in model.requests:
                    for tool in req.get("tools") or []:
                        self.assertNotIn(tool["function"]["name"], {"create_reply_draft", "create_after_sales_operation"})
                self.reply(cid)
                incoming = self.append_mail(cid, "Any progress?")
                next_id = UUID(incoming["run_id"])
                self.assertEqual(self.row(agent_runs, agent_runs.c.id == next_id)["execution_mode"], "human_assist")
                capture = []
                def understand_next(m):
                    payload = __import__("json").loads(m[1]["content"])
                    capture.append(payload)
                    return understanding(payload["messages"])
                result, _ = self.execute(ScriptedModel(understand_next, handoff()))
                self.assertEqual(result["outcome"], "human_advice", result)
                self.assertIn("simulated_human", [r["sender"] for r in capture[0]["messages"]])
                self.assertEqual(self.outbound(cid), [])
                self.assertEqual(self.count(b.operations), 0)

    def test_write_tools_and_autonomous_draft_are_rejected_by_real_gateway(self):
        cid, _, _ = self.commercial()
        self.append_mail(cid, "Please process it now")
        _, _, _, gateway = self.components()
        for name in ("create_after_sales_operation", "cancel_after_sales_operation", "check_after_sales_eligibility"):
            self.assert_error("tool_not_allowed", lambda: gateway.call(call(name, {})))
        self.assert_error("autonomous_reply_forbidden", lambda: gateway.call(call("create_reply_draft", {})))
        self.assertEqual(self.count(b.operations), 0)
        self.assertEqual(self.outbound(cid), [])

    def test_staff_reply_supersedes_an_inflight_assist(self):
        cid, _, _ = self.commercial()
        incoming = self.append_mail(cid, "Any update?")
        job, context, _, _ = self.components()
        self.reply(cid)
        from globalmail_agent.application.commit_outcome import commit_outcome
        self.assert_error("lease_expired", lambda: commit_outcome(self.engine, self.store, context, job,
            understanding([]), {"kind": "handoff", "data": {"reason": "cannot_decide", "summary": "late",
                "gaps": ["late"], "draft": "late"}}))
        self.assertEqual(self.row(agent_runs, agent_runs.c.id == UUID(incoming["run_id"]))["status"], "superseded")
        self.assertEqual(self.outbound(cid), [])

    def test_resolved_mail_is_recorded_without_reopen_or_run(self):
        cid, _, _ = self.commercial()
        self.service.close(cid, Close(expected_version=self.conversation(cid)["row_version"]), uuid4().hex)
        count = self.count(agent_runs)
        incoming = self.append_mail(cid, "I have another question")
        self.assertNotIn("run_id", incoming)
        conv = self.conversation(cid)
        self.assertEqual(conv["lifecycle"], "resolved")
        self.assertEqual(self.count(agent_runs), count)
        self.assert_error("conversation_not_open", lambda: self.service.takeover(cid,
            Takeover(expected_version=conv["row_version"]), uuid4().hex))
        self.assert_error("conversation_not_open", lambda: self.reply(cid))

    def test_normal_supported_reply_still_sends_once(self):
        cid, _ = self.create_mail()
        result, _ = self.execute(ScriptedModel(understanding([]), terminal()))
        self.assertEqual(result["outcome"], "reply_and_wait", result)
        self.assertEqual(len(self.outbound(cid)), 1)
        self.assertFalse(self.conversation(cid)["persistent_human"])
