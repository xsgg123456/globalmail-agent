"""Strict public preview command and deterministic policy interpreter."""
import hashlib
import json
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

from globalmail_agent.domain.policy_conditions import Conditions, affected_share, customer_choice, integer, reported_problem, date
from globalmail_agent.domain.policy_fulfillment import address, availability, logistics, return_conditions, warehouse, window
from globalmail_agent.domain.policy_ledger import ledger

INTERPRETER_VERSION = "deterministic-eligibility/1.0"


class EligibilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["refund", "return", "replacement", "spare_part", "logistics"]
    order_line_id: str | None = Field(default=None, min_length=1, max_length=160)
    quantity: int = Field(default=1, ge=1)
    amount_minor: int | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    item_id: str | None = Field(default=None, min_length=1, max_length=160)


def validate_profile(policy):
    if policy.get("version") not in ("1.0.1", "2.0.0"):
        raise ValueError("unsupported_policy_version")
    for section, key, approved in (("return", "window_days_after_delivery", 30),
            ("refund", "partial_offer_max_basis_points", 2000),
            ("replacement", "defect_window_days_after_delivery", 365),
            ("spare_part", "defect_window_days_after_delivery", 365), ("logistics", "stale_tracking_days", 7)):
        value = policy[section][key]
        if not integer(value) or value != approved:
            raise ValueError("unsupported_rule_value")
    for section, key in (("return", "receipt_required_for_refund"), ("return", "inspection_required_for_refund"),
            ("refund", "full_refund_needs_return"), ("replacement", "return_required"), ("replacement", "inspection_required")):
        if policy[section].get(key) is not True:
            raise ValueError("unsupported_prerequisite")


def _scope(checks, context, order, policy):
    missing = [key for key in ("brand", "market", "channel", "currency") if not order.get(key)]
    if missing:
        checks.add("policy_scope", "订单缺适用范围字段：" + "、".join(missing), "needs_input")
        return
    covered = all(order[key] in policy[plural] for key, plural in (
        ("brand", "brands"), ("market", "markets"), ("channel", "channels"), ("currency", "currencies")))
    if context.get("mode") not in policy.get("allowed_modes", []):
        covered = False
    checks.add("policy_scope", "政策适用范围已核对" if covered else "此订单或模式不在政策范围内",
               "fulfilled" if covered else "ineligible", [order] if covered else [])
    current = date(context.get("as_of"))
    available = date(policy.get("available_at"))
    effective = date(policy.get("effective_at") or policy.get("effective_from"))
    end = date(policy.get("effective_to"))
    if not current or not available or not effective:
        checks.add("policy_time", "政策可用时间或当前截点未知", "needs_input")
    elif current < available or current < effective or (end and current >= end):
        checks.add("policy_time", "此版本在当前截点尚不可用或已失效", "ineligible")


def _refund(checks, context, command, units, share_paid, remaining):
    amount, currency = command.amount_minor, command.currency
    if amount is None or currency is None:
        checks.add("refund_amount", "需要明确退款金额和币种", "needs_input")
        return
    if currency != context["order"].get("currency"):
        checks.add("refund_currency", "币种须与订单一致，禁止自动换汇", "ineligible")
        return
    if amount == 0:
        checks.add("refund_amount", "退款金额必须大于零", "ineligible")
        return
    if share_paid is None or remaining is None:
        checks.add("refund_amount", "退款份额或可退余额未核实", "needs_input")
        return
    if amount > min(share_paid, remaining):
        checks.add("refund_amount", "退款金额超过受影响实付份额或可退余额", "ineligible")
        return
    policy = context["policy"]
    if amount == share_paid:
        window(checks, context["order"], context["as_of"], policy["return"]["window_days_after_delivery"])
        warehouse(checks, context["state"], context["line"], units, command.quantity)
        checks.add("refund_amount", "全额退款金额在受影响份额内", records=[context["line"]])
    else:
        maximum = share_paid * policy["refund"]["partial_offer_max_basis_points"] // 10000
        if amount > maximum:
            checks.add("refund_amount", "部分退款超过政策比例上限，须人工审查", "requires_review")
        else:
            checks.add("refund_amount", "部分退款未超过整数向下取整上限", records=[context["line"]])


