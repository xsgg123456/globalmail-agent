"""Stable issue associations resolve candidates against this branch's verified order lines."""
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.conversation_schema import case_issues, messages
from globalmail_agent.adapters.business_schema import branch_orders, branch_order_lines, operations
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.application.business_read_model import scope_where
from globalmail_agent.application.conversation_lock import ServiceError


def ensure_issue(conn, conv, line, kind, source_message_id=None):
    key = str(line["id"]) + ":" + kind
    old = conn.execute(sa.select(case_issues).where(case_issues.c.conversation_id == conv["id"],
        case_issues.c.issue_key == key, *scope_where(case_issues, conv))).mappings().first()
    if old:
        return dict(old)
    order = conn.execute(sa.select(branch_orders).where(branch_orders.c.id == line["order_id"],
        *scope_where(branch_orders, conv))).mappings().one()
    value = dict(id=uuid4(), **{k: conv[k] for k in SCOPE_KEYS}, conversation_id=conv["id"],
        issue_key=key, status="open", version=1, order_line_id=line["id"],
        order_number=order["source_snapshot"].get("display_order_number"), business_type=kind,
        source_message_id=source_message_id, plan_status="candidate")
    conn.execute(sa.insert(case_issues).values(**value))
    return value


def sync_intents(conn, conv, value):
    if conv["mode"] != "simulation":
        return
    orders = conn.execute(sa.select(branch_orders).where(*scope_where(branch_orders, conv))).mappings().all()
    lines = conn.execute(sa.select(branch_order_lines).where(*scope_where(branch_order_lines, conv))).mappings().all()
    visible = {str(r["id"]): r for r in conn.execute(sa.select(messages).where(
        messages.c.conversation_id == conv["id"], messages.c.seq <= conv["visible_message_seq"],
        *scope_where(messages, conv))).mappings()}
    for intent in value.get("intents", []):
        selected = [o for o in orders if intent.get("order_number") == o["source_snapshot"].get("display_order_number")]
        if not intent.get("order_number") and len(orders) == 1:
            selected = orders
        if len(selected) != 1:
            continue
        candidates = [l for l in lines if l["order_id"] == selected[0]["id"] and (
            not intent.get("target_item") or intent["target_item"] in {l["external_id"], l["sku"]})]
        refs = [visible[r["message_id"]] for r in intent.get("sources", []) if r["message_id"] in visible]
        if len(candidates) == 1 and refs:
            kind = {"parts": "spare_part", "shipment": "logistics"}.get(intent["business_type"], intent["business_type"])
            ensure_issue(conn, conv, candidates[0], kind, max(refs, key=lambda r: r["seq"])["id"])


def operation_issue(conn, conv, operation):
    line = conn.execute(sa.select(branch_order_lines).where(branch_order_lines.c.id == operation["order_line_id"],
        *scope_where(branch_order_lines, conv))).mappings().one()
    ref = operation["source_snapshot"].get("selection_ref", {})
    source = None
    if ref.get("message_id"):
        source = conn.execute(sa.select(messages.c.id).where(messages.c.conversation_id == conv["id"],
            sa.or_(sa.cast(messages.c.id, sa.String) == ref["message_id"], messages.c.source_message_id == ref["message_id"]),
            messages.c.seq <= conv["visible_message_seq"], *scope_where(messages, conv))).scalar_one_or_none()
    return ensure_issue(conn, conv, line, operation["kind"], source)


def bind_plan(conn, conv, operation, source_message_id=None):
    issue = operation_issue(conn, conv, operation)
    conn.execute(case_issues.update().where(case_issues.c.id == issue["id"]).values(
        current_operation_id=operation["external_id"], plan_status=operation["status"],
        source_message_id=source_message_id or issue.get("source_message_id"), version=issue["version"] + 1))
    return issue


def validate_issue_target(conn, conv, command, line):
    row = conn.execute(sa.select(case_issues).where(case_issues.c.conversation_id == conv["id"],
        *scope_where(case_issues, conv))).mappings().all()
    match = next((r for r in row if command.issue_id in {str(r["id"]), r["issue_key"]}), None)
    if not match or match["order_line_id"] is not None and (
            match["order_line_id"] != line["id"] or match["business_type"] != command.action):
        raise ServiceError("issue_target_mismatch", 422)
