"""A failed/unknown/source-changed negative must block paying for a positive review."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from bootstrap import digest
from run_request_controls import known_usage, validate_negative_history, effective_control_request


class RequestRunnerGuards(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.response = Path(self.temp.name) / "response.json"
        self.response.write_bytes(b"actual negative response")
        self.result = {"status": "awaiting_negative_fulltext_review", "source_changed_during_attempt": False,
            "within_original_budget": True, "observations": [{"status": "PASS", "actual_supported": False,
                "usage": {"prompt_tokens": 20, "completion_tokens": 4}, "checks": {"usage_known": True},
                "new_model_http_calls": 1}]}
        self.gate = {"status": "PASS", "reviewer": "coding_agent_semantic_review_not_external_business_owner",
            "negative_reply_failures_explicitly_explained": True, "actual_response_sha256": digest(self.response.read_bytes())}

    def test_accepted_actual_negative_source_allows_second_control(self):
        validate_negative_history(self.result, self.gate, self.response)

    def test_failed_unknown_or_changed_source_cannot_pay_for_positive(self):
        mutations = [("status", "FAIL"), ("usage", None), ("actual_supported", True), ("new_model_http_calls", 2)]
        for key, value in mutations:
            with self.subTest(key=key):
                result = deepcopy(self.result)
                result["observations"][0][key] = value
                with self.assertRaisesRegex(RuntimeError, "no_positive_HTTP"):
                    validate_negative_history(result, self.gate, self.response)
        result = deepcopy(self.result)
        result["source_changed_during_attempt"] = True
        with self.assertRaisesRegex(RuntimeError, "no_positive_HTTP"):
            validate_negative_history(result, self.gate, self.response)

    def test_semantic_gate_cannot_accept_a_different_raw_response(self):
        self.response.write_bytes(b"different response")
        with self.assertRaisesRegex(RuntimeError, "source_changed_no_positive_HTTP"):
            validate_negative_history(self.result, self.gate, self.response)

    def test_unknown_tokens_are_not_treated_as_zero_or_boolean_counts(self):
        self.assertFalse(known_usage(None))
        self.assertFalse(known_usage({"usage": {"prompt_tokens": None, "completion_tokens": 4}}))
        self.assertFalse(known_usage({"usage": {"prompt_tokens": True, "completion_tokens": 4}}))
        self.assertTrue(known_usage({"usage": {"prompt_tokens": 0, "completion_tokens": 0}}))

    def test_positive_timeout_cap_keeps_every_other_prepared_field_and_does_not_mutate(self):
        request = {"messages": [{"role": "user", "content": "Full original DATA"}],
            "schema": {"title": "OutcomeReview"}, "tools": None, "timeout": 60}
        original = deepcopy(request)
        self.assertEqual(effective_control_request(request, 61000), dict(original, timeout=59))
        self.assertEqual(effective_control_request(request, 20000), original)
        self.assertEqual(request, original)
        with self.assertRaisesRegex(RuntimeError, "no_HTTP"):
            effective_control_request(request, 120000)


if __name__ == "__main__":
    unittest.main()