def evaluate_eligibility(command, context):
    """Consume only a scoped BusinessQueries context; never load a fallback policy."""
    if not isinstance(command, EligibilityRequest):
        command = EligibilityRequest.model_validate(command)
    policy = context["policy"]
    validate_profile(policy)
    checks, order, line = Conditions(policy), context.get("order"), context.get("line")
    state = context.get("state") or {}
    remaining = None
    if not order or not line:
        checks.add("order_identity", "须明确当前订单行", "needs_input")
    else:
        _scope(checks, context, order, policy)
        identity = (checks.evidence("order_identity", order, "当前客户订单")
            and checks.evidence("order_identity", line, "准确订单商品"))
        if identity:
            checks.add("order_identity", "当前客户准确订单商品已核验", records=[order, line])
        if command.order_line_id and command.order_line_id != line.get("line_id"):
            checks.add("order_identity", "目标订单行与已核验上下文不一致", "ineligible")
        paid_valid = checks.evidence("paid_amount", line, "订单行实付金额") if command.action != "logistics" else True
        if command.action != "logistics" and not integer(line.get("paid_minor")):
            checks.add("paid_amount", "订单行实付须为非负最小货币单位整数", "needs_input")
            paid_valid = False
        elif command.action != "logistics" and paid_valid:
            checks.add("paid_amount", "订单行实付金额已核验", records=[line])
        if command.action == "logistics":
            logistics(checks, context, line)
        elif not integer(line.get("quantity"), 1):
            checks.add("quantity", "订单行数量须为正整数", "needs_input")
        else:
            choice = customer_choice(checks, state, line, command) if command.action != "logistics" else None
            units, share_paid = affected_share(checks, line, command, choice)
            remaining = ledger(checks, state, line, order.get("currency"), units, command.action, order) if identity and paid_valid else None
            if command.action == "refund":
                _refund(checks, context, command, units, share_paid, remaining)
            elif command.action == "return":
                window(checks, order, context["as_of"], policy["return"]["window_days_after_delivery"])
                return_conditions(checks, state, line)
            elif command.action in ("replacement", "spare_part"):
                window(checks, order, context["as_of"], policy[command.action]["defect_window_days_after_delivery"])
                reported_problem(checks, state, line, item_id=command.item_id if command.action == "spare_part" else None)
                purchases = [row for row in state.get("customer_choices", [])
                    if row.get("order_line_id") == line["line_id"] and row.get("source_message_id")
                    in state.get("visible_source_message_ids", []) and (row.get("purpose") == "purchase"
                    or row.get("kind") == "purchase_spare_part")]
                if command.action == "spare_part" and purchases:
                    checks.add("spare_entitlement", "购买备用件不构成免费售后资格", "ineligible")
                availability(checks, context, line, order, command)
                address(checks, state, choice, order)
                if command.action == "replacement":
                    warehouse(checks, state, line, units, command.quantity)
    risk = [row for row in state.get("risk_flags", []) if row.get("status") == "active"]
    for row in risk:
        if checks.evidence("safety", row, "安全风险", "requires_review"):
            checks.add("safety", "有效安全风险须人工审查", "requires_review", [row])
    data = {"outcome": checks.outcome(), "conditions": checks.items, "policy_id": policy["policy_id"],
        "version": policy["version"], "authorized": False, "publication_status": "unpublished",
        "remaining_refund_minor": remaining, "missing_fields": checks.missing()}
    payload = {"command": command.model_dump(), "context": context, "result": data,
               "interpreter": INTERPRETER_VERSION}
    data["decision_id"] = "preview-" + hashlib.sha256(json.dumps(payload, sort_keys=True,
        ensure_ascii=False, default=str, separators=(",", ":")).encode("utf-8")).hexdigest()
    return data
