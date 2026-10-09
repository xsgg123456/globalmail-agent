"""Exact visible customer quotes bind a candidate choice to verified transaction fields."""
import re
import sqlalchemy as sa
from globalmail_agent.adapters.conversation_schema import messages, case_issues
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.adapters.body_store import read_body
from globalmail_agent.application.business_read_model import scope_where
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.application.understanding_revisions import current_understanding


def visible_quote(conn, store, conv, ref):
    rows = conn.execute(sa.select(messages).where(messages.c.conversation_id == conv["id"],
        messages.c.seq <= conv["visible_message_seq"], messages.c.sender.in_(["customer", "real_customer"]),
        *scope_where(messages, conv))).mappings().all()
    row = next((r for r in rows if ref.message_id in {str(r["id"]), r["source_message_id"]}), None)
    if not row or ref.quote not in read_body(conn, store, conv, row["body_object_id"]):
        raise ServiceError("selection_source_invalid", 422)
    return row


def normalize_selection(conn, store, conv, context, command, data):
    message = visible_quote(conn, store, conv, command.selection_ref)
    issue = conn.execute(sa.select(case_issues).where(case_issues.c.conversation_id == conv["id"],
        *scope_where(case_issues, conv))).mappings().all()
    if not any(command.issue_id in {str(r["id"]), r["issue_key"]} for r in issue):
        raise ServiceError("issue_out_of_scope", 422)
    choices = data["state"]["customer_choices"]
    matching = [r for r in choices if r.get("source_message_id") == message["source_message_id"]]
    if not matching:
        known = current_understanding(conn, store, conv, context.run_id) or {}
        category = {"spare_part": "parts", "logistics": "shipment"}.get(command.action, command.action)
        intents = [i for i in known.get("intents", []) if i["business_type"] == category and i["consent"] == "explicit"
            and not i.get("condition") and i.get("requested_solution") and any(
                r["message_id"] == str(message["id"]) and r["quote"] == command.selection_ref.quote for r in i["sources"])]
        quote = command.selection_ref.quote
        line, order = data["line"], data["order"]
        if len(intents) != 1 or intents[0].get("order_number") not in {None, order["display_order_number"]}:
            raise ServiceError("customer_selection_required", 422)
        if intents[0].get("target_item") not in {None, line["sku"], line["line_id"], line.get("product_name"), command.item_id}:
            raise ServiceError("selection_target_mismatch", 422)
        if len(data.get("all_lines", [line])) > 1 and line["sku"] not in quote and line["line_id"] not in quote:
            raise ServiceError("selection_target_ambiguous", 422)
        if command.quantity != 1 and not re.search(r"(?<!\d)" + str(command.quantity) + r"(?!\d)", quote):
            raise ServiceError("selection_quantity_required", 422)
        if command.action == "refund":
            decimal = f"{command.amount_minor / 100:.2f}" if command.amount_minor is not None else ""
            if not command.currency or command.currency not in quote or not decimal or decimal not in quote:
                raise ServiceError("selection_amount_currency_required", 422)
        if command.action in {"replacement", "spare_part"} and (command.item_id or line["sku"]) not in quote:
            raise ServiceError("selection_item_required", 422)
        if command.affected_unit_ids and command.quantity < line["quantity"] and any(unit not in quote for unit in command.affected_unit_ids):
            raise ServiceError("selection_units_required", 422)
        choice = {"source_kind": "customer_statement", "evidence_ref": "message:" + str(message["id"]),
            "source_message_id": message["source_message_id"], "source_message_seq": message["seq"],
            "action": command.action, "kind": command.action, "accepted": True,
            "order_line_id": line["line_id"], "quantity": command.quantity, "amount_minor": command.amount_minor,
            "currency": command.currency, "item_id": command.item_id or line["sku"],
            "address_version": command.address_version, "affected_unit_ids": command.affected_unit_ids}
        choices.append(choice)
    else:
        if any(r.get("source_message_seq", 0) > message["seq"] for r in choices
                if r.get("order_line_id") in {None, data["line"]["line_id"]}):
            raise ServiceError("selection_superseded", 422)
        if command.affected_unit_ids is not None and command.quantity < data["line"]["quantity"] and not any(
                set(r.get("affected_unit_ids") or []) == set(command.affected_unit_ids) for r in matching):
            raise ServiceError("selection_units_mismatch", 422)
        known = current_understanding(conn, store, conv, context.run_id) or {}
        later = {str(r["id"]) for r in conn.execute(sa.select(messages.c.id).where(
            messages.c.conversation_id == conv["id"], messages.c.seq > message["seq"],
            messages.c.seq <= conv["visible_message_seq"], messages.c.sender.in_(["customer", "real_customer"]))).mappings()}
        if any(i["consent"] in {"explicit", "declined", "conditional"} and
                i.get("order_number") in {None, data["order"]["display_order_number"]} and
                i.get("target_item") in {None, data["line"]["sku"], data["line"]["line_id"], command.item_id} and
                any(ref["message_id"] in later for ref in i["sources"]) for i in known.get("intents", [])):
            raise ServiceError("selection_superseded", 422)
    if command.address_ref:
        visible_quote(conn, store, conv, command.address_ref)
    if command.address_version is not None and command.address_version != data["state"].get("address_confirmation", {}).get("version"):
        raise ServiceError("stale_address", 422)
    return message


def cancellation_source(conn, store, conv, context, ref, operation):
    message = visible_quote(conn, store, conv, ref)
    latest = conn.execute(sa.select(sa.func.max(messages.c.seq)).where(messages.c.conversation_id == conv["id"],
        messages.c.sender.in_(["customer", "real_customer"]), messages.c.seq <= conv["visible_message_seq"])).scalar_one()
    if message["seq"] != latest:
        raise ServiceError("selection_superseded", 422)
    known = current_understanding(conn, store, conv, context.run_id) or {}
    target = operation["source_snapshot"].get("item_id")
    choices = [i for i in known.get("intents", []) if not i.get("condition") and i["consent"] in {"explicit", "declined"}
        and i.get("target_item") in {None, target, operation["source_snapshot"]["order_line_id"]}
        and any(r["message_id"] == str(message["id"]) and r["quote"] == ref.quote for r in i["sources"])]
    # Direct cancellation remains usable before an understanding response exists.
    conditional = re.search(r"\b(if|unless|whether|can|could)\b|不要取消|不取消|不想取消|如果|是否", ref.quote, re.IGNORECASE)
    negated = re.search(r"\b(?:not|never|don't|do not)\b.{0,30}\bcancel", ref.quote, re.IGNORECASE)
    explicit = not conditional and not negated and re.search(
        r"\bcancel(?:lation)?\b|\bstorni\w*|取消|不要|改为", ref.quote, re.IGNORECASE)
    category = {"refund": r"refund|rückerstatt|退款", "replacement": r"replacement|exchange|ersatz|换货",
        "spare_part": r"spare|part|补件|配件", "return": r"return|rücksend|退货",
        "logistics": r"investigation|shipment|查件|物流"}[operation["kind"]]
    explicit = explicit and (operation["external_id"] in ref.quote or re.search(category, ref.quote, re.IGNORECASE))
    if not explicit and not any(i["consent"] == "declined" or i["business_type"] != {
            "spare_part": "parts", "logistics": "shipment"}.get(operation["kind"], operation["kind"]) for i in choices):
        raise ServiceError("cancellation_selection_required", 422)
    return message
