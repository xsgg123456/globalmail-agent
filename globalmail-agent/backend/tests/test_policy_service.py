"""Service propagates safe scoped failures and performs no write/fallback."""
import unittest
from globalmail_agent.application.eligibility import EligibilityService
from policy_helpers import context, command


class Queries:
    def __init__(self, result):
        self.result, self.calls = result, []

    def eligibility_context(self, conversation_id, order_line_id):
        self.calls.append((conversation_id, order_line_id))
        return self.result


def service(result):
    value = EligibilityService.__new__(EligibilityService)
    value.queries = Queries(result)
    return value


class ServiceTests(unittest.TestCase):
    def test_scoped_denials_and_technical_failures_are_returned_without_reinterpretation(self):
        for status in ("empty", "needs_input", "denied", "unavailable", "unknown", "error"):
            original = {"status": status, "reason_code": "safe_reason", "data": None, "source_kind": "unknown"}
            value = service(original)
            self.assertIs(value.preview("conversation-1", command()), original)
            self.assertEqual(value.queries.calls, [("conversation-1", "line-1")])

    def test_missing_policy_stays_unavailable_without_v2_or_current_fallback(self):
        inputs = context()
        inputs["policy"] = None
        result = service({"status": "ok", "data": inputs}).preview("conversation-1", command())
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason_code"], "policy_unavailable")
        self.assertIsNone(result["data"])

    def test_unpublished_preview_preserves_queries_provenance_and_no_execute_method(self):
        original = {"status": "ok", "reason_code": "context", "data": context(version=1),
            "evidence_refs": ["order-evidence"], "source_kind": "synthetic", "simulation": True,
            "observed_at": "2026-10-08T10:00:00+08:00", "resource_versions": {"policy": "1.0.1"}}
        value = service(original)
        result = value.preview("conversation-1", command())
        self.assertEqual(result["data"]["version"], "1.0.1")
        self.assertEqual(result["data"]["outcome"], "eligible")
        self.assertFalse(result["data"]["authorized"])
        self.assertEqual(result["evidence_refs"], original["evidence_refs"])
        self.assertEqual(result["resource_versions"], original["resource_versions"])
        self.assertFalse(hasattr(value, "execute"))

    def test_invalid_or_unsupported_policy_returns_safe_gap(self):
        for patch in ({"version": "future-version"}, {"refund": {"partial_offer_max_basis_points": True}}):
            inputs = context()
            inputs["policy"].update(patch)
            result = service({"status": "ok", "data": inputs}).preview("conversation-1", command())
            self.assertEqual(result["status"], "unavailable")
            self.assertIsNone(result["data"])


if __name__ == "__main__":
    unittest.main()
