"""Use original P7-06 material to verify the contrast does not hide wrong understanding."""
from copy import deepcopy
import json
import unittest
from bootstrap import ROOT
from prepare_request_controls import AFTER, BEFORE, CASE, ORIGIN, PREFERENCE, synthetic_positive


class RequestControlTests(unittest.TestCase):
    def original(self):
        path = ROOT / "tmp/phase7-agent-eval" / ORIGIN / CASE / "request-05.json"
        if not path.exists():
            self.skipTest("private_actual_request_unavailable")
        return json.loads(json.loads(path.read_text(encoding="utf-8"))["messages"][1]["content"])

    def test_wrong_understanding_all_evidence_and_unchanged_claim_sources_retained(self):
        original = self.original()
        unchanged = deepcopy(original)
        positive, audit = synthetic_positive(original)
        self.assertEqual(original, unchanged)
        self.assertEqual(positive["understanding"], original["understanding"])
        self.assertEqual(positive["understanding"]["intents"][0]["business_type"], "troubleshooting")
        self.assertIsNone(positive["understanding"]["intents"][0]["condition"])
        self.assertEqual(positive["context"], original["context"])
        self.assertEqual(positive["observations"], original["observations"])
        self.assertEqual(positive["draft"]["claims"][1]["source_ids"], original["draft"]["claims"][1]["source_ids"])
        self.assertEqual(positive["draft"]["body"], original["draft"]["body"].replace(BEFORE, AFTER, 1) + "\n\n" + PREFERENCE)
        self.assertEqual(positive["draft"]["claims"][3], {"kind": "customer_fact", "text": PREFERENCE,
            "source_ids": [original["context"]["messages"][0]["message_id"]]})
        self.assertEqual(len(audit["operations"]), 4)

    def test_no_preference_source_or_changed_product_prefix_refuses_preparation(self):
        original = self.original()
        original["context"]["messages"][0]["body"] = "Where is my parcel?"
        with self.assertRaisesRegex(RuntimeError, "source_not_unique"):
            synthetic_positive(original)
        original = self.original()
        positive, _ = synthetic_positive(original)
        with self.assertRaisesRegex(RuntimeError, "claim_structure_changed"):
            synthetic_positive(positive)


if __name__ == "__main__":
    unittest.main()
