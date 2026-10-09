"""Manual sourced corrections retain original rows and immutable event history."""
import sqlalchemy as sa
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.application.business_read_model import scope_where
from globalmail_agent.application.conversation_lock import ServiceError


def correct_fulfillment(conn, conv, branch, line, command):
    table = b.shipments if command.event == "original_shipment" else b.return_receipts
    row = conn.execute(sa.select(table).where(*scope_where(table, conv), table.c.order_line_id == line["id"],
        table.c.external_id == command.resource_id).with_for_update()).mappings().first()
    if not row:
        raise ServiceError("business_resource_out_of_scope", 422)
    if command.expected_resource_version != row["version"]:
        raise ServiceError("stale_business_resource_version")
    original = {**row["source_snapshot"], **row["details"]}
    values = {}
    if command.event == "original_shipment":
        if row["operation_id"] or row["parcel_purpose"] != "original_order" or not all([
                command.status, command.carrier, command.tracking_number]):
            raise ServiceError("original_parcel_evidence_required", 422)
        ranks = {"label_created": 0, "shipped": 1, "in_transit": 1, "delivered": 2}
        if ranks.get(command.status, -1) < ranks.get(row["status"], -1):
            raise ServiceError("shipment_transition_invalid")
        values["status"] = command.status
        original.update(status=command.status, carrier=command.carrier, tracking_number=command.tracking_number)
    elif command.event == "inspection_correction":
        if not row["received"] or row["inspection"] not in {"failed", "disputed"} or not command.inspection:
            raise ServiceError("inspection_correction_requires_disputed_or_failed_result", 422)
        if command.quantity != row["quantity"]:
            raise ServiceError("return_quantity_mismatch", 422)
        values["inspection"] = command.inspection
        original.update(inspection=command.inspection, inspection_correction_ref=command.receipt_ref)
        if command.inspection == "passed":
            original.update(inspected_quantity=row["quantity"], inspected_unit_ids=original.get("affected_unit_ids", []))
    elif command.event == "return_documents":
        if row["received"] or not all([command.return_address, command.packing_instructions, command.postage_responsibility]):
            raise ServiceError("return_documents_required", 422)
        if command.postage_responsibility != original.get("postage_responsibility"):
            raise ServiceError("postage_policy_changed", 422)
        if command.postage_responsibility == "merchant" and not all([command.prepaid_label_ref, command.carrier, command.tracking_number]):
            raise ServiceError("prepaid_label_required", 422)
        original.update(return_address=command.return_address, packing_instructions=command.packing_instructions,
            prepaid_label_ref=command.prepaid_label_ref, carrier=command.carrier, tracking_number=command.tracking_number,
            document_version=command.business_version, document_ref=command.receipt_ref)
    original.update(updated_at=branch["clock"].isoformat(), correction_reason=command.reason)
    conn.execute(table.update().where(table.c.id == row["id"]).values(
        **values, version=row["version"] + 1, details=original))
