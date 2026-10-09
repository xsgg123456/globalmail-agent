"""Local review files cannot silently release the next paid run."""
import json
from pathlib import Path
import tempfile
import unittest
from semantic_review import await_review


class SemanticReviewGateTests(unittest.TestCase):
    def test_failed_semantic_review_is_preserved_as_failed(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            review = {"status": "FAIL", "reviewer": "coding_agent_semantic_review_not_external_business_owner",
                "business_rules": "Unsupported customer history; do not continue paid runs."}
            (path / "semantic-review.json").write_text(json.dumps(review), encoding="utf-8")
            output = await_review(path)
            self.assertEqual(output["status"], "FAIL")
            self.assertEqual(output["business_rules"], review["business_rules"])
            self.assertEqual(len(output["review_sha256"]), 64)

    def test_unknown_status_or_reviewer_cannot_release_next_run(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for review in ({"status": "pending", "reviewer": "coding_agent_semantic_review_not_external_business_owner"},
                    {"status": "PASS", "reviewer": "model_self_assessment"}):
                (path / "semantic-review.json").write_text(json.dumps(review), encoding="utf-8")
                with self.assertRaisesRegex(RuntimeError, "local_semantic_review_format_invalid"):
                    await_review(path)


if __name__ == "__main__":
    unittest.main()
