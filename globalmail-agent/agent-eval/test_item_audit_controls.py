"""Actual frozen contrasts remain complete; per-item failures cannot be hidden by true."""
from copy import deepcopy
import json
import unittest
from bootstrap import ROOT
from item_audit import evaluate_item_audit
from prepare_item_audit_controls import PRIOR, prepare_request, repair_positive_sources
from globalmail_agent.adapters.model_provider import prompt
from globalmail_agent.agent.outcome_validation import OutcomeReview
from globalmail_agent.agent.review_audit import audit_sources, trigger_units


class ItemAuditControlTests(unittest.TestCase):
    def materials(self):
        path = ROOT / "tmp/phase7-agent-eval" / PRIOR / "manifest-planned-zero-http.json"
        if not path.exists():
            self.skipTest("private_frozen_contrast_unavailable")
        manifest = json.loads(path.read_text(encoding="utf-8"))
        return [json.loads((ROOT / target["prepared_file"]).read_text(encoding="utf-8")) for target in manifest["targets"]]

    def prepared(self, original, *, positive_sources=False):
        return prepare_request(original, OutcomeReview.model_json_schema(), prompt("validation"),
            prompt("validation-grounding"), positive_sources=positive_sources)

    def review_and_payload(self):
        request, _ = self.prepared(self.materials()[1], positive_sources=True)
        payload = json.loads(request["messages"][1]["content"])
        sources = audit_sources(payload["context"], payload["observations"])
        review = {"request_checks": [{"unit_index": i, "status": "addressed", "reply_quote": payload["draft"]["claims"][-1]["text"]}
            for i, _ in enumerate(payload["trigger_units"])], "source_checks": [],
            "reason": "Offline format/source-match fixture only; not a semantic or model-quality verdict.",
            "supported": True, "language_correct": True, "unsupported_claims": []}
        for i, claim in enumerate(payload["draft"]["claims"]):
            review["source_checks"].append({"claim_index": i, "supported": True,
                "evidence": [{"source_id": identity, "quote": sources[identity]} for identity in claim["source_ids"]]})
        return review, payload

    def test_both_original_DATA_drafts_and_wrong_understanding_remain_complete(self):
        for original in self.materials():
            with self.subTest(body=original["messages"][1]["content"][:20]):
                before = deepcopy(original)
                prepared, audit = self.prepared(original)
                old = json.loads(original["messages"][1]["content"])
                new = json.loads(prepared["messages"][1]["content"])
                self.assertEqual(original, before)
                self.assertEqual({k: v for k, v in new.items() if k != "trigger_units"}, old)
                self.assertEqual(new["understanding"]["intents"][0]["business_type"], "troubleshooting")
                self.assertIsNone(new["understanding"]["intents"][0]["condition"])
                self.assertEqual(new["trigger_units"], trigger_units(new["context"]))
                body = next(row["body"] for row in new["context"]["messages"] if row["message_id"] == new["context"]["trigger_message_id"])
                self.assertEqual("".join(new["trigger_units"]), body)
                self.assertEqual(prepared["messages"][2], original["messages"][2])
                self.assertEqual(prepared["tools"], original["tools"])
                self.assertEqual(prepared["timeout"], original["timeout"])
                self.assertEqual(audit["original_DATA_sha256"], audit["existing_DATA_sha256"])

    def test_tail_replacement_or_missing_required_audits_is_refused(self):
        original = self.materials()[0]
        schema = OutcomeReview.model_json_schema()
        with self.assertRaisesRegex(RuntimeError, "tail_must_remain_verbatim"):
            prepare_request(original, schema, prompt("validation"), "different tail")
        schema = deepcopy(schema)
        schema["required"].remove("source_checks")
        with self.assertRaisesRegex(RuntimeError, "required_current_contract"):
            prepare_request(original, schema, prompt("validation"), prompt("validation-grounding"))

    def test_whitespace_and_punctuation_units_are_lossless(self):
        body = "Question?\n\nIf not, refund later.  Not now!\n尾句？ 末尾无句号"
        context = {"messages": [{"message_id": "actual", "body": body}], "trigger_message_id": "actual"}
        self.assertEqual("".join(trigger_units(context)), body)
        self.assertIn("Not now!", "".join(trigger_units(context)))

    def test_explicit_source_only_positive_repair_keeps_every_body_text_and_non_draft_field(self):
        original = self.materials()[1]
        prepared, audit = self.prepared(original, positive_sources=True)
        before = json.loads(original['messages'][1]['content'])
        after = json.loads(prepared['messages'][1]['content'])
        reconstructed, operations = repair_positive_sources(before)
        self.assertEqual({k: v for k, v in after.items() if k != 'trigger_units'}, reconstructed)
        self.assertEqual({k: v for k, v in reconstructed.items() if k != 'draft'},
            {k: v for k, v in before.items() if k != 'draft'})
        self.assertEqual(after['draft']['body'], before['draft']['body'])
        self.assertEqual([c['text'] for c in after['draft']['claims']], [c['text'] for c in before['draft']['claims']])
        self.assertEqual(len(operations), 3)
        self.assertEqual(audit['explicit_synthetic_positive_source_only_repairs'], operations)
        bad = deepcopy(before)
        bad['draft']['claims'][2]['kind'] = 'customer_fact'
        with self.assertRaisesRegex(RuntimeError, 'original_source_premise_changed'):
            repair_positive_sources(bad)

    def test_total_true_cannot_override_omitted_request_or_unsupported_claim(self):
        review, payload = self.review_and_payload()
        for collection, key, value in (("request_checks", "status", "omitted"),
                ("request_checks", "status", "changed_condition"), ("source_checks", "supported", False)):
            with self.subTest(collection=collection, key=key):
                bad = deepcopy(review)
                bad[collection][-1][key] = value
                complete, safe = evaluate_item_audit(OutcomeReview.model_validate(bad), payload)
                self.assertTrue(complete["model_supported"])
                self.assertFalse(safe["audit_accepts"])
                self.assertFalse(safe["effective_supported_AND"])

    def test_missing_duplicate_out_of_range_and_changed_quotes_fail(self):
        review, payload = self.review_and_payload()
        cases = []
        for collection in ("request_checks", "source_checks"):
            bad = deepcopy(review)
            bad[collection].pop()
            cases.append(bad)
            bad = deepcopy(review)
            bad[collection][-1] = deepcopy(bad[collection][0])
            cases.append(bad)
        bad = deepcopy(review)
        bad["source_checks"][0]["claim_index"] = 100
        cases.append(bad)
        bad = deepcopy(review)
        bad["request_checks"][0]["reply_quote"] = "not in this actual draft"
        cases.append(bad)
        for key, value in (("quote", "not in the claimed actual source"), ("quote", "   "), ("source_id", "foreign-customer")):
            bad = deepcopy(review)
            bad["source_checks"][0]["evidence"][0][key] = value
            cases.append(bad)
        for bad in cases:
            _, safe = evaluate_item_audit(OutcomeReview.model_validate(bad), payload)
            self.assertFalse(safe["audit_accepts"])
            self.assertFalse(safe["effective_supported_AND"])

    def test_exact_source_audit_is_private_and_legacy_fields_are_not_filled(self):
        review, payload = self.review_and_payload()
        complete, safe = evaluate_item_audit(OutcomeReview.model_validate(review), payload)
        self.assertTrue(safe["audit_accepts"])
        self.assertTrue(all(e["exact_quote_match"] for row in complete["source_checks"] for e in row["evidence_checks"]))
        self.assertNotIn("reason", safe)
        self.assertNotIn("request_checks", safe)
        self.assertNotIn("source_checks", safe)
        with self.assertRaises(ValueError):
            OutcomeReview.model_validate({k: v for k, v in review.items() if k not in {"request_checks", "source_checks"}})
        payload["trigger_units"][-1] = "clipped conditional preference"
        with self.assertRaisesRegex(RuntimeError, "trigger_units_not_product_exact"):
            evaluate_item_audit(OutcomeReview.model_validate(review), payload)


if __name__ == "__main__":
    unittest.main()
