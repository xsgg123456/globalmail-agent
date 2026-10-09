"""Literal parameters in a customer quote must agree with the normalized plan."""
import re
from globalmail_agent.application.conversation_lock import ServiceError


def exact_identifier(value, quote):
    return bool(value and re.search(r"(?<![\w-])" + re.escape(value) + r"(?![\w-])", quote))


def intent_applies_to_plan(intent, data, command):
    number = intent.get("order_number")
    if number not in {None, data["order"]["display_order_number"]}:
        return False
    target = intent.get("target_item")
    if target in {None, command.item_id, data["line"]["line_id"], data["line"]["sku"], data["line"].get("product_name")}:
        return True
    resolved = [line for line in data.get("all_lines", [data["line"]])
        if target in {line["line_id"], line["sku"], line.get("product_name")}]
    # An unknown target may be a changed plan; only a verified different line is independent.
    if not resolved or any(line["line_id"] == data["line"]["line_id"] for line in resolved):
        return True
    return not any(exact_identifier(line["line_id"], ref["quote"]) or exact_identifier(line["sku"], ref["quote"])
        or line.get("product_name") and line["product_name"] in ref["quote"]
        for line in resolved for ref in intent.get("sources", []))


def validate_declared_parameters(command, data, quote):
    counts = re.findall(r"(?<![\w.])(\d+)\s*(?:unit(?:\(s\)|s)?|replacement(?:\(s\)|s)?|items?|pieces?|件|个)",
        quote, re.IGNORECASE)
    if any(int(count) != command.quantity for count in counts):
        raise ServiceError("selection_quantity_mismatch", 422)
    if command.action not in {"replacement", "spare_part"}:
        return
    target = command.item_id or data["line"]["sku"]
    allowed = {target, data["line"]["sku"], data["line"]["line_id"], data["order"]["display_order_number"]}
    allowed.update(command.affected_unit_ids or [])
    codes = re.findall(r"(?<![\w-])[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)+(?![\w-])", quote)
    if any(any(character.isdigit() for character in code) and code not in allowed for code in codes):
        raise ServiceError("selection_target_mismatch", 422)
