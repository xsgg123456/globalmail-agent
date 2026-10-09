"""Full context survives reply-schema pressure through actual PG and handoff."""
import json
from agent_fixture import AgentFixture, ScriptedModel, understanding, call
from globalmail_agent.adapters.conversation_schema import human_reviews
from globalmail_agent.adapters.agent_schema import tool_commands
from globalmail_agent.agent.budget import input_estimate
from globalmail_agent.agent.tool_schemas import schemas
from globalmail_agent.adapters.model_provider import prompt
from globalmail_agent.knowledge.base import canonical
from globalmail_agent.application.business_queries import BusinessQueries


class AgentMenuPressureTests(AgentFixture):
    def test_registered_but_undeclared_tool_is_not_executed_and_paid_usage_is_kept(self):
        cid, _ = self.create_mail("Please help with my lamp.")
        model = ScriptedModel(understanding,
            {"calls": [call("get_order_snapshot", {"display_order_number": "not-a-visible-order"})]})
        output, job = self.execute(model)
        names = {tool["function"]["name"] for tool in model.requests[-1]["tools"]}
        self.assertNotIn("get_order_snapshot", names)
        self.assertEqual(output, {"error_code": "model_tool_not_allowed"})
        ledger = self.budget_row(job)
        self.assertEqual(ledger["model_requests"], 2)
        self.assertEqual(ledger["input_tokens"], 40)
        self.assertEqual(ledger["output_tokens"], 20)
        self.assertEqual(ledger["unknown_requests"], 0)
        self.assertEqual(ledger["tool_calls"], 0)
        self.assertEqual(self.count(tool_commands), 0)
        self.assertEqual(self.count(human_reviews), 0)
        self.assertEqual(self.outbound(cid), [])

    def pressure_case(self, repeats):
        cid, _ = self.scene()
        number = BusinessQueries(self.engine).detail(cid)["data"]["orders"][0]["display_order_number"]
        detail = "Full customer detail. " * repeats
        self.append_mail(cid, "My order is " + number + ". " + detail)

        def candidate(messages):
            payload = json.loads(messages[-1]["content"])
            source = {"message_id": payload["messages"][-1]["message_id"], "quote": number}
            return understanding([], order_candidates=[{"value": number, "sources": [source]}])

        model = ScriptedModel(candidate,
            {"calls": [call("get_order_snapshot", {"display_order_number": number})]},
            {"calls": [call("request_human_review", {"reason": "cannot_decide",
                "summary": "Explicit engineering handoff with the complete customer context.",
                "gaps": ["This fixture measures menu reachability, not natural-language quality."], "draft": ""})]})
        output, job = self.execute(model)
        return cid, detail, model, output, job

    def test_full_context_handoff_fits_when_both_terminal_schemas_do_not(self):
        cid, detail, model, output, job = self.pressure_case(300)
        self.assertEqual(output.get("outcome"), "handoff", (output, len(model.requests)))
        request = model.requests[-1]
        names = {tool["function"]["name"] for tool in request["tools"]}
        both = input_estimate(request["messages"], schemas({"create_reply_draft", "request_human_review"}))
        human = input_estimate(request["messages"], request["tools"])
        self.assertGreater(both, 16000, (both, human, names))
        self.assertLessEqual(human, 16000, (both, human, names))
        self.assertEqual(names, {"request_human_review"}, (both, human, names))
        self.assertIn(detail, request["messages"][1]["content"])
        earlier = model.requests[-2]["messages"]
        self.assertEqual(request["messages"][:len(earlier) - 1], earlier[:-1])
        self.assertEqual(self.budget_row(job)["model_requests"], 3)
        self.assertEqual(self.budget_row(job)["tool_calls"], 2)
        self.assertEqual(self.budget_row(job)["unknown_requests"], 0)
        self.assertEqual(self.outbound(cid), [])

    def test_full_context_still_over_handoff_budget_does_not_fake_human_review(self):
        detail = "Full customer detail. " * 350
        cid, _ = self.create_mail(detail)
        values = []
        def candidate(messages):
            payload = json.loads(messages[-1]["content"])
            quote = "Full customer detail. " * 40
            source = {"message_id": payload["messages"][-1]["message_id"], "quote": quote}
            value = understanding([], facts=[{"key": "detail_" + str(n), "value": quote,
                "kind": "customer_report", "sources": [source]} for n in range(4)])
            values.append(value)
            return value
        model = ScriptedModel(candidate)
        output, job = self.execute(model)
        self.assertEqual(output, {"error_code": "input_budget_exceeded"})
        self.assertEqual(len(model.requests), 1)
        first = model.requests[0]
        self.assertLessEqual(input_estimate(first["messages"], [first["schema"]]), 16000)
        payload = json.loads(first["messages"][1]["content"])
        complete = [{"role": "system", "content": prompt("decision")},
            {"role": "user", "content": canonical({"context": payload, "understanding": values[0]}).decode()},
            {"role": "system", "content": prompt("grounding")}]
        self.assertGreater(input_estimate(complete, schemas({"request_human_review"})), 16000)
        self.assertIn(detail, complete[1]["content"])
        self.assertEqual(self.budget_row(job)["model_requests"], 1)
        self.assertEqual(self.budget_row(job)["tool_calls"], 0)
        self.assertEqual(self.count(human_reviews), 0)
        self.assertEqual(self.outbound(cid), [])
