"""Claims-first model input retains strict full-body validation and legacy receipts."""
import json
from agent_fixture import AgentFixture, ScriptedModel, understanding, draft, call
from globalmail_agent.adapters import agent_schema as a


def parts(*paragraphs, **changes):
    value = draft()
    value.pop("body")
    value["claims"] = [{"kind": "clarification", "text": text, "source_ids": []}
        for text in paragraphs]
    value.update(changes)
    return value


class ReplyPartsTests(AgentFixture):
    def test_ordered_parts_are_reviewed_and_committed_as_exact_complete_body(self):
        cid, _ = self.create_mail("Hallo, die Batterien sind neu.")
        paragraphs = ["Vielen Dank für Ihre Nachricht.", "Die Batterien sind neu.",
            "Haben Sie weitere Beobachtungen?\nBitte beschreiben Sie diese."]
        def reply(messages):
            message = json.loads(messages[1]["content"])["context"]["messages"][0]
            value = parts(*paragraphs, language="de")
            value["claims"][1].update(kind="customer_fact", source_ids=[message["message_id"]])
            return {"calls": [call("create_reply_draft", value)]}
        model = ScriptedModel(lambda messages: understanding(messages, language="de"), reply)
        output, job = self.execute(model)
        self.assertEqual(output.get("outcome"), "reply_and_wait", output)
        menu = next(row["function"]["parameters"] for row in model.requests[1]["tools"]
            if row["function"]["name"] == "create_reply_draft")
        self.assertNotIn("body", menu["properties"])
        self.assertNotIn("body", menu["required"])
        review = json.loads(model.requests[-1]["messages"][1]["content"])
        self.assertEqual(review["draft"]["body"], "\n\n".join(paragraphs))
        self.assertEqual([row["text"] for row in review["draft"]["claims"]], paragraphs)
        self.assertEqual(self.service.detail(cid)["messages"][-1]["body"], "\n\n".join(paragraphs))
        self.assertEqual(len(self.outbound(cid)), 1)
        self.assertEqual(self.budget_row(job)["model_requests"], 3)

    def test_parts_and_identical_legacy_body_reuse_same_normalized_receipt(self):
        self.create_mail()
        _, _, budget, gateway = self.components()
        value = parts("Thank you.", "Could you share your order number?")
        first_id, first = gateway.call(call("create_reply_draft", value, "same-normalized"))
        legacy = {**value, "body": "\n\n".join(row["text"] for row in value["claims"])}
        replay_id, replay = gateway.call(call("create_reply_draft", legacy, "same-normalized"))
        self.assertEqual(first_id, replay_id)
        self.assertEqual(first, replay)
        self.assertEqual(first["data"]["body"], legacy["body"])
        self.assertEqual(self.count(a.tool_commands), 1)
        self.assertEqual(self.budget_row(budget.job)["tool_calls"], 1)
        self.assert_error("tool_command_conflict", lambda: gateway.call(call("create_reply_draft",
            {**legacy, "body": legacy["body"] + " A refund succeeded."}, "same-normalized")))

    def test_invalid_parts_reject_before_tool_budget_and_empty_mail_never_passes_review(self):
        cid, _ = self.create_mail()
        _, _, budget, gateway = self.components()
        self.assert_error("tool_parameters_invalid", lambda: gateway.call(
            {"id": "invalid-json-type", "name": "create_reply_draft", "arguments": {}}))
        for value in (parts("Thank you.", workspace_id="forged"),
                parts("Thank you.", body=None),
                parts(*["x" * 1900] * 5), parts("Thank you.", claims=[{"kind": "clarification",
                    "text": 123, "source_ids": []}])):
            with self.subTest(value=str(value)[:50]):
                self.assert_error("tool_parameters_invalid", lambda: gateway.call(call("create_reply_draft", value)))
        self.assertEqual(self.count(a.tool_commands), 0)
        self.assertEqual(self.budget_row(budget.job)["tool_calls"], 0)
        bad = {"calls": [call("create_reply_draft", parts())]}
        model = ScriptedModel(understanding, bad,
            {"calls": [call("create_reply_draft", parts())]}, reviews=[])
        output, _ = self.execute(model, budget.job)
        self.assertEqual(output.get("error_code"), "reply_body_required", output)
        self.assertEqual(len(model.requests), 3)
        self.assertEqual(self.outbound(cid), [])

    def test_malicious_parts_still_require_full_semantic_rejection(self):
        cid, _ = self.create_mail()
        body = "Your refund was completed successfully."
        denial = {"supported": False, "language_correct": True, "unsupported_claims": [body],
            "reason": "No successful scoped refund ledger exists."}
        model = ScriptedModel(understanding, {"calls": [call("create_reply_draft", parts(body))]},
            {"calls": [call("create_reply_draft", parts(body))]}, reviews=[denial, denial])
        output, job = self.execute(model)
        self.assertEqual(output.get("error_code"), "reply_grounding_invalid", output)
        self.assertEqual(len(model.requests), 5)
        self.assertEqual(self.budget_row(job)["model_requests"], 5)
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.count(a.reply_artifacts), 0)
