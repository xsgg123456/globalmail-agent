"""Evidence and condition helpers for a deterministic, read-only preview."""
from datetime import datetime

TRUSTED_KINDS = {"tool_fact", "verified_fixture", "human_decision"}
OUTCOME_PRIORITY = ("requires_review", "ineligible", "needs_input", "wait")


def integer(value, minimum=0):
    return type(value) is int and value >= minimum


def date(value):
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value)
        return parsed if parsed.tzinfo and parsed.utcoffset() is not None else None
    except (TypeError, ValueError):
        return None


def reference(record):
    value = record.get("evidence_ref")
    if isinstance(value, dict):
        value = value.get("evidence_id") or value.get("source_ref")
    return value if isinstance(value, str) and value else None


class Conditions:
    def __init__(self, policy):
        self.policy, self.items = policy, []

    def add(self, code, label, status="fulfilled", records=()):
        self.items.append({"code": code, "label": label, "status": status,
                           "fulfilled_by": sorted({ref for r in records if (ref := reference(r))})})
        return status == "fulfilled"

    def evidence(self, code, record, label, missing="needs_input"):
        requirement = self.policy.get("evidence_requirements", {}).get(code)
        allowed = set(requirement["allowed_kinds"]) if requirement else TRUSTED_KINDS | (
            {"customer_statement"} if code == "customer_choice" else set())
        kind = record.get("source_kind") if isinstance(record, dict) else None
        if not record or not reference(record):
            return self.add(code, label, missing)
        if kind not in allowed or record.get("verified") is False:
            status = requirement.get("on_missing", missing) if requirement else "requires_review"
            return self.add(code, label + "：来源需核验", status)
        return True

    def outcome(self):
        statuses = {item["status"] for item in self.items}
        return next((value for value in OUTCOME_PRIORITY if value in statuses), "eligible")

    def missing(self):
        return sorted({item["code"] for item in self.items if item["status"] in OUTCOME_PRIORITY})


def customer_choice(checks, state, line, command):
    visible = set(state.get("visible_source_message_ids", []))
    candidates = [choice for choice in state.get("customer_choices", [])
        if choice.get("order_line_id") in (None, line["line_id"])]
    if not candidates:
        checks.add("customer_choice", "需要客户明确接受此次方案", "needs_input")
        return None
    if len(candidates) > 1:
        if any(not integer(c.get("source_message_seq"), 1) for c in candidates):
            checks.add("customer_choice", "客户选择先后顺序未确认", "needs_input")
            return None
        newest = max(c["source_message_seq"] for c in candidates)
        latest = [c for c in candidates if c["source_message_seq"] == newest]
        if len(latest) != 1:
            checks.add("customer_choice", "同一封来信有多条选择，需明确此次方案", "needs_input")
            return None
        choice = latest[0]
    else:
        choice = candidates[0]
    if choice.get("source_message_id") not in visible:
        checks.add("customer_choice", "客户选择须关联当前可见消息", "needs_input")
        return None
    if not checks.evidence("customer_choice", choice, "客户明确选择"):
        return None
    exact = (choice.get("order_line_id") == line["line_id"]
        and (choice.get("action") or choice.get("kind")) == command.action
        and choice.get("accepted") is True and integer(choice.get("quantity"), 1)
        and choice["quantity"] == command.quantity)
    if command.action == "refund":
        exact = exact and integer(choice.get("amount_minor")) and (
            choice["amount_minor"] == command.amount_minor and choice.get("currency") == command.currency)
    if command.action in ("spare_part", "replacement"):
        target = command.item_id or (line.get("sku") if command.action == "replacement" else None)
        exact = exact and bool(target) and (choice.get("item_id") or choice.get("part_id")) == target
    if not exact:
        checks.add("customer_choice", "最新选择尚未明确接受此动作、数量或金额币种", "needs_input")
        return None
    checks.add("customer_choice", "客户明确接受此次方案", records=[choice])
    return choice


def affected_share(checks, line, command, choice):
    quantity, paid = line.get("quantity"), line.get("paid_minor")
    if not integer(quantity, 1) or not integer(paid):
        checks.add("quantity", "订单行数量或实付字段不完整", "needs_input")
        return None, None
    if command.quantity > quantity:
        checks.add("quantity", "申请数量超过订单行数量", "ineligible")
        return None, None
    allocations = line.get("unit_allocations", [])
    if command.quantity == quantity:
        units = {row.get("unit_id") for row in allocations} if allocations else {str(i) for i in range(quantity)}
        if allocations and (len(units) != quantity or any(not isinstance(unit, str) for unit in units)):
            checks.add("quantity", "订单单位份额标识不一致", "requires_review")
            return None, None
        checks.add("quantity", "此次涉及整行商品数量", records=[line])
        return units, paid
    units = (choice or {}).get("affected_unit_ids")
    if not isinstance(units, list) or not allocations:
        checks.add("quantity", "部分数量须明确单位份额及实付分摊", "needs_input")
        return None, None
    allocation = {row.get("unit_id"): row.get("paid_minor") for row in allocations}
    valid = (all(isinstance(key, str) and key for key in allocation)
        and all(integer(value) for value in allocation.values())
        and len(allocation) == quantity == len(allocations) and sum(allocation.values()) == paid
        and all(isinstance(unit, str) for unit in units)
        and len(units) == len(set(units)) == command.quantity and set(units) <= allocation.keys())
    if not valid:
        checks.add("quantity", "受影响份额或金额分摊不一致", "requires_review")
        return None, None
    checks.add("quantity", "受影响单位份额已明确", records=[line])
    return set(units), sum(allocation[unit] for unit in units)


def reported_problem(checks, state, line, allowed=("defect", "missing"), item_id=None):
    evidence = [row for row in state.get("problem_evidence", [])
        if row.get("order_line_id") == line["line_id"] and row.get("reason") in allowed]
    if not evidence and state.get("verified_fixture") is True and reference(state):
        # These remain the explicit initial fixture facts, never model/tool conclusions.
        if state.get("defect_confirmed_in_simulation") is True and "defect" in allowed:
            evidence = [{"reason": "defect", "source_kind": "verified_fixture", "evidence_ref": reference(state)}]
        elif state.get("confirmed_missing_part_id") and "missing" in allowed:
            evidence = [{"reason": "missing", "item_id": state["confirmed_missing_part_id"],
                "source_kind": "verified_fixture", "evidence_ref": reference(state)}]
    if not evidence:
        checks.add("reported_problem", "需要当前商品的问题及原因依据", "needs_input")
        return None
    row = evidence[-1]
    if item_id and (row.get("item_id") or row.get("part_id")) != item_id:
        checks.add("reported_problem", "问题依据须明确对应此次准确配件", "needs_input")
        return None
    if row.get("uncertain") is True or row.get("kind") == "hypothesis":
        checks.add("reported_problem", "问题证据仍不确定", "needs_input")
        return None
    if row.get("source_kind") == "visual_observation" and row.get("reason") == "missing":
        checks.add("reported_problem", "局部图片不能证明缺件", "needs_input")
        return None
    if row.get("source_kind") == "customer_statement" and (
            row.get("source_message_id") not in state.get("visible_source_message_ids", [])):
        checks.add("reported_problem", "问题申报须来自可见客户消息", "needs_input")
        return None
    if not checks.evidence("reported_problem", row, "客户问题依据"):
        return None
    checks.add("reported_problem", "当前商品问题依据已具备", records=[row])
    return row
