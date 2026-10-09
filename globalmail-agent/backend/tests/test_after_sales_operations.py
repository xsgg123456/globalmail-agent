"""Authorization, cross-command compensation and atomic ledger behavior in PostgreSQL."""
from uuid import UUID, uuid4
import sqlalchemy as sa
from after_sales_fixture import AfterSalesFixture
from globalmail_agent.adapters import business_schema as b, after_sales_schema as a
from globalmail_agent.adapters.conversation_schema import conversations, case_issues
from globalmail_agent.application.conversation_lock import lock_conversation
from globalmail_agent.domain.operations import CheckOperation
from globalmail_agent.knowledge.index_commands import WithdrawCommand


class AfterSalesOperationTests(AfterSalesFixture):
    def test_unpublished_policy_and_bad_quote_cannot_create_decision_authority(self):
        cid, context, command = self.prepared()
        denied = self.check(cid, context, command)
        self.assertEqual(denied["reason_code"], "published_policy_required")
        self.assertEqual(self.count(b.policy_decisions), 0)
        self.publish_policy()
        cid, context, command = self.prepared()
        bad = command.model_copy(update={"selection_ref": command.selection_ref.model_copy(update={"quote": "INVENTED_CONSENT"})})
        self.assertEqual(self.check(cid, context, bad)["reason_code"], "selection_source_invalid")

    def test_refund_duplicate_commands_reuse_and_reserve_amount_once(self):
        self.publish_policy()
        cid, context, command = self.prepared()
        checked = self.check(cid, context, command)
        self.assertTrue(checked["data"]["authorized"], checked)
        first, request, identity = self.create_operation(cid, context, command, checked)
        self.assertEqual(first["reason_code"], "operation_created", first)
        second, _, _ = self.create_operation(cid, context, command, checked, identity)
        self.assertEqual(second, first)
        different = command.model_copy(update={"amount_minor": 5000})
        self.assert_error("idempotency_conflict", lambda: self.create_operation(cid, context, different, checked, identity))
        again, _, _ = self.create_operation(cid, context, command)
        self.assertEqual(again["reason_code"], "operation_reused", again)
        self.assertEqual(self.count(b.operations), 1)
        self.assertEqual(self.count(a.compensation_reservations), 1)
        data = self.sales.listing(cid)["data"]
        self.assertEqual(data["operations"][0]["status"], "accepted")
        self.assertEqual(data["executions"], [])
        from globalmail_agent.application.business_queries import BusinessQueries
        self.assertEqual(BusinessQueries(self.engine).detail(cid)["data"]["orders"][0]["pending_refund_minor"], 5499)

    def test_new_run_and_new_issue_reuse_the_same_reserved_unit(self):
        self.publish_policy()
        cid, context, command = self.prepared()
        first, _, _ = self.create_operation(cid, context, command)
        appended = self.append_mail(cid, "Thank you for recording my accepted refund request.")
        context.run_id = UUID(appended["run_id"])
        with self.engine.begin() as conn:
            conv = lock_conversation(conn, cid)
            issue_id = uuid4()
            conn.execute(sa.insert(case_issues).values(id=issue_id, **{k: conv[k] for k in b.SCOPE_KEYS},
                conversation_id=cid, issue_key="same-order-new-issue", status="open", version=1))
        command = command.model_copy(update={"issue_id": str(issue_id)})
        again, _, _ = self.create_operation(cid, context, command)
        self.assertEqual(again["reason_code"], "operation_reused", again)
        self.assertEqual(again["data"]["operation"]["operation_id"], first["data"]["operation"]["operation_id"])
        self.assertEqual(self.count(a.compensation_reservations), 1)

    def test_policy_edit_numbers_are_used_and_revocation_blocks_creation(self):
        self.publish_policy(refund={"partial_offer_max_basis_points": 1000})
        cid, context, command = self.prepared(amount=1000)
        checked = self.check(cid, context, command)
        self.assertFalse(checked["data"]["authorized"], checked)
        self.assertIn("refund_amount", checked["data"]["missing_fields"])
        current = self.releases.listing()["head"]
        self.releases.withdraw(self.policy_did, WithdrawCommand(expected_version=1,
            expected_release_epoch=current["epoch"]), uuid4().hex)
        self.assertEqual(self.check(cid, context, command)["status"], "denied")

    def test_waiting_warehouse_reserves_compensation_without_execution(self):
        self.publish_policy()
        cid, context, command = self.prepared(warehouse=False)
        checked = self.check(cid, context, command)
        self.assertTrue(checked["data"]["authorized"], checked)
        created, _, _ = self.create_operation(cid, context, command, checked)
        operation = created["data"]["operation"]
        self.assertEqual(operation["status"], "waiting_condition")
        self.assertNotIn("create_execution", operation["allowed_events"])
        self.assert_error("simulation_event_not_allowed", lambda: self.push(cid, operation["operation_id"], "create_execution"))
        self.assertEqual(self.count(b.executions), 0)

    def test_cross_scope_decision_and_stale_address_are_denied(self):
        self.publish_policy()
        cid, context, command = self.prepared()
        old = self.check(cid, context, command)
        other, other_context, other_command = self.prepared()
        output, _, _ = self.create_operation(other, other_context, other_command, old)
        self.assertEqual(output["reason_code"], "decision_not_found")
        cid, context, command = self.prepared("spare_part")
        command = command.model_copy(update={"address_version": 99})
        self.assertEqual(self.check(cid, context, command)["reason_code"], "stale_address")

    def test_partial_units_have_exact_paid_share_and_exclude_other_compensation(self):
        self.publish_policy()
        cid, context, command = self.prepared(quantity=2)
        output, _, _ = self.create_operation(cid, context, command)
        self.assertEqual(output["reason_code"], "operation_created", output)
        self.assertEqual(output["data"]["operation"]["affected_unit_ids"], ["u0"])
        conflict = command.model_copy(update={"action": "replacement", "item_id": "H-CTD16-US-BK", "amount_minor": None, "currency": None})
        checked = self.check(cid, context, conflict)
        self.assertFalse(checked["data"]["authorized"])
