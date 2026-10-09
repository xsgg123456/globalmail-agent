"""Reject attempts to loosen the schema while diagnosing output order/descriptions."""
from copy import deepcopy
import json
import unittest
from bootstrap import ROOT
from prepare_review_schema_controls import ORDER, PRIOR, schema_audit


class ReviewSchemaControlTests(unittest.TestCase):
    def materials(self):
        candidate = ROOT / "tmp/phase7-planned-outcome-review-schema.json"
        manifest = ROOT / "tmp/phase7-agent-eval" / PRIOR / "manifest-planned-zero-http.json"
        if not candidate.exists() or not manifest.exists():
            self.skipTest("private_candidate_material_unavailable")
        prior = json.loads(manifest.read_text(encoding="utf-8"))
        old = json.loads((ROOT / prior["targets"][0]["prepared_file"]).read_text(encoding="utf-8"))["schema"]
        return old, json.loads(candidate.read_text(encoding="utf-8"))

    def test_reason_first_candidate_retains_original_types_bounds_and_strictness(self):
        old, new = self.materials()
        audit = schema_audit(old, new)
        self.assertEqual(audit["new_property_order"], ORDER)
        self.assertEqual(set(audit["old_required_order"]), set(ORDER))
        self.assertTrue(audit["additionalProperties_false_preserved"])
        self.assertTrue(all(field["type_and_bounds_equal"] for field in audit["fields"]))
        self.assertEqual(new["properties"]["reason"]["maxLength"], 1500)
        self.assertEqual(new["properties"]["unsupported_claims"]["maxItems"], 20)

    def test_expanded_bounds_optional_fields_or_changed_types_are_refused(self):
        old, candidate = self.materials()
        changes = [("reason", "maxLength", 1501), ("unsupported_claims", "maxItems", 21), ("supported", "type", "string")]
        for name, key, value in changes:
            with self.subTest(name=name, key=key):
                new = deepcopy(candidate)
                new["properties"][name][key] = value
                with self.assertRaisesRegex(RuntimeError, "type_or_bound_changed"):
                    schema_audit(old, new)
        new = deepcopy(candidate)
        new["required"].remove("supported")
        with self.assertRaisesRegex(RuntimeError, "required_set_changed"):
            schema_audit(old, new)


if __name__ == "__main__":
    unittest.main()
