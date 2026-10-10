"""Versioned waits register and receive under the conversation lock, including early results."""
from uuid import uuid4
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from globalmail_agent.adapters.agent_schema import wait_conditions, wake_pending, agent_run_contexts
from globalmail_agent.adapters.business_schema import operations
from globalmail_agent.adapters.conversation_schema import case_issues, conversations, messages, domain_events
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.application.conversation_lock import ServiceError


def register_wait(conn, conv, run_id, condition, operation_id=None, observed_version=0, issue_id=None):
    issue = conn.execute(sa.select(case_issues.c.id).where(case_issues.c.conversation_id == conv["id"],
        case_issues.c.issue_key == "correspondence")).scalar_one()
    if issue_id:
        from uuid import UUID
        try:
            requested = UUID(issue_id)
        except ValueError:
            raise ServiceError("issue_out_of_scope", 422) from None
        selected = conn.execute(sa.select(case_issues).where(case_issues.c.id == requested,
            case_issues.c.conversation_id == conv["id"], *[case_issues.c[k] == conv[k] for k in SCOPE_KEYS])).mappings().first()
        if not selected:
            raise ServiceError("issue_out_of_scope", 422)
        issue = selected["id"]
    key = condition + ":" + (operation_id or ("issue/" + str(issue) if issue_id else "customer"))
    latest = 0 if issue_id else observed_version
    if operation_id:
        row = conn.execute(sa.select(operations).where(operations.c.external_id == operation_id,
            *[operations.c[k] == conv[k] for k in SCOPE_KEYS]).with_for_update()).mappings().first()
        if not row:
            raise ServiceError("operation_out_of_scope", 422)
        from globalmail_agent.application.case_issues import operation_issue
        issue = operation_issue(conn, conv, row)["id"]
        if issue_id and issue != requested:
            raise ServiceError("issue_target_mismatch", 422)
        latest = max(int(row["source_snapshot"].get("version", 0)), row["version"] if row["decision_id"] else 0)
    pending = conn.execute(sa.select(wake_pending).where(wake_pending.c.conversation_id == conv["id"],
        wake_pending.c.condition_key == key).with_for_update()).mappings().first()
    latest = max(latest, pending["business_version"] if pending else 0)
    if (operation_id or issue_id) and observed_version > latest:
        raise ServiceError("future_business_version", 422)
    if latest > observed_version:
        # Commit this trigger, rather than throwing away the wake with a rolled-back draft.
        notification = _record_wake_locked(conn, conv, key, latest)
        if not notification["changed"]:
            raise ServiceError("stale_business_context")
        return False
    conn.execute(wait_conditions.update().where(wait_conditions.c.conversation_id == conv["id"],
        wait_conditions.c.condition_key == key, wait_conditions.c.status == "active").values(status="replaced"))
    conn.execute(sa.insert(wait_conditions).values(id=uuid4(), **{k: conv[k] for k in SCOPE_KEYS},
        conversation_id=conv["id"], run_id=run_id, issue_id=issue, operation_id=operation_id,
        owner=conv["processing_owner"], condition_type=condition, last_seen_business_version=observed_version,
        status="active", condition_key=key))
    return True


def record_wake(conn, conv, condition_key, business_version):
    """Internal controlled receiver: holds slot/conversation before any operation or run lock."""
    from globalmail_agent.application.conversation_lock import lock_conversation
    current = lock_conversation(conn, conv["id"], conv["workspace_id"])
    pieces = condition_key.split(":", 1)
    if len(pieces) != 2 or pieces[0] not in {"manual_execution", "refund_receipt", "warehouse_receipt", "inventory", "shipment_changed"}:
        raise ServiceError("wait_condition_invalid", 422)
    operation = conn.execute(sa.select(operations.c.id).where(operations.c.external_id == pieces[1],
        *[operations.c[k] == current[k] for k in SCOPE_KEYS]).with_for_update()).scalar_one_or_none()
    if operation is None:
        raise ServiceError("operation_out_of_scope", 422)
    return _record_wake_locked(conn, current, condition_key, business_version)


