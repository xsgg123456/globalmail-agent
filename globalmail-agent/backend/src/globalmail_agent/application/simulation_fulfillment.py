"""Labels, actual dispatch, return receipt and inspection remain separate facts."""
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.application.after_sales_ledger import provenance
from globalmail_agent.application.business_read_model import scope_where
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.application.simulation_inventory import settle
from globalmail_agent.domain.returns import return_document


def create_label(conn, conv, branch, operation, execution, command, policy):
    if not command.receipt_ref:
        raise ServiceError("document_receipt_required", 422)
    outbound = operation["kind"] in {"replacement", "spare_part"} and execution is not None
    if outbound:
        if not command.tracking_number or not command.carrier:
            raise ServiceError("shipment_tracking_required", 422)
        existing = conn.execute(sa.select(b.shipments.c.id).where(b.shipments.c.execution_id == execution["id"],
            *scope_where(b.shipments, conv))).first()
        if existing:
            raise ServiceError("shipment_already_created")
        external_id = "PARCEL-" + uuid4().hex
        payload = {"parcel_id": external_id, "tracking_number": command.tracking_number, "carrier": command.carrier,
            "receipt_ref": command.receipt_ref, "status": "label_created", "purpose": "outbound",
            "quantity": operation["quantity"], "item_id": operation["source_snapshot"]["plan"]["item_id"],
            "updated_at": branch["clock"].isoformat()}
        conn.execute(sa.insert(b.shipments).values(id=uuid4(), **provenance(conv, payload, "parcel:" + external_id),
            order_id=operation["order_id"], order_line_id=operation["order_line_id"], operation_id=operation["id"],
            execution_id=execution["id"], external_id=external_id, parcel_purpose="replacement" if operation["kind"] == "replacement" else "spare_part",
            status="label_created", snapshot_at=branch["clock"]))
        return
    if operation["kind"] not in {"return", "replacement", "refund"}:
        raise ServiceError("return_not_applicable", 422)
    existing = conn.execute(sa.select(b.return_receipts.c.id).where(b.return_receipts.c.operation_id == operation["id"],
        *scope_where(b.return_receipts, conv))).first()
    if existing:
        raise ServiceError("return_already_authorized")
    state = branch["state"]
    reason = state.get("return_request_details", {}).get("reason")
    if reason is None and state.get("defect_confirmed_in_simulation") is True:
        reason = "defect"
    if reason not in {"defect", "unwanted"}:
        raise ServiceError("return_reason_required", 422)
    expected_payer = policy["return"]["defect_label_fee_payer" if reason == "defect" else "unwanted_label_fee_payer"]
    if not command.return_address or not command.packing_instructions or command.postage_responsibility != expected_payer:
        raise ServiceError("return_document_details_required", 422)
    if expected_payer == "merchant" and not command.prepaid_label_ref:
        raise ServiceError("prepaid_return_label_required", 422)
    external_id = "RMA-" + uuid4().hex
    payload = return_document(policy, reason, external_id, operation["quantity"],
        operation["source_snapshot"]["plan"]["affected_unit_ids"], command)
    payload.update(receipt_ref=command.receipt_ref,
        tracking_number=command.tracking_number, carrier=command.carrier, reason=reason, updated_at=branch["clock"].isoformat())
    if payload["prepaid_label"] and (not command.tracking_number or not command.carrier):
        raise ServiceError("prepaid_return_label_required", 422)
    conn.execute(sa.insert(b.return_receipts).values(id=uuid4(), **provenance(conv, payload, "return:" + external_id),
        order_id=operation["order_id"], order_line_id=operation["order_line_id"], operation_id=operation["id"],
        execution_id=execution["id"] if execution else None, external_id=external_id, quantity=operation["quantity"],
        status="authorized", received=False, inspection=None, snapshot_at=branch["clock"]))


def return_event(conn, conv, branch, operation, command):
    row = conn.execute(sa.select(b.return_receipts).where(b.return_receipts.c.operation_id == operation["id"],
        *scope_where(b.return_receipts, conv)).with_for_update()).mappings().one_or_none()
    if not row:
        raise ServiceError("return_authorization_required")
    event = command.event
    if event in {"received", "inspected"} and command.quantity is None:
        raise ServiceError("warehouse_quantity_required", 422)
    if command.quantity is not None and command.quantity != row["quantity"]:
        raise ServiceError("return_quantity_mismatch", 422)
    if event == "return_in_transit":
        if row["status"] != "authorized" or not command.tracking_number or not command.carrier:
            raise ServiceError("return_tracking_required", 422)
        status, received, inspection = "in_transit", False, None
    elif event == "received":
        if row["status"] not in {"authorized", "in_transit"} or not command.receipt_ref:
            raise ServiceError("warehouse_receipt_required", 422)
        status, received, inspection = "received", True, None
    elif event == "inspected":
        if not row["received"] or row["inspection"] is not None or not command.receipt_ref:
            raise ServiceError("warehouse_inspection_required", 422)
        if command.reason not in {"passed", "failed", "disputed"}:
            raise ServiceError("inspection_result_required", 422)
        status, received, inspection = "inspected", True, command.reason
    else:
        raise ServiceError("return_transition_invalid")
    snapshot = {**row["source_snapshot"], **row["details"], "status": status, "received": received, "inspection": inspection,
        "updated_at": branch["clock"].isoformat()}
    if command.receipt_ref:
        snapshot["receipt_ref"] = command.receipt_ref
    if event == "return_in_transit":
        snapshot.update(tracking_number=command.tracking_number, carrier=command.carrier)
    if event == "inspected" and inspection == "passed":
        snapshot.update(inspected_quantity=row["quantity"], inspected_unit_ids=snapshot["affected_unit_ids"])
    conn.execute(b.return_receipts.update().where(b.return_receipts.c.id == row["id"]).values(status=status,
        received=received, inspection=inspection, version=row["version"] + 1, details=snapshot))


def shipment_event(conn, conv, branch, operation, execution, command):
    if not execution:
        raise ServiceError("execution_required", 422)
    parcel = conn.execute(sa.select(b.shipments).where(b.shipments.c.execution_id == execution["id"],
        *scope_where(b.shipments, conv)).with_for_update()).mappings().one_or_none()
    expected = "label_created" if command.event == "shipped" else "shipped"
    if not parcel or parcel["status"] != expected or not command.receipt_ref:
        raise ServiceError("shipment_transition_evidence_required", 422)
    if command.event == "shipped":
        settle(conn, conv, execution, consume=True)
    snapshot = {**parcel["source_snapshot"], **parcel["details"], "status": command.event, "receipt_ref": command.receipt_ref,
        "updated_at": branch["clock"].isoformat()}
    conn.execute(b.shipments.update().where(b.shipments.c.id == parcel["id"])
        .values(status=command.event, version=parcel["version"] + 1, details=snapshot))
