"""Commit-correlated business notifications use the existing task and lease protocol."""
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a, business_schema as b
from globalmail_agent.adapters.conversation_schema import conversations, domain_events
from globalmail_agent.application.business_read_model import scope_where
from globalmail_agent.application.waits import _record_wake_locked
from globalmail_agent.application.event_store import record_event, append_ui_event

CONDITIONS = {"inventory_changed": "inventory", "received": "warehouse_receipt", "inspected": "warehouse_receipt",
    "return_in_transit": "warehouse_receipt", "label_created": "shipment_changed", "shipped": "shipment_changed",
    "delivered": "shipment_changed"}


def publish_operation_event(conn, conv, operation, event, source_id):
    """One committed result can satisfy several waits; each target keeps a versioned receipt."""
    condition = CONDITIONS.get(event, "refund_receipt" if operation["kind"] == "refund" else "manual_execution")
    targets = [operation]
    if condition in {"warehouse_receipt", "inventory"}:
        related = conn.execute(sa.select(b.operations).where(*scope_where(b.operations, conv),
            b.operations.c.order_line_id == operation["order_line_id"], b.operations.c.id != operation["id"],
            b.operations.c.decision_id.is_not(None), b.operations.c.status.in_([
                "accepted", "waiting_condition", "awaiting_execution", "processing", "unknown", "failed"]))) .mappings().all()
        targets.extend(related)
    results = []
    for target in targets:
        source = source_id + ":" + target["external_id"]
        prior = conn.execute(sa.select(domain_events).where(domain_events.c.conversation_id == conv["id"],
            domain_events.c.source == "business_wait", domain_events.c.source_event_id.startswith(source + ":"))).mappings().first()
        if prior:
            results.append({"changed": False, "status": prior["status"]})
            continue
        waits = conn.execute(sa.select(a.wait_conditions).where(a.wait_conditions.c.conversation_id == conv["id"],
            a.wait_conditions.c.operation_id == target["external_id"], a.wait_conditions.c.status == "active")).mappings().all()
        relevant = bool(waits) or target["decision_id"] is not None
        if not relevant:
            record_event(conn, conv, "business_result", source, "operation.result_changed",
                {"operation_id": target["external_id"], "event": event}, suppressed=True)
            results.append({"changed": False, "status": "record_only"})
            continue
        keys = {w["condition_key"] for w in waits} or {condition + ":" + target["external_id"]}
        for key in sorted(keys):
            old = conn.execute(sa.select(a.wake_pending.c.business_version).where(
                a.wake_pending.c.conversation_id == conv["id"], a.wake_pending.c.condition_key == key)).scalar_one_or_none()
            version = max(target["version"], (old or 0) + 1)
            current = conn.execute(sa.select(conversations).where(conversations.c.id == conv["id"])).mappings().one()
            results.append(_record_wake_locked(conn, current, key, version, source_event_id=source + ":" + key))
    append_ui_event(conn, conv["id"], "business.recorded", {"event_id": source_id, "event": event})
    return {"changed": any(r["changed"] for r in results), "status": results[-1]["status"] if results else "record_only"}
