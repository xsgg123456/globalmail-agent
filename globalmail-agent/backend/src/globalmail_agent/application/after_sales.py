"""Guarded internal after-sales requests; every effect and command receipt is atomic."""
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters import business_schema as b, after_sales_schema as a
from globalmail_agent.application.business_queries import BusinessQueries
from globalmail_agent.application.business_read_model import read_model, scope_where
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.application.after_sales_policy import published_policy
from globalmail_agent.application.after_sales_selection import normalize_selection, cancellation_source
from globalmail_agent.application.after_sales_ledger import provenance, operations_view, operation_row, refresh_balances, release_compensation
from globalmail_agent.application.event_store import append_ui_event
from globalmail_agent.domain.operations import CheckOperation, CreateOperation, CancelOperation, COMPENSATING, plan
from globalmail_agent.domain.policy import EligibilityRequest, evaluate_eligibility
from globalmail_agent.domain.compensation import selected_units
from globalmail_agent.domain.orders import result
from globalmail_agent.knowledge.base import canonical, sha


class AfterSalesService:
    def __init__(self, engine, store, workspace_id=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.workspace_id = engine, store, workspace_id

    def listing(self, conversation_id, operation_id=None):
        return BusinessQueries(self.engine, self.workspace_id).read(conversation_id,
            lambda model: operations_view(model, operation_id))

    def _evaluate(self, conn, conv, context, command, exclude=None):
        if conv["mode"] != "simulation" or context.mode != "simulation":
            raise ServiceError("historical_write_denied", 422)
        if context.conversation_id != conv["id"] or context.workspace_id != conv["workspace_id"]:
            raise ServiceError("context_out_of_scope", 422)
        if command.action != "refund" and (command.amount_minor is not None or command.currency is not None):
            raise ServiceError("unexpected_transaction_amount", 422)
        conn.execute(sa.select(b.branch_order_lines.c.id).where(*scope_where(b.branch_order_lines, conv))
            .order_by(b.branch_order_lines.c.id).with_for_update()).all()
        model = read_model(conn, conv["id"], self.workspace_id)
        selected = BusinessQueries.selected(model, command.order_line_id)
        if not selected:
            raise ServiceError("order_line_out_of_scope", 422)
        bundle = published_policy(conn, self.store, self.workspace_id, context, model, selected)
        data = BusinessQueries.context_from_model(model, selected)
        from globalmail_agent.application.case_issues import validate_issue_target
        validate_issue_target(conn, conv, command, selected[0])
        from globalmail_agent.application.plan_changes import check_plan_change
        check_plan_change(conn, conv, selected[0]["id"], command.action, exclude)
        data.update(policy=bundle["rules"], all_lines=[l[1] for l in model["lines"]])
        data["state"]["risk_flags"] = [*data["state"].get("risk_flags", []), *context.payload.get("active_risks", [])]
        normalize_selection(conn, self.store, conv, context, command, data)
        if exclude:
            data["state"]["operations"] = [o for o in data["state"]["operations"] if o["operation_id"] != exclude]
            data["state"]["execution_records"] = [e for e in data["state"]["execution_records"] if e["operation_id"] != exclude]
            from globalmail_agent.domain.compensation import refundable_balance
            same_line = [o for o in data["state"]["operations"] if o["order_line_id"] == data["line"]["line_id"]]
            succeeded, reserved = refundable_balance(same_line, data["state"]["execution_records"])
            order_rows = [o for o in data["state"]["operations"] if o["order_id"] == data["order"]["order_id"]]
            order_amounts = refundable_balance(order_rows, data["state"]["execution_records"])
            data["order"].update(refunded_minor=order_amounts[0], pending_refund_minor=order_amounts[1])
            data["line"].update(refunded_minor=succeeded, pending_refund_minor=reserved)
        request = EligibilityRequest.model_validate({k: getattr(command, k) for k in EligibilityRequest.model_fields})
        decision = evaluate_eligibility(request, data, policy_validated=True)
        if command.action == "logistics":
            for condition in decision["conditions"]:
                if condition["code"] == "shipment" and condition["status"] == "wait":
                    condition["status"] = "fulfilled"
            if all(c["status"] == "fulfilled" for c in decision["conditions"]):
                decision["outcome"] = "eligible"
        waiting = [c for c in decision["conditions"] if c["status"] != "fulfilled"]
        allowed_wait = bool(waiting) and all(c["status"] == "wait" and c["code"] in {
            "inventory", "warehouse_receipt", "warehouse_inspection"} for c in waiting)
        decision["authorized"] = decision["outcome"] == "eligible" or allowed_wait
        units = selected_units(command, data["line"])
        if units is None:
            decision["authorized"] = False
            decision["conditions"].append({"code": "quantity", "label": "须明确此次受影响单位份额", "status": "needs_input", "fulfilled_by": []})
            decision["missing_fields"] = sorted(set(decision["missing_fields"]) | {"quantity"})
        proposal = plan(command)
        proposal["affected_unit_ids"] = sorted(units) if units else None
        if command.action in {"spare_part", "replacement"}:
            proposal["item_id"] = command.item_id or data["line"]["sku"]
            proposal["address_version"] = data["state"].get("address_confirmation", {}).get("version")
        return model, selected, data, decision, proposal

    def check(self, conn, conv, context, args):
        command = args if isinstance(args, CheckOperation) else CheckOperation.model_validate(args)
        try:
            model, selected, data, decision, proposal = self._evaluate(conn, conv, context, command)
        except ServiceError as error:
            return result("denied", error.code, simulation=conv["mode"] == "simulation")
        identity = uuid4()
        decision.update(decision_id=str(identity), plan=proposal, conversation_version=conv["row_version"],
            business_digest=model["business_digest"], release_id=str(context.release_id), release_epoch=context.release_epoch)
        conn.execute(sa.insert(b.policy_decisions).values(id=identity, **provenance(conv, decision, "decision:" + str(identity)),
            order_line_id=selected[0]["id"], policy_profile_id=model["branch"]["policy_profile_id"],
            authorized=decision["authorized"], decision_data=decision, plan_digest=sha(canonical(proposal)),
            release_id=context.release_id, run_id=context.run_id))
        return BusinessQueries.response(model, data=decision, code="after_sales_eligibility")

    def _prior(self, conn, conv, command_id, command, action):
        digest = sha(canonical(command.model_dump(mode="json")))
        old = conn.execute(sa.select(a.operation_commands).where(a.operation_commands.c.command_id == command_id,
            *scope_where(a.operation_commands, conv))).mappings().first()
        if old and (old["payload_hash"] != digest or old["action"] != action):
            raise ServiceError("idempotency_conflict")
        return old["result"] if old else None, digest

    def _remember(self, conn, conv, command_id, operation, action, digest, response):
        conn.execute(sa.insert(a.operation_commands).values(id=uuid4(), **{k: conv[k] for k in a.SCOPE_KEYS},
            command_id=command_id, operation_id=operation["id"], action=action, payload_hash=digest, result=response))
        return response

    def create(self, conn, conv, context, args, command_id):
        command = args if isinstance(args, CreateOperation) else CreateOperation.model_validate(args)
        previous, digest = self._prior(conn, conv, command_id, command, "create")
        if previous is not None:
            return previous
        try:
            decision_id = UUID(command.decision_id)
        except ValueError:
            return result("denied", "decision_not_found", simulation=True)
        old_decision = conn.execute(sa.select(b.policy_decisions).where(b.policy_decisions.c.id == decision_id,
            *scope_where(b.policy_decisions, conv))).mappings().first()
        if not old_decision or not old_decision["decision_data"]:
            return result("denied", "decision_not_found", simulation=True)
        try:
            model, selected, data, decision, proposal = self._evaluate(conn, conv, context, command)
        except ServiceError as error:
            return result("denied", error.code, simulation=True)
        plan_hash = sha(canonical(proposal))
        existing = conn.execute(sa.select(b.operations).where(*scope_where(b.operations, conv),
            b.operations.c.order_line_id == selected[0]["id"], b.operations.c.plan_digest == plan_hash,
            b.operations.c.status != "cancelled", b.operations.c.confirmed_not_executed.is_(False))
            .order_by(b.operations.c.created_at).with_for_update()).mappings().first()
        if existing:
            response = operations_view(model, existing["external_id"])
            response.update(reason_code="operation_reused")
            response["data"]["operation"] = response["data"]["operations"][0]
            return self._remember(conn, conv, command_id, existing, "create", digest, response)
        saved = old_decision["decision_data"]
        if old_decision["plan_digest"] != plan_hash or saved["release_id"] != str(context.release_id):
            return result("conflict", "decision_plan_changed", simulation=True)
        if saved["conversation_version"] != conv["row_version"] or saved["business_digest"] != model["business_digest"]:
            return result("conflict", "decision_stale", simulation=True)
        if not decision["authorized"]:
            return BusinessQueries.response(model, "conflict" if any(c["code"] == "compensation_conflict" for c in decision["conditions"])
                else "needs_input", "after_sales_conditions_unsatisfied", decision)
        identity, external_id = uuid4(), "OP-" + uuid4().hex
        state = "accepted" if decision["outcome"] == "eligible" else "waiting_condition"
        snapshot = {**proposal, "operation_id": external_id, "order_line_id": selected[1]["line_id"],
            "issue_id": command.issue_id, "kind": command.action, "status": state, "version": 1,
            "selection_ref": command.selection_ref.model_dump(), "plan": proposal, "confirmed_not_executed": False,
            "waiting_conditions": [c["code"] for c in decision["conditions"] if c["status"] == "wait"],
            "updated_at": context.as_of.isoformat(), "policy_id": decision["policy_id"], "policy_version": decision["version"]}
        row = dict(id=identity, **provenance(conv, snapshot, "operation:" + external_id),
            order_id=selected[0]["order_id"], order_line_id=selected[0]["id"], external_id=external_id,
            kind=command.action, quantity=command.quantity, amount_minor=command.amount_minor, currency=command.currency,
            issue_id=command.issue_id, status=state, snapshot_at=context.as_of, plan_digest=plan_hash,
            decision_id=decision_id, policy_release_id=context.release_id, version=1)
        conn.execute(sa.insert(b.operations).values(**row))
        from globalmail_agent.application.case_issues import bind_plan
        bind_plan(conn, conv, row)
        if command.action in COMPENSATING:
            for position, unit in enumerate(proposal["affected_unit_ids"]):
                unit_amount = None if command.amount_minor is None else command.amount_minor // len(proposal["affected_unit_ids"]) + int(
                    position < command.amount_minor % len(proposal["affected_unit_ids"]))
                conn.execute(sa.insert(a.compensation_reservations).values(id=uuid4(), **model["scope"], operation_id=identity,
                    order_line_id=selected[0]["id"], unit_id=unit, amount_minor=unit_amount, currency=command.currency))
        refresh_balances(conn, conv)
        response = operations_view(read_model(conn, conv["id"], self.workspace_id), external_id)
        response["data"]["operation"] = response["data"]["operations"][0]
        response.update(reason_code="operation_created")
        append_ui_event(conn, conv["id"], "operation.created", {"operation_id": external_id, "status": state})
        return self._remember(conn, conv, command_id, row, "create", digest, response)

    def cancel(self, conn, conv, context, args, command_id):
        command = args if isinstance(args, CancelOperation) else CancelOperation.model_validate(args)
        previous, digest = self._prior(conn, conv, command_id, command, "cancel")
        if previous is not None:
            return previous
        if conv["mode"] != "simulation":
            return result("denied", "historical_write_denied")
        if context.mode != "simulation" or context.conversation_id != conv["id"] or context.workspace_id != conv["workspace_id"]:
            return result("denied", "context_out_of_scope", simulation=True)
        conn.execute(sa.select(b.branch_order_lines.c.id).where(*scope_where(b.branch_order_lines, conv))
            .order_by(b.branch_order_lines.c.id).with_for_update()).all()
        operation = operation_row(conn, conv, command.operation_id, lock=True)
        if not operation:
            return result("denied", "operation_out_of_scope", simulation=True)
        if operation["version"] != command.expected_operation_version:
            return result("conflict", "stale_operation_version", simulation=True)
        cancellation_source(conn, self.store, conv, context, command.selection_ref, operation)
        executions = conn.execute(sa.select(b.executions).where(b.executions.c.operation_id == operation["id"],
            *scope_where(b.executions, conv)).with_for_update()).mappings().all()
        if operation["status"] == "succeeded" or any(e["status"] == "succeeded" for e in executions):
            return result("denied", "executed_operation_not_cancelable", simulation=True)
        if any(not e["confirmed_not_executed"] for e in executions):
            details = {**operation["source_snapshot"], **operation["details"], "cancellation_requested": True,
                "cancellation_ref": command.selection_ref.model_dump(), "version": operation["version"] + 1}
            conn.execute(b.operations.update().where(b.operations.c.id == operation["id"]).values(
                details=details, version=operation["version"] + 1))
            response = result("unknown", "execution_reconciliation_required", simulation=True,
                data={"operation_id": operation["external_id"], "version": operation["version"] + 1})
            return self._remember(conn, conv, command_id, operation, "cancel", digest, response)
        snapshot = {**operation["source_snapshot"], "status": "cancelled", "version": operation["version"] + 1}
        conn.execute(b.operations.update().where(b.operations.c.id == operation["id"]).values(status="cancelled",
            version=operation["version"] + 1, confirmed_not_executed=True, details=snapshot))
        release_compensation(conn, operation)
        from globalmail_agent.application.case_issues import bind_plan
        bind_plan(conn, conv, dict(operation, status="cancelled"))
        refresh_balances(conn, conv)
        response = operations_view(read_model(conn, conv["id"], self.workspace_id), operation["external_id"])
        response.update(reason_code="operation_cancelled")
        append_ui_event(conn, conv["id"], "operation.cancelled", {"operation_id": operation["external_id"]})
        return self._remember(conn, conv, command_id, operation, "cancel", digest, response)
