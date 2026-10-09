"""Distinguish exact claim assembly from preserved legacy raw bodies in safe evidence."""
import json
import unittest
from uuid import uuid4, uuid5
from bootstrap import digest
from draft_lineage import draft_lineage


class DraftLineageTests(unittest.TestCase):
    def receipt(self, args, normalized):
        run = uuid4()
        return {"run": {"id": run}, "tools": [{"id": str(uuid5(run, "actual-call")),
            "name": "create_reply_draft", "arguments": {**args, "body": normalized},
            "result": {"data": {**args, "body": normalized}}}]}, [{"response": {"calls": [{
                "id": "actual-call", "name": "create_reply_draft", "arguments": json.dumps(args)}]}}]

    def test_new_claims_preserve_order_spaces_and_unicode(self):
        texts = [" First claim. ", "Zweite Aussage: \u00e4."]
        record, requests = self.receipt({"claims": [{"text": t} for t in texts]}, "\n\n".join(texts))
        audit = draft_lineage(record, requests)[0]
        self.assertEqual(audit["model_body_mode"], "ordered_claims")
        self.assertIsNone(audit["raw_body_sha256"])
        self.assertTrue(audit["normalized_equals_exact_ordered_claim_join"])
        self.assertEqual(audit["claim_text_sha256_in_order"], [digest(t.encode()) for t in texts])

    def test_added_or_trimmed_text_is_visible(self):
        record, requests = self.receipt({"claims": [{"text": " Keep spaces. "}]}, "Keep spaces.")
        self.assertFalse(draft_lineage(record, requests)[0]["normalized_equals_exact_ordered_claim_join"])

    def test_legacy_explicit_body_is_compared_without_reconstruction(self):
        body = "First. Second."
        record, requests = self.receipt({"body": body, "claims": [{"text": "First."}, {"text": "Second."}]}, body)
        audit = draft_lineage(record, requests)[0]
        self.assertTrue(audit["normalized_equals_original_explicit_body"])
        self.assertIsNone(audit["normalized_equals_exact_ordered_claim_join"])
        self.assertEqual(audit["actual_normalized_body_sha256"], digest(body.encode()))


if __name__ == "__main__":
    unittest.main()
