"""The audited identity exceptions must not hide changed ledger or SOP facts."""
from copy import deepcopy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from uuid import uuid4
from bootstrap import ROOT, digest
from draft_prefix import DraftPrefixReplay


class DraftAuditTests(unittest.TestCase):
    def build(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        orders = {"command_source_id": "command:" + str(uuid4()), "status": "ok",
            "data": {"orders": [{"customer_id": str(uuid4()), "paid_minor": 5499}]},
            "evidence_refs": [{"evidence_id": "branch:" + str(uuid4())}],
            "observed_at": "2026-10-08T10:00:00+00:00", "resource_versions": {"business_digest": "a" * 64}}
        evidence_id = str(uuid4())
        knowledge = {"command_source_id": "command:" + str(uuid4()), "status": "ok",
            "data": {"evidence": [{"evidence_id": evidence_id, "text": "Complete frozen SOP.", "version_number": 1}]},
            "evidence_refs": [{"evidence_id": evidence_id}],
            "observed_at": "2026-10-08T10:00:01+00:00", "resource_versions": {"business_digest": "a" * 64}}
        old_messages = [{"role": "tool", "tool_call_id": f"call_{i}", "content": json.dumps(result)}
            for i, result in enumerate((orders, knowledge))]
        fresh = deepcopy((orders, knowledge))
        for result in fresh:
            result["command_source_id"] = "command:" + str(uuid4())
            result["observed_at"] = "2026-10-08T11:00:00+00:00"
            result["resource_versions"]["business_digest"] = "b" * 64
        fresh[0]["data"]["orders"][0]["customer_id"] = str(uuid4())
        fresh[0]["evidence_refs"][0]["evidence_id"] = "branch:" + str(uuid4())
        new_evidence = str(uuid4())
        fresh[1]["data"]["evidence"][0]["evidence_id"] = new_evidence
        fresh[1]["evidence_refs"][0]["evidence_id"] = new_evidence
        model = type("NeverCall", (), {"model": "qwen3.7-plus", "configured": True})()
        loaded = ({}, [{}, {}, {}, {"messages": old_messages}], [], {})
        adapter = DraftPrefixReplay(model, loaded, Path(temporary.name))
        return adapter, fresh

    @staticmethod
    def messages(results):
        return [{"role": "tool", "tool_call_id": f"call_{i}", "content": json.dumps(result)}
            for i, result in enumerate(results)]

    def test_only_identity_and_observation_metadata_may_change(self):
        adapter, fresh = self.build()
        adapter.compare_observations(self.messages(fresh))
        self.assertEqual(len(adapter.current_observations), 2)

    def test_changed_business_amount_is_rejected(self):
        adapter, fresh = self.build()
        fresh[0]["data"]["orders"][0]["paid_minor"] += 1
        with self.assertRaisesRegex(RuntimeError, "business_or_full_knowledge_changed"):
            adapter.compare_observations(self.messages(fresh))

    def test_changed_full_sop_text_is_rejected(self):
        adapter, fresh = self.build()
        fresh[1]["data"]["evidence"][0]["text"] += " invented action"
        with self.assertRaisesRegex(RuntimeError, "business_or_full_knowledge_changed"):
            adapter.compare_observations(self.messages(fresh))

    def test_plain_assistant_content_alongside_tool_call_is_preserved(self):
        adapter, _ = self.build()
        response = {"content": "I need the current order before selecting a scoped reference.",
            "calls": [{"id": "call_order", "name": "get_order_snapshot", "arguments": '{"order_number":"999-7100002-8100000"}'}],
            "request_id": "paid-original", "usage": {"prompt_tokens": 100, "completion_tokens": 10}}
        adapter.loaded = (*adapter.loaded[:2], [{}, response], {"origin_attempt_id": "accepted",
            "origin_sampling": {"temperature": 0.7}})
        adapter.index = 1
        actual = adapter.request([], tools=[{"name": "get_order_snapshot"}])
        self.assertEqual(actual["content"], response["content"])
        self.assertEqual(json.loads(actual["calls"][0]["arguments"]), json.loads(response["calls"][0]["arguments"]))
        self.assertFalse(actual["_eval_provenance"]["new_http_call"])

    @unittest.skipUnless((ROOT / "tmp/phase7-agent-eval/20261008-191114-7c80c70b/P7-03-attempts-failed/response-02.json").exists(),
        "actual private historical payload is unavailable in this checkout")
    def test_actual_191114_second_response_content_arguments_and_origin_preserved(self):
        source = ROOT / "tmp/phase7-agent-eval/20261008-191114-7c80c70b/P7-03-attempts-failed/response-02.json"
        original_hash = digest(source.read_bytes())
        response = json.loads(source.read_text(encoding="utf-8"))
        with self.assertRaises(json.JSONDecodeError):
            json.loads(response["content"])
        adapter, _ = self.build()
        adapter.loaded = (*adapter.loaded[:2], [{}, response], {"origin_attempt_id": "20261008-191114-7c80c70b",
            "origin_sampling": {"temperature": 0.7}})
        adapter.index = 1
        actual = adapter.request([], tools=[{"name": "get_order_snapshot"}])
        self.assertEqual(actual["content"], response["content"])
        self.assertEqual(len(actual["calls"]), len(response["calls"]))
        for old, new in zip(response["calls"], actual["calls"]):
            self.assertEqual({k: v for k, v in old.items() if k != "arguments"},
                {k: v for k, v in new.items() if k != "arguments"})
            self.assertEqual(json.loads(old["arguments"]), json.loads(new["arguments"]))
        self.assertEqual({k: v for k, v in actual.items() if k not in ("calls", "_eval_provenance")},
            {k: v for k, v in response.items() if k != "calls"})
        self.assertEqual(actual["_eval_provenance"]["origin_provider_request_id"], response["request_id"])
        self.assertEqual(original_hash, digest(source.read_bytes()))


if __name__ == "__main__":
    unittest.main()
