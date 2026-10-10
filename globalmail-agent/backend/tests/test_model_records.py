"""Full request/response and failure snapshots are actual execution receipts, not fixture UI rows."""
from agent_fixture import AgentFixture, ScriptedModel, understanding, terminal
from globalmail_agent.application.run_records import RunRecords
from globalmail_agent.application.conversation_lock import ServiceError


class ModelRecordTests(AgentFixture):
    def test_each_request_preserves_full_messages_schema_tools_output_and_reasoning(self):
        cid, rid = self.create_mail()
        model = ScriptedModel(understanding([]), {**terminal(), "reasoning_content": "supplier returned sample"})
        result, _ = self.execute(model)
        self.assertEqual(result["outcome"], "reply_and_wait")
        records = RunRecords(self.engine, self.store).get(rid)["model_calls"]
        self.assertEqual(len(records), 3)
        for saved, executed in zip(records, model.requests):
            self.assertEqual(saved["request"]["messages"], executed["messages"])
            self.assertEqual(saved["request"]["response_schema"], executed["schema"])
            self.assertEqual(saved["request"]["tools"], executed["tools"] or [])
            self.assertEqual(saved["status"], "completed")
        self.assertEqual(records[1]["response"]["reasoning_content"], "supplier returned sample")
        self.assertEqual(records[1]["reasoning_state"], "returned")
        self.assertEqual(records[0]["reasoning_state"], "not_returned")

    def test_timeout_attempts_have_distinct_failed_receipts_and_unknown_usage(self):
        cid, rid = self.create_mail()
        result, _ = self.execute(ScriptedModel(ServiceError("model_timeout", 503), ServiceError("model_timeout", 503)))
        self.assertEqual(result["error_code"], "model_timeout")
        records = RunRecords(self.engine, self.store).get(rid)["model_calls"]
        self.assertEqual(len(records), 2)
        self.assertEqual(len({r["request_key"] for r in records}), 2)
        for record in records:
            self.assertEqual(record["status"], "failed")
            self.assertEqual(record["error_code"], "model_timeout")
            self.assertIsNone(record["response"])
            self.assertIsNone(record["input_tokens"])
        self.assertEqual(self.outbound(cid), [])
