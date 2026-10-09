"""Material regression: H11 contrast retains full evidence and the literal questions."""
from copy import deepcopy
import json
import unittest
from bootstrap import ROOT
from prepare_cause_controls import CASE, ORIGIN, REMOVED, synthetic_positive


class CauseControlTests(unittest.TestCase):
    def original(self):
        path = ROOT / "tmp/phase7-agent-eval" / ORIGIN / CASE / "request-06.json"
        if not path.exists():
            self.skipTest("private_actual_request_unavailable")
        return json.loads(json.loads(path.read_text(encoding="utf-8"))["messages"][1]["content"])

    def test_actual_evidence_questions_sources_and_claim_order_retained(self):
        original = self.original()
        before = deepcopy(original)
        positive, audit = synthetic_positive(original)
        self.assertEqual(original, before)
        self.assertEqual(audit["modified_fields"], ["draft.body", "draft.claims[2].text"])
        self.assertEqual(positive["context"], original["context"])
        self.assertEqual(positive["observations"], original["observations"])
        expected = deepcopy(original)
        expected["draft"]["body"] = expected["draft"]["body"].replace(REMOVED, "", 1)
        expected["draft"]["claims"][2]["text"] = expected["draft"]["claims"][2]["text"].replace(REMOVED, "", 1)
        self.assertEqual(positive, expected)
        self.assertEqual(positive["draft"]["claims"][2]["text"],
            "Haben Sie die Fernbedienung schon einmal mit der Lampe gekoppelt (gepairt)?")
        self.assertEqual(positive["draft"]["body"], "\n\n".join(c["text"] for c in positive["draft"]["claims"]))
        self.assertEqual(positive["draft"]["citation_ids"], original["draft"]["citation_ids"])

    def test_missing_or_duplicate_causal_sentence_refuses_preparation(self):
        original = self.original()
        positive, _ = synthetic_positive(original)
        with self.assertRaisesRegex(RuntimeError, "expected_one_body_and_one_claim"):
            synthetic_positive(positive)
        original["draft"]["body"] += REMOVED
        with self.assertRaisesRegex(RuntimeError, "expected_one_body_and_one_claim"):
            synthetic_positive(original)


if __name__ == "__main__":
    unittest.main()
