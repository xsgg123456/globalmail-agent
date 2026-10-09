"""Natural full/same-item choices bind only to unambiguous verified transaction values."""
import re


def natural_binding(command, data, quote):
    if re.search(r"\b(if|unless|whether|not|never|don't|do not)\b|如果|是否|不要|不需要|不想|不退款", quote, re.IGNORECASE):
        return False
    line, order = data["line"], data["order"]
    if len(data.get("all_lines", [line])) != 1 or line["quantity"] != 1 or command.quantity != 1:
        return False
    if command.action == "refund":
        text = quote
        for identity in (order.get("display_order_number"), line.get("sku"), line.get("line_id")):
            if identity:
                text = text.replace(identity, "")
        currencies = re.findall(r"\b(?:USD|EUR|GBP|CAD|AUD|CNY|JPY|CHF|HKD|NZD|SGD)[A-Za-z0-9]*\b", text, re.IGNORECASE)
        qualified = re.findall(r"(?:\b(?:in|currency|währung)\s*[:=]?\s*|(?:币种|货币)\s*[：:=]?\s*)"
            r"([A-Za-z][A-Za-z0-9]{2,7})\b", text, re.IGNORECASE)
        currencies.extend(code for code in qualified if code.casefold() not in {"full", "voll", "voller", "total"})
        if re.search(r"\d|[$€£¥]", text) or any(code.upper() != order.get("currency") for code in currencies):
            return False
        return bool(re.search(r"full refund|fully refund|vollst[aä]ndig\w*.*r[uü]ckerstatt|全额退款", quote, re.IGNORECASE)
            and command.amount_minor == line.get("paid_minor") and command.currency == order.get("currency"))
    if command.action == "replacement":
        return bool(re.search(r"replacement|exchange|ersatz|换货|更换", quote, re.IGNORECASE)
            and (command.item_id or line["sku"]) == line["sku"])
    if command.action == "spare_part":
        candidates = {r["part_id"] for r in data.get("compatibility", []) if r.get("sku") == line["sku"]
            and r.get("hardware_revision") == line.get("hardware_revision") and "simulation" in r.get("allowed_modes", [])}
        target = data["state"].get("confirmed_missing_part_id") or data["state"].get("requested_part_id")
        if target:
            candidates &= {target}
        return bool(re.search(r"remote|spare|part|fernbedien|ersatzteil|补件|遥控|配件", quote, re.IGNORECASE)
            and candidates == {command.item_id})
    return False
