"""Actual source-backed natural selection and execution rejection after later customer messages."""
import unittest
from types import SimpleNamespace
from uuid import uuid4
import sqlalchemy as sa
from after_sales_fixture import AfterSalesFixture
from agent_fixture import understanding
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.agent.understanding import Understanding, validate_sources
from globalmail_agent.observability.local_records import save_understanding
from globalmail_agent.application.selection_parameters import intent_applies_to_plan


class SelectionFreshnessTests(AfterSalesFixture):
    def current_selection(self, cid, command, body, consent="explicit", target_item=None, order_number=None):
        self.append_mail(cid, body)
        job, context, _, _ = self.components()
        message = context.payload["messages"][-1]
        source = {"message_id": message["message_id"], "quote": body}
        category = {"spare_part": "parts", "logistics": "shipment"}.get(command.action, command.action)
        value = Understanding.model_validate(understanding([], intents=[{
            "business_type": category, "order_number": order_number, "target_item": target_item,
            "condition": None, "requested_solution": body, "consent": consent, "sources": [source]}]))
        save_understanding(self.engine, self.store, context.workspace_id, job, validate_sources(value, context.payload))
        return context, command.model_copy(update={"selection_ref": command.selection_ref.model_copy(update=source)})

    def test_natural_full_refund_binds_real_paid_amount_and_rejects_conditional_or_wrong_amount(self):
        self.publish_policy()
        cid, _, command = self.prepared()
        context, current = self.current_selection(cid, command, "Please give me a full refund.")
        checked = self.check(cid, context, current)
        self.assertTrue(checked["data"]["authorized"], checked)
        self.assertEqual(self.check(cid, context, current.model_copy(update={"amount_minor": 5000}))["reason_code"],
            "selection_amount_currency_required")
        self.assertEqual(self.check(cid, context, current.model_copy(update={"currency": "EUR"}))["reason_code"],
            "selection_amount_currency_required")

    def test_later_uninterpreted_or_declined_customer_message_blocks_old_execution(self):
        self.publish_policy()
        cid, _, command = self.prepared()
        context, current = self.current_selection(cid, command, "Please give me a full refund.")
        output, _, _ = self.create_operation(cid, context, current)
        op = output["data"]["operation"]["operation_id"]
        self.append_mail(cid, "I do not want a refund now.")
        self.assert_error("selection_revalidation_required", lambda: self.push(cid, op, "create_execution"))
        job, latest, _, _ = self.components()
        message = latest.payload["messages"][-1]
        value = Understanding.model_validate(understanding([], intents=[{
            "business_type": "refund", "order_number": None, "target_item": None, "condition": None,
            "requested_solution": "withdraw refund", "consent": "declined",
            "sources": [{"message_id": message["message_id"], "quote": message["body"]}]}]))
        save_understanding(self.engine, self.store, latest.workspace_id, job, validate_sources(value, latest.payload))
        self.assert_error("selection_superseded", lambda: self.push(cid, op, "create_execution"))
        self.assertEqual(self.count(b.executions), 0)
        self.assertEqual(self.count(b.operations), 1)

    def test_conditional_full_refund_cannot_bind_natural_choice(self):
        self.ambiguous_choice(1, "If the parcel is late, please give me a full refund.")

    def test_multiple_units_cannot_bind_ambiguous_natural_choice(self):
        self.ambiguous_choice(2, "Please give me a full refund.")

    def ambiguous_choice(self, quantity, body):
        self.publish_policy()
        cid, _, command = self.prepared(quantity=quantity)
        context, current = self.current_selection(cid, command, body)
        self.assertEqual(self.check(cid, context, current)["reason_code"], "selection_amount_currency_required")
        self.assertEqual(self.count(b.operations), 0)

    def test_same_plan_current_confirmation_reuses_original_and_records_actual_execution_source(self):
        self.publish_policy()
        cid, _, command = self.prepared()
        context, current = self.current_selection(cid, command, "Please give me a full refund.")
        output, _, _ = self.create_operation(cid, context, current)
        op = output["data"]["operation"]["operation_id"]
        latest, renewed = self.current_selection(cid, command, "Yes, I still confirm the full refund of 54.99 USD.")
        reused, _, _ = self.create_operation(cid, latest, renewed)
        self.assertEqual(reused["data"]["operation"]["operation_id"], op)
        self.push(cid, op, "create_execution")
        with self.engine.connect() as conn:
            saved = conn.execute(sa.select(b.executions.c.source_snapshot)).scalar_one()
            self.assertEqual(saved["execution_selection_ref"]["message_id"], renewed.selection_ref.message_id)
        self.assertEqual(self.count(b.operations), 1)

    def test_changed_explicit_refund_amount_does_not_execute_old_plan(self):
        self.reject_changed_refund("Yes, I confirm a full refund of 50.00 USD.")

    def test_changed_explicit_refund_currency_does_not_execute_old_plan(self):
        self.reject_changed_refund("Yes, I confirm a full refund in EUR.")

    def test_larger_amount_containing_original_digits_does_not_execute_old_plan(self):
        self.reject_changed_refund("Yes, I confirm a full refund of 154.99 USD.")

    def test_currency_token_containing_original_code_does_not_execute_old_plan(self):
        self.reject_changed_refund("Yes, I confirm a full refund of 54.99 USDT.")

    def test_unsupported_currency_without_amount_does_not_execute_old_plan(self):
        self.reject_changed_refund("Yes, I confirm a full refund in USDT.")

    def test_natural_same_currency_reconfirmation_executes_original_plan(self):
        self.publish_policy()
        cid, _, command = self.prepared()
        context, current = self.current_selection(cid, command, "Please give me a full refund.")
        output, _, _ = self.create_operation(cid, context, current)
        op = output["data"]["operation"]["operation_id"]
        self.current_selection(cid, command, "Yes, I confirm a full refund in USD.")
        self.push(cid, op, "create_execution")
        self.assertEqual(self.count(b.operations), 1)
        self.assertEqual(self.count(b.executions), 1)

    def test_changed_explicit_replacement_quantity_does_not_execute_single_unit_plan(self):
        self.reject_changed_replacement("Yes, please send 2 replacements of H-CTD16-US-BK.", "selection_quantity_mismatch")

    def test_changed_replacement_sku_suffix_does_not_execute_original_plan(self):
        self.reject_changed_replacement("Yes, please send replacement H-CTD16-US-BK-NEW instead.", "selection_target_mismatch")

    def test_explicit_unknown_target_cannot_bypass_retained_original_choice(self):
        self.publish_policy()
        cid, context, command = self.prepared(action="replacement")
        output, _, _ = self.create_operation(cid, context, command)
        op = output["data"]["operation"]["operation_id"]
        self.current_selection(cid, command, "Please send replacement H-CTD16-US-BK-NEW instead.",
            target_item="H-CTD16-US-BK-NEW")
        self.assert_error("selection_target_mismatch", lambda: self.push(cid, op, "create_execution"))
        self.assertEqual(self.count(b.operations), 1)
        self.assertEqual(self.count(b.executions), 0)

    def test_same_single_replacement_reconfirmation_executes_original_plan(self):
        self.publish_policy()
        cid, context, command = self.prepared(action="replacement")
        output, _, _ = self.create_operation(cid, context, command)
        op = output["data"]["operation"]["operation_id"]
        self.current_selection(cid, command, "Yes, send 1 replacement of H-CTD16-US-BK to the same confirmed address.")
        self.push(cid, op, "create_execution")
        self.assertEqual(self.count(b.operations), 1)
        self.assertEqual(self.count(b.executions), 1)

    def reject_changed_replacement(self, body, code):
        self.publish_policy()
        cid, context, command = self.prepared(action="replacement")
        output, _, _ = self.create_operation(cid, context, command)
        op = output["data"]["operation"]["operation_id"]
        self.current_selection(cid, command, body)
        self.assert_error(code, lambda: self.push(cid, op, "create_execution"))
        self.assertEqual(self.count(b.operations), 1)
        self.assertEqual(self.count(b.executions), 0)

    def reject_changed_refund(self, body):
        self.publish_policy()
        cid, _, command = self.prepared()
        context, current = self.current_selection(cid, command, "Please give me a full refund.")
        output, _, _ = self.create_operation(cid, context, current)
        op = output["data"]["operation"]["operation_id"]
        self.current_selection(cid, command, body)
        self.assert_error("selection_amount_currency_required", lambda: self.push(cid, op, "create_execution"))
        self.assertEqual(self.count(b.operations), 1)
        self.assertEqual(self.count(b.executions), 0)


class IntentTargetScopeTests(unittest.TestCase):
    def setUp(self):
        self.data = {"order": {"display_order_number": "999-7100006-8100000"},
            "line": {"line_id": "line-one", "sku": "H-CTD16-US-BK"},
            "all_lines": [{"line_id": "line-one", "sku": "H-CTD16-US-BK"},
                {"line_id": "line-two", "sku": "H-CTD17-US-WH"}]}
        self.command = SimpleNamespace(item_id="H-CTD16-US-BK")

    def test_source_backed_known_other_line_is_independent(self):
        intent = {"target_item": "H-CTD17-US-WH", "sources": [{"quote": "Please replace H-CTD17-US-WH."}]}
        self.assertFalse(intent_applies_to_plan(intent, self.data, self.command))

    def test_unknown_or_unproved_other_target_still_requires_revalidation(self):
        for target in ("H-CTD16-US-BK-NEW", "H-CTD17-US-WH"):
            with self.subTest(target=target):
                intent = {"target_item": target, "sources": [{"quote": "Please replace H-CTD16-US-BK-NEW."}]}
                self.assertTrue(intent_applies_to_plan(intent, self.data, self.command))
