"""Exact roundtrip and original source bindings for an isolated format experiment."""
from unittest import TestCase
from globalmail_agent.agent.review_audit import audit_sources
from globalmail_agent.knowledge.base import canonical
from review_observations import original_observations, parsed_observations


class ObservationPresentationTests(TestCase):
    def rows(self):
        return [{"role": "tool", "tool_call_id": "call-1", "content": canonical({
            "status": "ok", "command_source_id": "command:one", "metadata": {"scope": "one"},
            "data": {"number": 1.5, "null": None, "boolean": False, "nested": [1, {"text": "中文\n\"quoted\"\\path"}],
                "evidence": [{"evidence_id": "ref:one", "text": "完整资料\n第二行"}]}}).decode()}]

    def test_roundtrip_preserves_every_value_and_original_raw_content(self):
        original = self.rows()
        decoded = parsed_observations(original)
        self.assertEqual(original_observations(decoded), original)
        self.assertIsInstance(decoded[0]["content"], dict)
        self.assertIsInstance(original[0]["content"], str)
        self.assertEqual(decoded[0]["role"], original[0]["role"])
        self.assertEqual(decoded[0]["tool_call_id"], original[0]["tool_call_id"])

    def test_complete_current_source_id_and_canonical_body_stay_identical(self):
        context = {"messages": [], "human_notes": []}
        original = self.rows()
        self.assertEqual(audit_sources(context, original),
            audit_sources(context, original_observations(parsed_observations(original))))

    def test_noncanonical_or_malformed_input_is_not_silently_repaired(self):
        for content in ('{ "status": "ok" }', 'not JSON'):
            with self.assertRaises((RuntimeError, ValueError)):
                parsed_observations([{"content": content}])
