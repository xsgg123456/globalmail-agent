"""Saved history incompatibility must stop before any services or embedding initialization."""
import sys
import unittest
from unittest.mock import patch
from bootstrap import ROOT, frozen_inputs
from eval_options import options
from history_seed import load_seed


class LegacyHistoryTests(unittest.TestCase):
    def test_old_paid_review_is_explicitly_incompatible_without_mutating_raw(self):
        cases, _ = frozen_inputs()
        source = ROOT / "tmp/phase7-agent-eval/20261008-172034-8484f882/P7-01-missing-order/response-03.json"
        if not source.exists():
            self.skipTest("private_saved_history_unavailable")
        before = source.read_bytes()
        with self.assertRaisesRegex(RuntimeError, "legacy_history_review_incompatible_no_initialization_or_Embedding_HTTP"):
            load_seed("20261008-172034-8484f882", cases["closed_loop"]["messages"][0])
        self.assertEqual(source.read_bytes(), before)

    def test_history_CLI_stops_before_service_setup_and_prefix_load(self):
        with (patch.object(sys, "argv", ["run_eval.py", "--group", "closed-loop", "--seed-attempt",
                "20261008-172034-8484f882", "--prefix-attempt", "20261008-182447-c623f2cd"]),
                patch("prefix_replay.load_prefix") as prefix, patch("bootstrap.prepare") as prepare):
            with self.assertRaisesRegex(RuntimeError, "legacy_history_review_incompatible"):
                options()
            prefix.assert_not_called()
            prepare.assert_not_called()

    def test_prefix_engineering_entry_stops_before_embedding_or_DB_setup(self):
        import audit_draft_prefix
        with (patch.object(audit_draft_prefix, "prepare") as prepare,
                patch.object(audit_draft_prefix, "isolated_database_environment") as setup):
            with self.assertRaisesRegex(RuntimeError, "legacy_history_review_incompatible"):
                audit_draft_prefix.main()
            prepare.assert_not_called()
            setup.assert_not_called()

    def test_fresh_conditional_refund_filter_does_not_load_history(self):
        with patch.object(sys, "argv", ["run_eval.py", "--group", "boundaries", "--case", "P7-06-conditional-refund",
                "--limit", "1", "--semantic-gate"]), patch("history_seed.load_seed") as load:
            args, _, _, first, prefix, second, third = options()
            self.assertEqual(args.case, "P7-06-conditional-refund")
            self.assertTrue(args.semantic_gate)
            self.assertEqual((first, prefix, second, third), (None, None, None, None))
            load.assert_not_called()


if __name__ == "__main__":
    unittest.main()
