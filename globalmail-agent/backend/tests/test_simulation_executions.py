"""Actual manual transitions preserve unknown reservations and require real receipt fields."""
from uuid import UUID, uuid4
import sqlalchemy as sa
from after_sales_fixture import AfterSalesFixture
from globalmail_agent.adapters import business_schema as b, after_sales_schema as a
from globalmail_agent.adapters.conversation_schema import conversations
from globalmail_agent.domain.executions import ExecutionLink, SimulationEvent


class SimulationExecutionTests(AfterSalesFixture):
    def operation(self, action="refund", **changes):
        self.publish_policy()
        cid, context, command = self.prepared(action, **changes)
        response, _, _ = self.create_operation(cid, context, command)
        self.assertEqual(response["reason_code"], "operation_created", response)
        return cid, context, command, response["data"]["operation"]["operation_id"]

    def test_refund_success_requires_receipt_and_preserves_exact_amount_currency(self):
        cid, _, _, op = self.operation()
        created = self.push(cid, op, "create_execution")
        self.assertEqual(created["executions"][0]["amount_minor"], 5499)
        self.assertEqual(created["executions"][0]["currency"], "USD")
        self.assert_error("execution_receipt_required", lambda: self.push(cid, op, "succeeded"))
        success = self.push(cid, op, "succeeded", receipt_ref="payment-channel-receipt-1")
        self.assertEqual(success["operations"][0]["status"], "succeeded")
        from globalmail_agent.application.business_queries import BusinessQueries
        snapshot = BusinessQueries(self.engine).detail(cid)["data"]["orders"][0]
        self.assertEqual((snapshot["refunded_minor"], snapshot["pending_refund_minor"]), (5499, 0))
        self.assert_error("simulation_event_not_allowed", lambda: self.push(cid, op, "create_execution"))

    def test_unknown_and_failed_keep_reservation_until_not_executed_receipt(self):
        cid, context, command, op = self.operation()
        self.push(cid, op, "create_execution")
        unknown = self.push(cid, op, "unknown")
        self.assertEqual(unknown["operations"][0]["status"], "unknown")
        self.assert_error("simulation_event_not_allowed", lambda: self.push(cid, op, "create_execution"))
        self.assert_error("not_executed_confirmation_required", lambda: self.push(cid, op, "reconciled_not_executed", confirmed_not_executed=True))
        reconciled = self.push(cid, op, "reconciled_not_executed", confirmed_not_executed=True,
            receipt_ref="platform-confirmed-no-refund", reason="Platform ledger confirms not submitted")
        self.assertTrue(reconciled["executions"][0]["confirmed_not_executed"])
        with self.engine.connect() as conn:
            self.assertFalse(conn.execute(sa.select(a.compensation_reservations.c.active)).scalar_one())
        from globalmail_agent.application.business_queries import BusinessQueries
        self.assertEqual(BusinessQueries(self.engine).detail(cid)["data"]["orders"][0]["pending_refund_minor"], 0)

    def test_spare_execution_owns_stock_label_is_not_shipping_and_dispatch_consumes_once(self):
        cid, _, _, op = self.operation("spare_part")
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(sa.select(sa.func.sum(b.inventory.c.reserved))).scalar_one(), 0)
        created = self.push(cid, op, "create_execution")
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(sa.select(sa.func.sum(b.inventory.c.reserved))).scalar_one(), 1)
        labeled = self.push(cid, op, "label_created", receipt_ref="erp-document", tracking_number="SIM-TRACK-1", carrier="Simulation Carrier")
        self.assertEqual(labeled["shipments"][0]["status"], "label_created")
        self.assert_error("simulation_event_not_allowed", lambda: self.push(cid, op, "succeeded", receipt_ref="dispatch-proof"))
        self.push(cid, op, "unknown")
        dispatched = self.push(cid, op, "shipped", receipt_ref="carrier-accepted")
        self.assertEqual(dispatched["shipments"][0]["status"], "shipped")
        self.push(cid, op, "succeeded", receipt_ref="erp-fulfillment-receipt")
        self.push(cid, op, "delivered", receipt_ref="carrier-delivery-proof")
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(sa.select(a.inventory_reservations.c.state)).scalar_one(), "consumed")
            stock = conn.execute(sa.select(b.inventory).where(b.inventory.c.item_id == "SIM-OUTON-01-REMOTE-01")).mappings().one()
            self.assertEqual((stock["on_hand"], stock["reserved"]), (4, 0))

    def test_return_document_receipt_and_inspection_stay_distinct(self):
        cid, _, _, op = self.operation("return", warehouse=False)
        self.push(cid, op, "create_execution")
        self.assert_error("return_document_details_required", lambda: self.push(cid, op, "label_created", receipt_ref="rma-incomplete"))
        labeled = self.push(cid, op, "label_created", receipt_ref="rma-authorization", return_address="Test Returns Warehouse",
            packing_instructions="Pack this authorized lamp and attach the reference.", postage_responsibility="customer")
        self.assertFalse(labeled["returns"][0]["received"])
        self.assertEqual(labeled["returns"][0]["postage_responsibility"], "customer")
        self.assert_error("simulation_event_not_allowed", lambda: self.push(cid, op, "inspected", receipt_ref="fake", reason="passed"))
        self.assert_error("warehouse_quantity_required", lambda: self.push(cid, op, "received", receipt_ref="warehouse-missing-quantity"))
        self.push(cid, op, "received", receipt_ref="warehouse-received", quantity=1)
        self.push(cid, op, "inspected", receipt_ref="warehouse-inspected", reason="passed", quantity=1)
        finished = self.push(cid, op, "succeeded", receipt_ref="return-complete")
        self.assertEqual(finished["operations"][0]["status"], "succeeded")

    def test_same_event_key_replays_but_changed_payload_and_link_mismatch_are_rejected(self):
        cid, _, _, op = self.operation()
        listing = self.sales.listing(cid, op)["data"]
        command = SimulationEvent(conversation_id=cid, expected_version=listing["conversation_version"], operation_id=op,
            expected_operation_version=1, event="create_execution")
        branch, key = UUID(listing["branch_id"]), uuid4().hex
        original = self.simulation.event(branch, command, key)
        self.assertEqual(self.simulation.event(branch, command, key), original)
        self.assertEqual(self.count(b.executions), 1)
        self.assert_error("idempotency_conflict", lambda: self.simulation.event(branch,
            command.model_copy(update={"event": "unknown"}), key))
        response = self.simulation.link(branch, ExecutionLink(conversation_id=cid, expected_version=original["conversation_version"],
            operation_id=op, expected_operation_version=2, execution_id=original["executions"][0]["execution_id"]), uuid4().hex)
        self.assertTrue(response["linked"])

    def test_human_or_stopped_gate_only_records_business_event(self):
        cid, _, _, op = self.operation()
        with self.engine.begin() as conn:
            conn.execute(conversations.update().where(conversations.c.id == cid).values(processing_owner="human_review", auto_run_gate="disabled"))
        response = self.push(cid, op, "create_execution")
        self.assertEqual(response["wake_status"], "suppressed_by_human")
