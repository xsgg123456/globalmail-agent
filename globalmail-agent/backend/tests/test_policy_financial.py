"""Balance, affected quantities and compensation conflicts across issues."""
import unittest
from globalmail_agent.domain.policy import evaluate_eligibility
from policy_helpers import context, command, fact, statuses


class FinancialTests(unittest.TestCase):
    def test_partial_refund_integer_floor_and_currency_no_conversion(self):
        for amount, expected in ((2000, "eligible"), (2001, "requires_review")):
            inputs = context(amount=amount)
            self.assertEqual(evaluate_eligibility(command(amount=amount), inputs)["outcome"], expected)
        inputs = context()
        request = command().model_copy(update={"currency": "EUR"})
        self.assertIn("ineligible", statuses(evaluate_eligibility(request, inputs), "refund_currency"))

    def test_line_quantity_does_not_give_one_item_the_whole_line_payment(self):
        inputs = context(quantity=2, paid=10001)
        inputs["state"]["customer_choices"][0]["quantity"] = 1
        result = evaluate_eligibility(command(), inputs)
        self.assertIn("needs_input", statuses(result, "quantity"))
        inputs["line"]["unit_allocations"] = [{"unit_id": "unit-A", "paid_minor": 5000},
                                               {"unit_id": "unit-B", "paid_minor": 5001}]
        inputs["state"]["customer_choices"][0].update(affected_unit_ids=["unit-A"], amount_minor=5000)
        inputs["state"]["returns"][0].update(quantity=1, affected_unit_ids=["unit-A"])
        self.assertEqual(evaluate_eligibility(command(amount=5000), inputs)["outcome"], "eligible")
        inputs["state"]["customer_choices"][0]["amount_minor"] = 10001
        self.assertIn("ineligible", statuses(evaluate_eligibility(command(), inputs), "refund_amount"))

    def test_invalid_paid_quantity_and_allocations_are_not_coerced(self):
        for field, value in (("paid_minor", True), ("paid_minor", 10001.0), ("quantity", True), ("quantity", 1.0)):
            inputs = context()
            inputs["line"][field] = value
            self.assertNotEqual(evaluate_eligibility(command(), inputs)["outcome"], "eligible")
        inputs = context(quantity=2)
        inputs["line"]["unit_allocations"] = [{"unit_id": "A", "paid_minor": True}, {"unit_id": "B", "paid_minor": 10000}]
        inputs["state"]["customer_choices"][0].update(quantity=1, affected_unit_ids=["A"])
        self.assertIn("requires_review", statuses(evaluate_eligibility(command(), inputs), "quantity"))

    def test_success_plus_pending_unknown_occupy_once_per_operation(self):
        inputs = context()
        inputs["order"].update(refunded_minor=1000, pending_refund_minor=2000)
        inputs["state"]["operations"] = [fact(operation_id="done", kind="refund", status="completed",
            order_line_id="line-1", quantity=1, amount_minor=1000, currency="USD", issue_id="old-issue"),
            fact(operation_id="unknown", kind="refund", status="unknown", order_line_id="line-1",
                 quantity=1, amount_minor=2000, currency="USD", issue_id="another-issue")]
        inputs["state"]["execution_records"] = [fact(execution_id="success", operation_id="done", status="succeeded",
            amount_minor=1000, currency="USD"), fact(execution_id="attempt", operation_id="unknown", status="unknown",
            amount_minor=2000, currency="USD"), fact(execution_id="retry", operation_id="unknown", status="pending",
            amount_minor=2000, currency="USD")]
        result = evaluate_eligibility(command(), inputs)
        self.assertEqual(result["remaining_refund_minor"], 7001)
        self.assertIn("requires_review", statuses(result, "compensation_conflict"))
        self.assertIn("wait", statuses(result, "compensation_conflict"))

    def test_disjoint_explicit_units_can_have_different_issues_but_overlap_cannot(self):
        inputs = context(quantity=2, paid=10001, amount=1000)
        inputs["line"]["unit_allocations"] = [{"unit_id": "A", "paid_minor": 5000}, {"unit_id": "B", "paid_minor": 5001}]
        inputs["state"]["customer_choices"][0].update(quantity=1, affected_unit_ids=["B"])
        inputs["state"]["operations"] = [fact(operation_id="old-replacement", kind="replacement", status="completed",
            order_line_id="line-1", quantity=1, affected_unit_ids=["A"], issue_id="different-issue")]
        result = evaluate_eligibility(command(amount=1000), inputs)
        self.assertEqual(result["outcome"], "eligible")
        inputs["state"]["customer_choices"][0]["affected_unit_ids"] = ["A"]
        result = evaluate_eligibility(command(amount=1000), inputs)
        self.assertEqual(result["outcome"], "requires_review")
        inputs["state"]["operations"][0].pop("affected_unit_ids")
        self.assertEqual(evaluate_eligibility(command(amount=1000), inputs)["outcome"], "requires_review")

    def test_aggregate_refunds_are_not_silently_split_or_lost(self):
        for line_count in (1, 2):
            inputs = context()
            inputs["order"].update(line_count=line_count, refunded_minor=1000)
            result = evaluate_eligibility(command(), inputs)
            self.assertIsNone(result["remaining_refund_minor"])
            self.assertIn("requires_review", statuses(result, "compensation_ledger"))

    def test_mismatched_or_visual_execution_cannot_restore_free_balance(self):
        inputs = context()
        inputs["order"]["refunded_minor"] = 1000
        inputs["state"]["operations"] = [fact(operation_id="done", kind="refund", status="completed",
            order_line_id="line-1", quantity=1, amount_minor=1000, currency="USD")]
        for patch in ({"currency": "EUR"}, {"amount_minor": 999}, {"source_kind": "visual_observation"}):
            inputs["state"]["execution_records"] = [fact(execution_id="ex", operation_id="done", status="succeeded",
                amount_minor=1000, currency="USD", **{key: value for key, value in patch.items() if key not in ("amount_minor", "currency")})]
            inputs["state"]["execution_records"][0].update(patch)
            self.assertIsNone(evaluate_eligibility(command(), inputs)["remaining_refund_minor"])


if __name__ == "__main__":
    unittest.main()
