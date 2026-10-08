"""Warehouse, exact compatibility, stock, address and entitlement boundaries."""
import unittest
from globalmail_agent.domain.policy import evaluate_eligibility
from policy_helpers import context, command, statuses, fact


class FulfillmentTests(unittest.TestCase):
    def test_full_refund_and_replacement_require_warehouse_not_customer_or_photo(self):
        for action in ("refund", "replacement"):
            for patch in ({"received": False}, {"inspection": "pending"}, {"quantity": True},
                          {"source_kind": "customer_statement"}, {"source_kind": "visual_observation"}):
                inputs = context(action=action)
                inputs["state"]["returns"][0].update(patch)
                result = evaluate_eligibility(command(action=action), inputs)
                self.assertNotEqual(result["outcome"], "eligible")
            inputs = context(action=action)
            inputs["state"]["returns"] = []
            self.assertIn("wait", statuses(evaluate_eligibility(command(action=action), inputs), "warehouse_receipt"))

    def test_receipt_and_inspection_must_cover_all_affected_quantity(self):
        inputs = context(quantity=2)
        inputs["state"]["returns"][0].update(quantity=1)
        self.assertNotEqual(evaluate_eligibility(command(quantity=2), inputs)["outcome"], "eligible")
        inputs["line"]["unit_allocations"] = [{"unit_id": "A", "paid_minor": 5000}, {"unit_id": "B", "paid_minor": 5001}]
        inputs["state"]["returns"] = [fact(order_line_id="line-1", received=True, inspection="passed",
            quantity=1, affected_unit_ids=["A"]), fact(order_line_id="line-1", received=True,
            inspection="passed", quantity=1, affected_unit_ids=["B"])]
        self.assertEqual(evaluate_eligibility(command(quantity=2), inputs)["outcome"], "eligible")
        inputs["state"]["returns"][1]["inspection"] = "disputed"
        self.assertEqual(evaluate_eligibility(command(quantity=2), inputs)["outcome"], "requires_review")

    def test_customer_choice_address_version_cannot_be_reused_after_move(self):
        inputs = context(action="spare_part")
        self.assertEqual(evaluate_eligibility(command(action="spare_part"), inputs)["outcome"], "eligible")
        for patch in ({"version": 3}, {"version": True}, {"confirmed": False}, {"market": "DE"}):
            inputs = context(action="spare_part")
            inputs["state"]["address_confirmation"].update(patch)
            self.assertIn("needs_input", statuses(evaluate_eligibility(command(action="spare_part"), inputs), "address"))
        inputs = context(action="spare_part")
        inputs["state"]["customer_choices"][0].pop("address_version")
        self.assertEqual(evaluate_eligibility(command(action="spare_part"), inputs)["outcome"], "needs_input")

    def test_stock_and_compatibility_use_exact_sku_region_hardware(self):
        for patch in ({"sku": "exact-sku-lookalike"}, {"hardware_revision": "another-hardware"},
                      {"market": "DE"}, {"market": None}):
            inputs = context(action="spare_part")
            inputs["compatibility"][0].update(patch)
            self.assertEqual(evaluate_eligibility(command(action="spare_part"), inputs)["outcome"], "requires_review")
        inputs = context(action="spare_part")
        inputs["state"]["inventory"][1].update(on_hand=1, reserved=1)
        self.assertEqual(evaluate_eligibility(command(action="spare_part"), inputs)["outcome"], "wait")
        for patch in ({"on_hand": 2.0}, {"reserved": True}, {"reserved": 100}):
            inputs = context(action="spare_part")
            inputs["state"]["inventory"][1].update(patch)
            self.assertEqual(evaluate_eligibility(command(action="spare_part"), inputs)["outcome"], "requires_review")
        inputs = context(action="spare_part")
        inputs["state"]["inventory"][1]["market"] = "DE"
        self.assertIn("needs_input", statuses(evaluate_eligibility(command(action="spare_part"), inputs), "inventory"))

    def test_safety_part_and_active_risk_always_require_review(self):
        inputs = context(action="spare_part")
        inputs["parts"][0]["safety_critical"] = True
        self.assertEqual(evaluate_eligibility(command(action="spare_part"), inputs)["outcome"], "requires_review")
        inputs = context()
        inputs["state"]["risk_flags"] = [fact(status="active", kind="potential_burn")]
        self.assertEqual(evaluate_eligibility(command(), inputs)["outcome"], "requires_review")
        inputs["state"]["risk_flags"][0]["status"] = "corrected_by_human"
        self.assertEqual(evaluate_eligibility(command(), inputs)["outcome"], "eligible")

    def test_inventory_snapshot_must_exist_and_not_exceed_context_time(self):
        for snapshot in (None, "not-a-date", "2026-10-09T09:00:00+08:00"):
            inputs = context(action="spare_part")
            inputs["state"]["inventory"][1]["snapshot_at"] = snapshot
            result = evaluate_eligibility(command(action="spare_part"), inputs)
            self.assertIn("needs_input", statuses(result, "inventory"))

    def test_purchase_spare_part_does_not_entitle_free_compensation(self):
        inputs = context(action="spare_part")
        inputs["state"]["customer_choices"][0]["purpose"] = "purchase"
        self.assertIn("ineligible", statuses(evaluate_eligibility(command(action="spare_part"), inputs), "spare_entitlement"))

    def test_fault_or_missing_evidence_for_another_part_does_not_entitle_requested_part(self):
        inputs = context(action="spare_part")
        inputs["state"]["problem_evidence"][0]["item_id"] = "another-part"
        self.assertIn("needs_input", statuses(evaluate_eligibility(command(action="spare_part"), inputs), "reported_problem"))

    def test_logistics_uses_parcel_time_without_requiring_refund_or_consent(self):
        inputs = context(action="logistics")
        inputs["line"]["paid_minor"] = None
        inputs["state"]["customer_choices"] = []
        parcel = fact(order_line_id="line-1", status="label_created", updated_at="2026-10-08T08:00:00+08:00")
        inputs["state"]["shipments"] = [parcel]
        result = evaluate_eligibility(command(action="logistics"), inputs)
        self.assertEqual(result["outcome"], "eligible")
        self.assertIsNone(result["remaining_refund_minor"])
        parcel["updated_at"] = "2026-09-30T08:00:00+08:00"
        self.assertEqual(evaluate_eligibility(command(action="logistics"), inputs)["outcome"], "wait")

    def test_exact_return_window_and_warranty_window_boundaries(self):
        for action, days in (("return", 30), ("spare_part", 365)):
            inputs = context(action=action)
            inputs["as_of"] = "2026-10-20T12:00:00+08:00" if days == 30 else "2027-09-20T12:00:00+08:00"
            self.assertIn("fulfilled", statuses(evaluate_eligibility(command(action=action), inputs), "delivery_date"))
            inputs["as_of"] = inputs["as_of"].replace("12:00:00", "12:00:01")
            self.assertIn("requires_review", statuses(evaluate_eligibility(command(action=action), inputs), "delivery_date"))
        inputs = context(action="return")
        inputs["order"]["delivered_at"] = None
        self.assertIn("needs_input", statuses(evaluate_eligibility(command(action="return"), inputs), "delivery_date"))


if __name__ == "__main__":
    unittest.main()