def _record_wake_locked(conn, conv, condition_key, business_version, *, source_event_id=None):
    from globalmail_agent.application.event_store import record_event, append_ui_event
    from globalmail_agent.application.task_queue import invalidate
    if type(business_version) is not int or business_version < 0:
        raise ServiceError("business_version_invalid", 422)
    old = conn.execute(sa.select(wake_pending).where(wake_pending.c.conversation_id == conv["id"],
        wake_pending.c.condition_key == condition_key).with_for_update()).mappings().first()
    if old and old["business_version"] >= business_version:
        return {"status": old["status"], "changed": False}
    condition, operation_id = condition_key.split(":", 1)
    operation = conn.execute(sa.select(operations).where(operations.c.external_id == operation_id,
        *[operations.c[k] == conv[k] for k in SCOPE_KEYS])).mappings().first()
    from globalmail_agent.application.case_issues import operation_issue
    if operation:
        issue = operation_issue(conn, conv, operation)
    elif operation_id.startswith("issue/"):
        from uuid import UUID
        issue = conn.execute(sa.select(case_issues).where(case_issues.c.id == UUID(operation_id[6:]),
            case_issues.c.conversation_id == conv["id"], *[case_issues.c[k] == conv[k] for k in SCOPE_KEYS])).mappings().first()
        operation_id = None
        if not issue:
            raise ServiceError("issue_out_of_scope", 422)
    else:
        raise ServiceError("operation_out_of_scope", 422)
    stmt = pg_insert(wake_pending).values(id=uuid4(), **{k: conv[k] for k in SCOPE_KEYS},
        conversation_id=conv["id"], condition_key=condition_key, business_version=business_version,
        issue_id=issue["id"], operation_id=operation_id,
        status="suppressed_by_human")
    conn.execute(stmt.on_conflict_do_update(index_elements=["conversation_id", "condition_key"],
        set_={"business_version": sa.func.greatest(wake_pending.c.business_version, business_version),
            "status": stmt.excluded.status, "observed_run_id": None,
            "issue_id": issue["id"], "operation_id": operation_id}))
    updated = dict(conv, input_revision=conv["input_revision"] + 1, row_version=conv["row_version"] + 1)
    invalidate(conn, conv["id"])
    conn.execute(conversations.update().where(conversations.c.id == conv["id"]).values(
        input_revision=updated["input_revision"], row_version=updated["row_version"],
        scheduling_state="idle" if conv["scheduling_state"] in {"queued", "running"} else conv["scheduling_state"]))
    trigger = conn.execute(sa.select(messages.c.id).where(messages.c.conversation_id == conv["id"],
        messages.c.seq <= conv["visible_message_seq"], messages.c.sender.in_(["customer", "real_customer"]))
        .order_by(messages.c.seq.desc()).limit(1)).scalar_one_or_none()
    if trigger is None:
        raise ServiceError("customer_trigger_missing")
    event = record_event(conn, updated, "business_wait", source_event_id or condition_key + ":" + str(business_version),
        "operation.result_changed", {"message_id": str(trigger), "condition_key": condition_key,
            "business_version": business_version}, suppressed=True)
    conn.execute(domain_events.update().where(domain_events.c.id == event["id"]).values(
        issue_id=issue["id"], operation_id=operation_id, condition_type=condition, business_version=business_version))
    append_ui_event(conn, conv["id"], "business.wake", {"conversation_id": str(conv["id"]),
        "input_revision": updated["input_revision"],
        "status": "suppressed_by_human"})
    return {"status": "suppressed_by_human", "changed": True}


def consume_wakes(conn, conv, run_id):
    observed = conn.execute(sa.select(agent_run_contexts.c.observed_wakes).where(
        agent_run_contexts.c.run_id == run_id)).scalar_one()
    for wake in observed:
        conn.execute(wake_pending.update().where(wake_pending.c.conversation_id == conv["id"],
            wake_pending.c.condition_key == wake["condition_key"], wake_pending.c.business_version <= wake["business_version"],
            wake_pending.c.status.in_(["pending", "suppressed_by_human"])).values(status="processed", observed_run_id=run_id))
        conn.execute(wait_conditions.update().where(wait_conditions.c.conversation_id == conv["id"],
            wait_conditions.c.condition_key == wake["condition_key"], wait_conditions.c.status == "active",
            wait_conditions.c.last_seen_business_version < wake["business_version"]).values(status="fulfilled"))
    observed_ids = conn.execute(sa.select(agent_run_contexts.c.observed_event_ids).where(
        agent_run_contexts.c.run_id == run_id)).scalar_one()
    for event_id in observed_ids:
        from uuid import UUID
        conn.execute(domain_events.update().where(domain_events.c.id == UUID(event_id),
            domain_events.c.conversation_id == conv["id"],
            *[domain_events.c[k] == conv[k] for k in SCOPE_KEYS],
            domain_events.c.status.in_(["pending", "suppressed_by_human"])).values(status="processed", observed_run_id=run_id))
