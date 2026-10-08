"""Policy evidence, immutable bundle and public-command regression cases."""
import copy
import hashlib
import importlib.util
import json
import unittest
from pydantic import ValidationError
from globalmail_agent.domain.policy import EligibilityRequest, evaluate_eligibility
from policy_helpers import ROOT, V1, context, command, statuses


class PublicCommandTests(unittest.TestCase):
    def test_numbers_are_strict_integers_and_no_scope_or_evidence_parameters(self):
        for field, values in (("quantity", [True, 1.0, "1", 0, -1]),
                              ("amount_minor", [True, 2.0, "2", -1])):
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValidationError):
                    EligibilityRequest.model_validate({"action": "refund", field: value})
        for field in ("evidence", "scope", "consent_ref", "customer_id", "policy_version", "as_of"):
            with self.subTest(field=field), self.assertRaises(ValidationError):
                EligibilityRequest.model_validate({"action": "refund", field: "forged"})

    def test_full_refund_calculates_but_never_authorizes_and_is_pure(self):
        inputs = context()
        before = copy.deepcopy(inputs)
        result = evaluate_eligibility(command(), inputs)
        self.assertEqual(result["outcome"], "eligible")
        self.assertFalse(result["authorized"])
        self.assertEqual(result["publication_status"], "unpublished")
        self.assertEqual(result["remaining_refund_minor"], 10001)
        self.assertTrue(result["decision_id"].startswith("preview-"))
        self.assertEqual(evaluate_eligibility(command(), inputs), result)
        self.assertEqual(inputs, before)

    def test_policy_scope_and_time_are_checked_without_current_fallback(self):
        for key, value in (("market", "FR"), ("brand", "other-brand"), ("channel", "other-channel")):
            inputs = context()
            inputs["order"][key] = value
            self.assertEqual(evaluate_eligibility(command(), inputs)["outcome"], "ineligible")
        inputs = context()
        inputs["as_of"] = "2026-10-01T12:00:00+08:00"
        self.assertIn("ineligible", statuses(evaluate_eligibility(command(), inputs), "policy_time"))
        inputs = context()
        inputs["mode"] = "historical_replay"
        self.assertIn("ineligible", statuses(evaluate_eligibility(command(), inputs), "policy_scope"))

    def test_newest_visible_choice_must_accept_exact_amount_currency_and_action(self):
        for patch in ({"currency": "EUR"}, {"amount_minor": 10000}, {"kind": "return"},
                      {"quantity": True}, {"accepted": False}, {"source_message_id": "future-message"},
                      {"order_line_id": "another-line"}):
            inputs = context()
            inputs["state"]["customer_choices"][0].update(patch)
            result = evaluate_eligibility(command(), inputs)
            self.assertIn("needs_input", statuses(result, "customer_choice"))
        inputs = context()
        rejected = copy.deepcopy(inputs["state"]["customer_choices"][0])
        rejected["accepted"] = False
        inputs["state"]["customer_choices"].append(rejected)
        self.assertEqual(evaluate_eligibility(command(), inputs)["outcome"], "needs_input")

    def test_visual_evidence_is_not_order_money_or_warehouse_ledger(self):
        for entity in ("order", "line"):
            inputs = context()
            inputs[entity]["source_kind"] = "visual_observation"
            result = evaluate_eligibility(command(), inputs)
            self.assertNotEqual(result["outcome"], "eligible")
            self.assertIsNone(result["remaining_refund_minor"])
        inputs = context()
        inputs["state"]["returns"][0]["source_kind"] = "visual_observation"
        result = evaluate_eligibility(command(), inputs)
        self.assertNotIn("fulfilled", statuses(result, "warehouse_receipt"))

    def test_v1_missing_mapping_rejects_visual_and_v2_only_accepts_clear_outer_defect(self):
        for version, expected in ((1, "requires_review"), (2, "eligible")):
            inputs = context(action="spare_part", version=version)
            inputs["state"]["problem_evidence"][0]["source_kind"] = "visual_observation"
            self.assertEqual(evaluate_eligibility(command(action="spare_part"), inputs)["outcome"], expected)
        for patch in ({"reason": "missing"}, {"uncertain": True}, {"kind": "hypothesis"}):
            inputs = context(action="spare_part")
            inputs["state"]["problem_evidence"][0].update(source_kind="visual_observation", **patch)
            self.assertIn("needs_input", statuses(evaluate_eligibility(command(action="spare_part"), inputs), "reported_problem"))


class BundleTests(unittest.TestCase):
    def test_same_version_rules_readable_hashes_and_original_v1_bytes(self):
        path = ROOT / "data/knowledge/v2/build_policy.py"
        spec = importlib.util.spec_from_file_location("build_policy", path)
        build = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(build)
        for name, content in build.artifacts().items():
            self.assertEqual((path.parent / name).read_bytes(), content)
        bundle = json.loads((path.parent / "policy-bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(bundle["publication_status"], "unpublished")
        self.assertEqual(bundle["content_review_status"], "pending")
        for name, value in bundle["v1_reference"]["files"].items():
            self.assertEqual(hashlib.sha256((path.parent.parent / "v1" / name).read_bytes()).hexdigest(), value)
        policy = json.loads((path.parent / "policies/policy-profile.json").read_text(encoding="utf-8"))
        for section in build.RULE_SECTIONS:
            self.assertEqual(policy[section], V1[section])
        bad = copy.deepcopy(policy)
        bad["refund"]["partial_offer_max_basis_points"] = 2000.0
        with self.assertRaises(ValueError):
            build.validate(bad, V1)


if __name__ == "__main__":
    unittest.main()
