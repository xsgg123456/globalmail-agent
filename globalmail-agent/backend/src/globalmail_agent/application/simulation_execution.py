"""Simulated execution attempts keep their receipt and uncertain results separate."""
from types import SimpleNamespace
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.application.after_sales_ledger import provenance, release_compensation
from globalmail_agent.application.business_read_model import scope_where
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.application.simulation_inventory import reserve, settle
from globalmail_agent.application.after_sales import AfterSalesService
from globalmail_agent.domain.operations import CheckOperation


def recheck(conn, store, conv, branch, operation):
    from globalmail_agent.application.risk_records import active_risks
    decision = conn.execute(sa.select(b.policy_decisions).where(b.policy_decisions.c.id == operation["decision_id"],
        *scope_where(b.policy_decisions, conv))).mappings().first()
    if not decision:
        raise ServiceError("managed_operation_required", 422)
    value = operation["source_snapshot"]
    context = SimpleNamespace(mode=conv["mode"], conversation_id=conv["id"], workspace_id=conv["workspace_id"],
        run_id=decision["run_id"], release_id=operation["policy_release_id"],
        release_epoch=decision["decision_data"]["release_epoch"], as_of=branch["clock"],
        payload={"active_risks": active_risks(conn, store, conv)})
    command = CheckOperation.model_validate({**value["plan"], "issue_id": value["issue_id"], "selection_ref": value["selection_ref"]})
    _, _, data, outcome, _ = AfterSalesService(None, store)._evaluate(conn, conv, context, command, exclude=operation["external_id"])
    if outcome["outcome"] != "eligible":
        raise ServiceError("execution_conditions_unsatisfied")
    return data


def create_execution(conn, store, conv, branch, operation):
    data = recheck(conn, store, conv, branch, operation)
    rows = conn.execute(sa.select(b.executions).where(b.executions.c.operation_id == operation["id"],
        *scope_where(b.executions, conv)).with_for_update()).mappings().all()
    if any(not e["confirmed_not_executed"] for e in rows):
        raise ServiceError("execution_reconciliation_required")
    identity, external_id = uuid4(), "EXEC-" + uuid4().hex
    attempt = max([e["attempt_no"] for e in rows], default=0) + 1
    payload = {"execution_id": external_id, "kind": operation["kind"], "quantity": operation["quantity"],
        "item_id": operation["source_snapshot"]["plan"].get("item_id"),
        "address_version": operation["source_snapshot"]["plan"].get("address_version"),
        "region_spec": data["order"]["market"], "hardware_revision": data["line"]["hardware_revision"],
        "amount_minor": operation["amount_minor"], "currency": operation["currency"],
        "affected_unit_ids": operation["source_snapshot"]["plan"]["affected_unit_ids"],
        "status": "accepted", "attempt_no": attempt, "confirmed_not_executed": False,
        "updated_at": branch["clock"].isoformat()}
    row = {"id": identity, **provenance(conv, payload, "execution:" + external_id),
        "order_id": operation["order_id"], "order_line_id": operation["order_line_id"], "operation_id": operation["id"],
        "external_id": external_id, "amount_minor": operation["amount_minor"], "currency": operation["currency"],
        "status": "accepted", "snapshot_at": branch["clock"], "attempt_no": attempt, "managed": True,
        "version": 1, "confirmed_not_executed": False}
    conn.execute(sa.insert(b.executions).values(**row))
    if operation["kind"] in {"spare_part", "replacement"}:
        reserve(conn, conv, operation, row)
    return row, "awaiting_execution"


def execution_event(conn, store, conv, branch, operation, execution, command):
    if not execution or execution["confirmed_not_executed"]:
        raise ServiceError("execution_required", 422)
    event = command.event
    status = execution["status"]
    if event == "reconciled_not_executed":
        if status not in {"unknown", "failed"} or not command.confirmed_not_executed or not command.receipt_ref or not command.reason:
            raise ServiceError("not_executed_confirmation_required", 422)
        sent = conn.execute(sa.select(b.shipments.c.id).where(b.shipments.c.execution_id == execution["id"],
            b.shipments.c.status.in_(["shipped", "delivered"]), *scope_where(b.shipments, conv))).first()
        if sent:
            raise ServiceError("not_executed_evidence_conflicts_with_dispatch")
        conn.execute(b.executions.update().where(b.executions.c.id == execution["id"]).values(
            status="failed", confirmed_not_executed=True, receipt_ref=command.receipt_ref,
            version=execution["version"] + 1, details={**execution["source_snapshot"],
                "status": "failed", "confirmed_not_executed": True, "receipt_ref": command.receipt_ref}))
        settle(conn, conv, execution, consume=False)
        release_compensation(conn, operation)
        return "failed", True
    valid = {"processing": {"accepted"}, "succeeded": {"accepted", "processing", "unknown"},
        "failed": {"accepted", "processing", "unknown"}, "unknown": {"accepted", "processing", "unknown"}}
    if event not in valid or status not in valid[event]:
        raise ServiceError("execution_transition_invalid")
    if event == "succeeded":
        if not command.receipt_ref:
            raise ServiceError("execution_receipt_required", 422)
        if operation["kind"] in {"refund", "logistics"}:
            recheck(conn, store, conv, branch, operation)
        elif operation["kind"] in {"replacement", "spare_part"}:
            parcel = conn.execute(sa.select(b.shipments.c.status).where(b.shipments.c.execution_id == execution["id"],
                *scope_where(b.shipments, conv))).scalars().all()
            if not any(status in {"shipped", "delivered"} for status in parcel):
                raise ServiceError("shipment_evidence_required")
        elif operation["kind"] == "return":
            recheck(conn, store, conv, branch, operation)
            receipts = conn.execute(sa.select(b.return_receipts).where(b.return_receipts.c.operation_id == operation["id"],
                *scope_where(b.return_receipts, conv))).mappings().all()
            if not any(r["received"] and r["inspection"] == "passed" and r["quantity"] == operation["quantity"] for r in receipts):
                raise ServiceError("warehouse_evidence_required")
    if event == "failed" and not command.reason:
        raise ServiceError("failure_reason_required", 422)
    payload = {**execution["source_snapshot"], "status": event, "receipt_ref": command.receipt_ref,
        "failure_code": command.reason if event == "failed" else None, "updated_at": branch["clock"].isoformat()}
    conn.execute(b.executions.update().where(b.executions.c.id == execution["id"]).values(status=event,
        receipt_ref=command.receipt_ref, version=execution["version"] + 1, details=payload))
    return event, False
