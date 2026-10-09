"""Per-conversation event order is allocated under its row lock, inside fact commit."""
from uuid import uuid4
from sqlalchemy import insert, select, update, func
from globalmail_agent.adapters.conversation_schema import conversations, ui_events, domain_events
from globalmail_agent.adapters.schema import SCOPE_KEYS

SAFE_KEYS = {"conversation_id", "message_id", "review_id", "run_id", "job_id", "processing_cycle_id",
             "status", "state", "row_version", "input_revision", "outcome", "reason_code",
             "artifact_id", "tool_name", "risk", "revision", "case_revision", "attachment_id", "evidence_epoch",
             "operation_id", "operation_version", "execution_id", "event_id", "event", "wake_status",
             "version", "conversation_version", "linked"}


def append_ui_event(conn, conversation_id, kind, payload):
    if set(payload) - SAFE_KEYS or any(not isinstance(v, (str, int, bool, type(None))) for v in payload.values()):
        raise ValueError("unsafe_event_payload")
    row = conn.execute(select(conversations).where(conversations.c.id == conversation_id)
                       .with_for_update()).mappings().one()
    seq = row["next_seq"] + 1
    conn.execute(update(conversations).where(conversations.c.id == conversation_id)
                 .values(next_seq=seq, updated_at=func.now()))
    conn.execute(insert(ui_events).values(id=uuid4(), **{k: row[k] for k in SCOPE_KEYS},
        conversation_id=conversation_id, seq=seq, kind=kind, payload=payload))
    return seq


def record_event(conn, conversation, source, source_event_id, kind, payload, *, suppressed=False):
    existing = conn.execute(select(*[domain_events.c[k] for k in ("id", *SCOPE_KEYS, "conversation_id", "source", "source_event_id", "kind", "payload", "status")]).where(
        domain_events.c.conversation_id == conversation["id"], domain_events.c.source == source,
        domain_events.c.source_event_id == source_event_id)).mappings().first()
    if existing:
        return dict(existing)
    value = dict(id=uuid4(), **{k: conversation[k] for k in SCOPE_KEYS},
        conversation_id=conversation["id"], source=source, source_event_id=source_event_id,
        kind=kind, payload=payload, status="suppressed_by_human" if suppressed else "pending")
    conn.execute(insert(domain_events).values(**value))
    return value


def read_events(conn, conversation_id, workspace_id, after_seq, limit=100):
    return [dict(row) for row in conn.execute(select(ui_events).where(
        ui_events.c.conversation_id == conversation_id, ui_events.c.workspace_id == workspace_id,
        ui_events.c.seq > after_seq).order_by(ui_events.c.seq).limit(limit)).mappings()]


def record_business_notification(conn, conversation, source_id):
    """Phase 3 record-only internal barrier; no operation injection or Phase 10 wake."""
    from globalmail_agent.application.conversation_lock import lock_conversation
    conversation = lock_conversation(conn, conversation["id"], conversation["workspace_id"])
    existing = conn.execute(select(domain_events).where(
        domain_events.c.conversation_id == conversation["id"], domain_events.c.source == "business_notification",
        domain_events.c.source_event_id == source_id)).mappings().first()
    if existing:
        return dict(existing)
    suppressed = (conversation["processing_owner"] != "agent" or conversation["lifecycle"] != "open"
                  or conversation["auto_run_gate"] != "open")
    event = record_event(conn, conversation, "business_notification", source_id,
        "operation.result_changed", {"conversation_id": str(conversation["id"])}, suppressed=suppressed)
    conn.execute(update(conversations).where(conversations.c.id == conversation["id"]).values(
        input_revision=conversation["input_revision"] + 1,
        row_version=conversation["row_version"] + 1, updated_at=func.now()))
    append_ui_event(conn, conversation["id"], "business.recorded", {
        "conversation_id": str(conversation["id"]), "status": event["status"],
        "input_revision": conversation["input_revision"] + 1,
        "row_version": conversation["row_version"] + 1})
    return event
