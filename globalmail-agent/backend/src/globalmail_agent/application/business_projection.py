"""Permitted fact fields; raw source snapshots are never public payloads."""
ORDER_FIELDS = {"order_id", "customer_id", "brand", "market", "channel", "currency", "paid_minor",
    "refunded_minor", "pending_refund_minor", "purchase_at", "delivered_at", "snapshot_at", "source_kind",
    "display_order_number", "display_order_number_source", "pricing_source", "tax_and_discount_semantics"}
LINE_FIELDS = {"line_id", "sku", "quantity", "paid_minor", "hardware_revision", "unit_allocations",
               "refunded_minor", "pending_refund_minor", "source_kind"}
LEDGER_FIELDS = {"operation_id", "order_id", "order_line_id", "issue_id", "kind", "status", "quantity",
    "amount_minor", "currency", "part_id", "execution_ids", "affected_unit_ids", "execution_id", "parcel_id",
    "purpose", "tracking_number", "carrier", "updated_at", "return_id", "line_id", "received", "inspection",
    "source_kind", "snapshot_at", "cancelable", "failure_code", "inspected_quantity", "inspected_unit_ids",
    "version", "item_id", "address_version", "region_spec", "hardware_revision", "confirmed_not_executed", "attempt_no", "receipt_ref", "plan",
    "authorized_return_reference", "return_address", "packing_instructions", "postage_responsibility", "prepaid_label", "prepaid_label_ref",
    "waiting_conditions", "cancellation_requested", "document_version", "document_ref", "inspection_correction_ref",
    "correction_reason", "correction_of_execution_id", "correction_ref", "staff_id"}


def project(record, allowed):
    return {key: record[key] for key in allowed if key in record}
