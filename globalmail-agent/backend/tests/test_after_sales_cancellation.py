"""Customer-source cancellation and conservative uncertain execution occupancy."""
from uuid import uuid4
import sqlalchemy as sa
from after_sales_fixture import AfterSalesFixture
from globalmail_agent.adapters import agent_schema as agent, business_schema as b, after_sales_schema as a
from globalmail_agent.adapters.conversation_schema import messages
from globalmail_agent.application.conversation_lock import lock_conversation
from globalmail_agent.domain.operations import CancelOperation


class AfterSalesCancellationTests(AfterSalesFixture):
    def prepared_operation(self):
        self.publish_policy()
        cid, context, request = self.prepared()
        output, _, _ = self.create_operation(cid, context, request)
        return cid, context, output["data"]["operation"]["operation_id"]

    def cancel(self, cid, context, op, *, body=None, version=None):
        body = body or "Please cancel " + op + "."
        self.append_mail(cid, body)
        with self.engine.begin() as conn:
            conv = lock_conversation(conn, cid)
            message = conn.execute(sa.select(messages).where(messages.c.conversation_id == cid)
                .order_by(messages.c.seq.desc())).mappings().first()
            operation = conn.execute(sa.select(b.operations).where(b.operations.c.external_id == op)).mappings().one()
            command = CancelOperation(operation_id=op, expected_operation_version=version or operation["version"],
                selection_ref={"message_id": str(message["id"]), "quote": body})
            identity = uuid4()
            conn.execute(sa.insert(agent.tool_commands).values(id=identity, **{k: conv[k] for k in b.SCOPE_KEYS},
                conversation_id=cid, run_id=context.run_id, command_key=uuid4().hex, name="cancel_after_sales_operation",
                arguments=command.model_dump(), payload_hash="a" * 64, status="prepared"))
            return self.sales.cancel(conn, conv, context, command, identity)

    def test_cancel_without_execution_releases_once_and_stale_version_does_not_write(self):
        cid, context, op = self.prepared_operation()
        self.assertEqual(self.cancel(cid, context, op, version=999)["reason_code"], "stale_operation_version")
        self.assertEqual(self.cancel(cid, context, op)["reason_code"], "operation_cancelled")
        with self.engine.connect() as conn:
            self.assertFalse(conn.execute(sa.select(a.compensation_reservations.c.active)).scalar_one())
            self.assertEqual(conn.execute(sa.select(b.operations.c.status)).scalar_one(), "cancelled")
        self.assertEqual(self.sales.listing(cid)["data"]["operations"][0]["allowed_events"], [])

    def test_unknown_execution_requires_reconciliation_before_cancel_can_release(self):
        cid, context, op = self.prepared_operation()
        self.push(cid, op, "create_execution")
        self.push(cid, op, "unknown")
        self.assertEqual(self.cancel(cid, context, op)["reason_code"], "execution_reconciliation_required")
        with self.engine.connect() as conn:
            self.assertTrue(conn.execute(sa.select(a.compensation_reservations.c.active)).scalar_one())
        self.push(cid, op, "reconciled_not_executed", confirmed_not_executed=True,
            receipt_ref="payment-lookup-none", reason="Payment provider confirms no transfer")
        self.assertEqual(self.cancel(cid, context, op)["reason_code"], "operation_cancelled")

    def test_negative_or_conditional_cancel_quote_cannot_authorize(self):
        cid, context, op = self.prepared_operation()
        for text in ["Please do not cancel " + op, "If it is delayed, cancel " + op, "Please cancel an unrelated order"]:
            self.assert_error("cancellation_selection_required", lambda: self.cancel(cid, context, op, body=text))
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(sa.select(b.operations.c.status)).scalar_one(), "accepted")

    def test_cancel_acknowledgment_requires_request_and_releases_once_with_actual_proof(self):
        cid, context, op = self.prepared_operation()
        self.push(cid, op, "create_execution")
        self.assert_error("simulation_event_not_allowed", lambda: self.push(cid, op, "cancellation_acknowledged",
            confirmed_not_executed=True, receipt_ref="cancel-proof", reason="Provider confirms not paid"))
        self.assertEqual(self.cancel(cid, context, op)["reason_code"], "execution_reconciliation_required")
        self.assert_error("not_executed_confirmation_required", lambda: self.push(cid, op, "cancellation_acknowledged"))
        output = self.push(cid, op, "cancellation_acknowledged", key="cancel-ack-once",
            confirmed_not_executed=True, receipt_ref="cancel-proof", reason="Provider confirms not paid")
        self.assertEqual(output["operations"][0]["status"], "cancelled")
        with self.engine.connect() as conn:
            self.assertFalse(conn.execute(sa.select(a.compensation_reservations.c.active)).scalar_one())
            self.assertTrue(conn.execute(sa.select(b.executions.c.confirmed_not_executed)).scalar_one())
        self.assert_error("simulation_event_not_allowed", lambda: self.push(cid, op, "cancellation_acknowledged",
            confirmed_not_executed=True, receipt_ref="cancel-proof", reason="Provider confirms not paid"))

    def test_historical_context_cannot_create_decision(self):
        self.publish_policy()
        cid, context, request = self.prepared()
        context.mode = "historical_replay"
        self.assertEqual(self.check(cid, context, request)["reason_code"], "historical_write_denied")
        self.assertEqual(self.count(b.policy_decisions), 0)
