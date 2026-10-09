"""Real ledger corrections preserve successful execution and compensation, never fake cancellation."""
from uuid import UUID, uuid4
import sqlalchemy as sa
from after_sales_fixture import AfterSalesFixture
from globalmail_agent.adapters import business_schema as b, after_sales_schema as a
from globalmail_agent.application.branch_facts import BranchFactsService
from globalmail_agent.domain.business_events import BranchFact


class ContinuousFulfillmentTests(AfterSalesFixture):
    def operation(self, action):
        self.publish_policy()
        cid, context, request = self.prepared(action, warehouse=action != "return")
        output, _, _ = self.create_operation(cid, context, request)
        return cid, context, output["data"]["operation"]["operation_id"]

    def test_unknown_corrective_attempt_does_not_release_original_success_and_can_retry_only_after_proof(self):
        cid, _, op = self.operation("spare_part")
        first = self.push(cid, op, "create_execution")["executions"][0]["execution_id"]
        self.push(cid, op, "label_created", receipt_ref="first-label", carrier="Simulation Carrier", tracking_number="FIRST")
        self.push(cid, op, "shipped", receipt_ref="first-shipped")
        self.push(cid, op, "succeeded", receipt_ref="first-success")
        correction = dict(staff_id="warehouse-operator", correction_of_execution_id=first,
            receipt_ref="correction-proof", reason="Wrong accessory verified")
        response = self.push(cid, op, "create_corrective_execution", **correction)
        second = next(e["execution_id"] for e in response["executions"] if e["execution_id"] != first)
        self.push(cid, op, "unknown", execution_id=second)
        self.assert_error("simulation_event_not_allowed", lambda: self.push(cid, op, "create_corrective_execution", **correction))
        self.push(cid, op, "reconciled_not_executed", execution_id=second, confirmed_not_executed=True,
            receipt_ref="only-second-not-dispatched", reason="Warehouse confirms corrective package never dispatched")
        with self.engine.connect() as conn:
            self.assertTrue(conn.execute(sa.select(a.compensation_reservations.c.active)).scalar_one())
            row = conn.execute(sa.select(b.operations)).mappings().one()
            self.assertEqual(row["status"], "succeeded")
            self.assertFalse(row["confirmed_not_executed"])
            self.assertEqual(sorted(conn.execute(sa.select(a.inventory_reservations.c.state)).scalars()), ["consumed", "released"])
        retried = self.push(cid, op, "create_corrective_execution", **correction)
        self.assertEqual(len(retried["executions"]), 3)
        self.assertEqual(self.count(b.operations), 1)
        self.assertEqual(self.count(a.compensation_reservations), 1)

    def test_failed_inspection_correction_keeps_original_event_and_current_result(self):
        cid, _, op = self.operation("return")
        self.push(cid, op, "create_execution")
        self.push(cid, op, "label_created", receipt_ref="authorized-rma", return_address="Private Test Returns",
            packing_instructions="Pack exact item and accessories", postage_responsibility="customer")
        self.push(cid, op, "received", receipt_ref="warehouse-received", quantity=1)
        self.push(cid, op, "inspected", receipt_ref="first-warehouse-inspection", quantity=1, reason="disputed")
        ledger = self.sales.listing(cid)["data"]
        current = ledger["returns"][0]
        command = BranchFact(conversation_id=cid, expected_version=ledger["conversation_version"], source_event_id="inspection-correction",
            order_line_id=current["order_line_id"], event="inspection_correction", expected_business_version=0, business_version=1,
            expected_resource_version=current["version"], resource_id=current["return_id"], staff_id="warehouse-operator",
            receipt_ref="second-inspection-proof", reason="Warehouse rechecked all returned units", inspection="passed", quantity=1)
        service = BranchFactsService(self.engine, self.store)
        self.assert_error("stale_business_resource_version", lambda: service.event(UUID(ledger["branch_id"]),
            command.model_copy(update={"expected_resource_version": 999}), uuid4().hex))
        service.event(UUID(ledger["branch_id"]), command, uuid4().hex)
        self.assertEqual(self.sales.listing(cid)["data"]["returns"][0]["inspection"], "passed")
        with self.engine.connect() as conn:
            original = conn.execute(sa.select(a.simulation_events.c.payload).where(a.simulation_events.c.event == "inspected")).scalar_one()
            self.assertEqual(original["reason"], "disputed")

    def test_corrective_dispatch_reuses_original_operation_and_keeps_consumed_stock_history(self):
        cid, _, op = self.operation("spare_part")
        first = self.push(cid, op, "create_execution")["executions"][0]["execution_id"]
        self.push(cid, op, "label_created", receipt_ref="first-label", carrier="Simulation Carrier", tracking_number="FIRST")
        self.push(cid, op, "shipped", receipt_ref="first-carrier-proof")
        self.push(cid, op, "succeeded", receipt_ref="first-erp-proof")
        self.assert_error("fulfillment_correction_proof_required", lambda: self.push(cid, op, "create_corrective_execution"))
        corrected = self.push(cid, op, "create_corrective_execution", staff_id="warehouse-operator",
            correction_of_execution_id=first, receipt_ref="warehouse-picking-error", reason="Warehouse confirmed wrong accessory dispatched")
        second = next(e["execution_id"] for e in corrected["executions"] if e["execution_id"] != first)
        self.push(cid, op, "label_created", execution_id=second, receipt_ref="second-label", carrier="Simulation Carrier", tracking_number="SECOND")
        self.push(cid, op, "shipped", execution_id=second, receipt_ref="second-carrier-proof")
        self.push(cid, op, "succeeded", execution_id=second, receipt_ref="second-erp-proof")
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(sa.select(sa.func.count()).select_from(b.operations)).scalar_one(), 1)
            self.assertEqual(conn.execute(sa.select(sa.func.count()).select_from(a.compensation_reservations)).scalar_one(), 1)
            self.assertEqual(conn.execute(sa.select(a.inventory_reservations.c.state)).scalars().all(), ["consumed", "consumed"])
            self.assertEqual(conn.execute(sa.select(b.executions.c.status)).scalars().all(), ["succeeded", "succeeded"])
        self.assert_error("fulfillment_correction_already_recorded", lambda: self.push(cid, op, "create_corrective_execution",
            staff_id="warehouse-operator", correction_of_execution_id=first, receipt_ref="same-error-new-key", reason="Repeat"))
