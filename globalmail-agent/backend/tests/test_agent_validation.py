"""Validation protocol failures are frozen explicitly, never model-quality evidence."""
from agent_fixture import AgentFixture, ScriptedModel, understanding, terminal, draft, call
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.application.commit_outcome import commit_outcome


def rejected(reason):
    return {"supported": False, "language_correct": True, "unsupported_claims": [reason], "reason": reason}


class AgentValidationTests(AgentFixture):
    def test_missing_fact_source_repairs_before_paid_review_and_sends_only_valid_draft(self):
        import json
        for kind, code, sources in (("customer_fact", "customer_fact_without_message", []),
                ("order_fact", "order_fact_without_tool", ["visible_message"])):
            with self.subTest(kind=kind):
                cid, _ = self.create_mail(email=f"source-repair-{kind}@example.test")
                def invalid(messages):
                    source = json.loads(messages[1]["content"])["context"]["messages"][0]["message_id"]
                    return terminal("Thank you for your message.", claims=[{"kind": kind,
                        "text": "Thank you for your message.", "source_ids": [source] if sources else []}])
                model = ScriptedModel(understanding, invalid, terminal())
                output, job = self.execute(model)
                self.assertEqual(output.get("outcome"), "reply_and_wait", output)
                self.assertEqual(len(model.requests), 4)
                self.assertIsNone(model.requests[2]["schema"])
                self.assertIn(code, model.requests[2]["messages"][-2]["content"])
                complete = [json.loads(m["content"])["rejected_terminal_result"]["data"]
                    for m in model.requests[2]["messages"] if m["role"] == "user"
                    and m["content"].startswith('{"provider_tool_call_id"')]
                self.assertEqual(complete[0]["body"], "Thank you for your message.")
                self.assertEqual(complete[0]["claims"][0]["kind"], kind)
                self.assertEqual(sum("supported" in (r["schema"] or {}).get("properties", {})
                    for r in model.requests), 1)
                self.assertEqual(self.budget_row(job)["model_requests"], 4)
                self.assertEqual(len(self.outbound(cid)), 1)
                self.assertEqual(self.service.detail(cid)["messages"][-1]["body"], draft()["body"])

    def test_repeated_missing_fact_sources_never_call_semantic_review_or_commit(self):
        cid, _ = self.create_mail()
        bad = terminal("Thank you.", claims=[{"kind": "customer_fact", "text": "Thank you.", "source_ids": []}])
        model = ScriptedModel(understanding, bad, bad, reviews=[])
        output, job = self.execute(model)
        self.assertEqual(output.get("error_code"), "customer_fact_without_message", output)
        self.assertEqual(len(model.requests), 3)
        self.assertEqual(sum("supported" in (r["schema"] or {}).get("properties", {})
            for r in model.requests), 0)
        self.assertEqual(self.budget_row(job)["model_requests"], 3)
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.count(a.reply_artifacts), 0)

    def test_last_two_requests_preserve_history_and_offer_only_terminal_tools(self):
        cid, _ = self.create_mail("Original complete customer text retained for final validation.")
        job, _, budget, _ = self.components()
        for _ in range(3):
            key = budget.reserve([{"role": "user", "content": "earlier attempts"}], "decision", "qwen3.7-plus")
            budget.settle(key, {"prompt_tokens": 20, "completion_tokens": 10})
        model = ScriptedModel(understanding, terminal())
        output, _ = self.execute(model, job)
        self.assertEqual(output.get("outcome"), "reply_and_wait", output)
        self.assertEqual({tool["function"]["name"] for tool in model.requests[1]["tools"]},
            {"create_reply_draft", "request_human_review"})
        self.assertIn("Original complete customer text retained", model.requests[1]["messages"][1]["content"])
        self.assertEqual(self.budget_row(job)["model_requests"], 6)
        self.assertEqual(len(self.outbound(cid)), 1)

    def test_validation_retains_full_tool_observations_without_duplicate_draft(self):
        cid, _ = self.create_mail("Visible full customer question.")
        model = ScriptedModel(understanding, {"calls": [call("get_case_context", {})]}, terminal())
        output, _ = self.execute(model)
        self.assertEqual(output.get("outcome"), "reply_and_wait", output)
        import json
        request = model.requests[-1]
        review = json.loads(next(message["content"] for message in request["messages"] if message["role"] == "user"))
        self.assertEqual(len(review["observations"]), 1)
        observation = json.loads(review["observations"][0]["content"])
        self.assertEqual(observation["data"]["messages"][0]["body"], "Visible full customer question.")
        self.assertEqual(review["draft"]["body"], draft()["body"])
        self.assertEqual(request["messages"][-1]["role"], "system")
        self.assertIn("FULL clause", request["messages"][-1]["content"])

    def test_last_request_only_offers_handoff_and_never_sends_unvalidated_reply(self):
        cid, _ = self.create_mail("Complete customer history at the final request.")
        job, _, budget, _ = self.components()
        for _ in range(4):
            key = budget.reserve([{"role": "user", "content": "prior bounded activity"}], "decision", "qwen3.7-plus")
            budget.settle(key, {"prompt_tokens": 20, "completion_tokens": 10})
        handoff = {"reason": "cannot_decide", "summary": "No budget remains for independent validation.",
            "gaps": ["Human review is required."], "draft": ""}
        model = ScriptedModel(understanding, {"calls": [call("request_human_review", handoff)]})
        output, _ = self.execute(model, job)
        self.assertEqual(output.get("outcome"), "handoff", output)
        self.assertEqual({tool["function"]["name"] for tool in model.requests[1]["tools"]}, {"request_human_review"})
        self.assertIn("Complete customer history", model.requests[1]["messages"][1]["content"])
        self.assertIn("WHETHER", model.requests[1]["messages"][-1]["content"])
        self.assertEqual(self.budget_row(job)["model_requests"], 6)
        self.assertEqual(self.outbound(cid), [])

    def test_repair_retains_complete_rejected_result_and_read_observations_once(self):
        import json
        cid, _ = self.create_mail("Entire customer message remains visible after rejection.")
        bad = "When you previously tried pairing, did the lamp flash?"
        model = ScriptedModel(understanding, {"calls": [call("get_case_context", {}, "read-full")]},
            terminal(bad), terminal(), reviews=[rejected("No customer source reports pairing."), {
                "supported": True, "language_correct": True, "unsupported_claims": [], "reason": "Engineering approval."}])
        output, job = self.execute(model)
        self.assertEqual(output.get("outcome"), "reply_and_wait", output)
        repaired = model.requests[4]["messages"]
        observations = [row for row in repaired if row["role"] == "tool"]
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0]["tool_call_id"], "read-full")
        self.assertEqual(json.loads(observations[0]["content"])["data"]["messages"][0]["body"],
            "Entire customer message remains visible after rejection.")
        results = [json.loads(row["content"]) for row in repaired if row["role"] == "user"
            and row["content"].startswith('{"provider_tool_call_id"')]
        self.assertEqual(len(results), 1)
        result = results[0]["rejected_terminal_result"]
        self.assertEqual(result["data"]["body"], bad)
        self.assertEqual(result["data"]["claims"], draft(bad)["claims"])
        self.assertIsNone(result["data"]["waiting_operation_id"])
        self.assertTrue(result["command_source_id"].startswith("command:"))
        self.assertFalse(any(call["function"]["name"] == "create_reply_draft" for row in repaired
            if row["role"] == "assistant" for call in row.get("tool_calls", [])))
        self.assertEqual(self.budget_row(job)["model_requests"], 6)
        self.assertEqual(len(self.outbound(cid)), 1)

    def test_malicious_clarification_financial_success_or_disassembly_is_rejected(self):
        for index, body in enumerate(("Your refund has been completed successfully.",
                "Open the power supply and dismantle the energized lamp.",
                "When you previously tried pairing, did the lamp flash?")):
            with self.subTest(body=body):
                cid, rid = self.create_mail(email=f"validation-{index}@example.test")
                model = ScriptedModel(understanding, terminal(body), terminal(body),
                    reviews=[rejected("No tool or applicable document supports this claim.")] * 2)
                output, job = self.execute(model)
                self.assertEqual(output.get("error_code"), "reply_grounding_invalid", output)
                self.assertEqual(len(model.requests), 5)
                self.assertEqual(self.budget_row(job)["model_requests"], 5)
                self.assertEqual(sum("supported" in (request["schema"] or {}).get("properties", {})
                    for request in model.requests), 2)
                self.assertEqual(self.outbound(cid), [])
                self.assertEqual(self.controls.get(rid)["run"]["status"], "failed")

    def test_claim_coverage_missing_sentence_is_rejected_without_semantic_request(self):
        cid, rid = self.create_mail()
        body = "Please provide the order number. A refund was completed."
        claims = [{"kind": "clarification", "text": "Please provide the order number.", "source_ids": []}]
        model = ScriptedModel(understanding, terminal(body, claims=claims), terminal(body, claims=claims))
        output, job = self.execute(model)
        self.assertEqual(output.get("error_code"), "reply_claims_incomplete", output)
        self.assertEqual(len(model.requests), 3)
        self.assertEqual(self.budget_row(job)["model_requests"], 3)
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.count(a.reply_artifacts), 0)

    def test_validated_hash_does_not_authorize_modified_or_unreviewed_body(self):
        cid, _ = self.create_mail()
        job, context, _, _ = self.components()
        self.assert_error("reply_not_validated", lambda: commit_outcome(self.engine, self.store, context, job,
            understanding([]), {"kind": "reply", "data": draft()}))
        original = draft()
        self.approve_fixture_draft(context, job, original)
        changed = draft("Please also send your address.")
        self.assert_error("reply_not_validated", lambda: commit_outcome(self.engine, self.store, context, job,
            understanding([]), {"kind": "reply", "data": changed}))
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.count(a.reply_artifacts), 0)

    def test_one_repair_can_replace_rejected_draft_before_atomic_send(self):
        cid, rid = self.create_mail()
        bad, good = "Your refund succeeded.", "Please provide the order number."
        approved = {"supported": True, "language_correct": True, "unsupported_claims": [],
            "reason": "Explicit engineering approval of clarification."}
        model = ScriptedModel(understanding, terminal(bad), terminal(good),
            reviews=[rejected("Refund has no receipt."), approved])
        output, job = self.execute(model)
        self.assertEqual(output.get("outcome"), "reply_and_wait", output)
        self.assertEqual(len(model.requests), 5)
        self.assertEqual(self.budget_row(job)["model_requests"], 5)
        self.assertEqual(len(self.outbound(cid)), 1)
        mails = self.service.detail(cid)["messages"]
        self.assertEqual(mails[-1]["body"], good)
        self.assertEqual(self.count(a.reply_artifacts), 1)
