"""Exact conditions, inventory reconciliation, current scope and HTTP refusal paths."""
from uuid import UUID, uuid4
import sqlalchemy as sa
from after_sales_fixture import AfterSalesFixture
from globalmail_agent.adapters import business_schema as b, after_sales_schema as a
from globalmail_agent.adapters.conversation_schema import conversations
from globalmail_agent.domain.executions import SimulationEvent, ExecutionLink


class SimulationSafetyTests(AfterSalesFixture):
    def setup_operation(self, action="refund", **changes):
        self.publish_policy()
        cid, context, request = self.prepared(action, **changes)
        response, _, _ = self.create_operation(cid, context, request)
        self.assertEqual(response["reason_code"], "operation_created", response)
        return cid, response["data"]["operation"]["operation_id"]

    def test_replacement_requires_same_exact_spec_and_records_dispatch(self):
        cid, op = self.setup_operation("replacement")
        self.push(cid, op, "create_execution")
        self.push(cid, op, "processing")
        self.push(cid, op, "label_created", receipt_ref="erp-replacement", tracking_number="SPEC-1", carrier="Test carrier")
        self.push(cid, op, "shipped", receipt_ref="carrier-handover")
        done = self.push(cid, op, "succeeded", receipt_ref="erp-replacement-complete")
        self.assertEqual(done["executions"][0]["item_id"], "H-CTD16-US-BK")
        self.assertEqual(done["executions"][0]["region_spec"], "US")
        self.assertEqual(done["executions"][0]["hardware_revision"], "SIM-V1")

    def test_logistics_investigation_has_real_execution_receipt(self):
        cid, op = self.setup_operation("logistics")
        self.push(cid, op, "create_execution")
        response = self.push(cid, op, "succeeded", receipt_ref="carrier-investigation-result")
        self.assertEqual(response["operations"][0]["kind"], "logistics")
        self.assertEqual(self.count(a.compensation_reservations), 0)

    def test_failed_fulfillment_retains_stock_until_confirmed_not_executed(self):
        cid, op = self.setup_operation("spare_part")
        self.push(cid, op, "create_execution")
        failed = self.push(cid, op, "failed", reason="ERP submit outcome is uncertain")
        self.assertEqual(failed["operations"][0]["status"], "failed")
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(sa.select(sa.func.sum(b.inventory.c.reserved))).scalar_one(), 1)
        self.push(cid, op, "reconciled_not_executed", confirmed_not_executed=True,
            receipt_ref="erp-confirms-no-order", reason="ERP lookup confirms no fulfillment")
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(sa.select(sa.func.sum(b.inventory.c.reserved))).scalar_one(), 0)
            self.assertEqual(conn.execute(sa.select(a.inventory_reservations.c.state)).scalar_one(), "released")

    def test_dispatch_proof_cannot_be_reconciled_as_not_executed(self):
        cid, op = self.setup_operation("spare_part")
        self.push(cid, op, "create_execution")
        self.push(cid, op, "label_created", receipt_ref="erp-label", tracking_number="TRACK", carrier="Test carrier")
        self.push(cid, op, "shipped", receipt_ref="carrier-handover")
        self.push(cid, op, "unknown")
        self.assert_error("simulation_event_not_allowed", lambda: self.push(cid, op, "reconciled_not_executed",
            confirmed_not_executed=True, receipt_ref="conflicting-erp", reason="Contradicts carrier dispatch"))
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(sa.select(a.inventory_reservations.c.state)).scalar_one(), "consumed")

    def test_inventory_wait_cannot_bypass_missing_address_and_restock_only_enables_execution(self):
        cid, op = self.setup_operation("spare_part", stock=0)
        missing, context, request = self.prepared("spare_part", stock=0, address_confirmed=False)
        denied, _, _ = self.create_operation(missing, context, request)
        self.assertEqual(denied["reason_code"], "after_sales_conditions_unsatisfied", denied)
        self.assertIn("address", denied["data"]["missing_fields"])
        self.assert_error("simulation_event_not_allowed", lambda: self.push(cid, op, "create_execution"))
        changed = self.push(cid, op, "inventory_changed", on_hand=3)
        self.assertIn("create_execution", changed["operations"][0]["allowed_events"])
        self.assertEqual(changed["executions"], [])
        self.push(cid, op, "create_execution")

    def test_merchant_return_authorization_requires_supplied_prepaid_document(self):
        cid, op = self.setup_operation("replacement", warehouse=False)
        fields = dict(receipt_ref="rma-ref", return_address="Confirmed simulation returns warehouse",
            packing_instructions="Protect the lamp and include the reference", postage_responsibility="merchant",
            tracking_number="PREPAID-TRACK", carrier="Test carrier")
        self.assert_error("prepaid_return_label_required", lambda: self.push(cid, op, "label_created", **fields))
        authorized = self.push(cid, op, "label_created", prepaid_label_ref="PREPAID-DOCUMENT", **fields)
        self.assertEqual(authorized["returns"][0]["prepaid_label_ref"], "PREPAID-DOCUMENT")
        self.assertEqual(authorized["returns"][0]["return_address"], fields["return_address"])

    def test_http_cross_branch_and_unknown_execution_reject_without_ledger_event(self):
        cid, op = self.setup_operation()
        data = self.sales.listing(cid, op)["data"]
        response = self.post(f"/simulation/branches/{uuid4()}/events", {"conversation_id": str(cid),
            "expected_version": data["conversation_version"], "operation_id": op, "expected_operation_version": 1,
            "event": "create_execution"})
        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(self.count(a.simulation_events), 0)
        self.assertEqual(self.count(b.executions), 0)
        response = self.client.get(f"/api/v1/operations/{op}?conversation_id={cid}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["data"]["operations"][0]["operation_id"], op)
