"""Deterministic draft rules and description; this never changes active policies."""
import json
from datetime import datetime
from pathlib import Path
from globalmail_agent.adapters.fixture_loader import FIXTURE_ROOT
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.base import canonical, sha

GENERATOR_VERSION = "knowledge-policy/1.0"
EDITABLE = {("return", "window_days_after_delivery"): (1, 3650),
    ("refund", "partial_offer_max_basis_points"): (1, 10000),
    ("replacement", "defect_window_days_after_delivery"): (1, 3650),
    ("spare_part", "defect_window_days_after_delivery"): (1, 3650),
    ("logistics", "stale_tracking_days"): (1, 365)}
KINDS = {"tool_fact", "verified_fixture", "human_decision", "customer_statement", "visual_observation"}
LEDGER = {"order_identity", "paid_amount", "quantity", "customer_choice", "address", "warehouse_receipt",
    "warehouse_inspection", "compatibility", "inventory", "compensation_ledger", "delivery_date"}


def validate_shape(value, template, path=()):
    if path in EDITABLE:
        minimum, maximum = EDITABLE[path]
        if type(value) is not int or not minimum <= value <= maximum:
            raise ServiceError("invalid_policy_number", 422)
    elif path and path[0] == "evidence_requirements":
        if len(path) < 3:
            if not isinstance(value, dict) or set(value) != set(template):
                raise ServiceError("invalid_policy_evidence", 422)
            for key in template:
                validate_shape(value[key], template[key], (*path, key))
        elif path[-1] == "allowed_kinds":
            if (not isinstance(value, list) or not value or len(value) != len(set(value))
                    or any(type(kind) is not str or kind not in KINDS for kind in value)
                    or path[1] in LEDGER and "visual_observation" in value
                    or path[1] in {"paid_amount", "warehouse_receipt", "warehouse_inspection", "compensation_ledger"}
                        and "customer_statement" in value):
                raise ServiceError("invalid_policy_evidence", 422)
        elif path[-1] == "on_missing":
            if value not in {"needs_input", "requires_review"}:
                raise ServiceError("invalid_policy_evidence", 422)
        elif type(value) is not str or not value.strip() or len(value) > 2000:
            raise ServiceError("invalid_policy_evidence", 422)
    elif isinstance(template, dict):
        if not isinstance(value, dict) or set(value) != set(template):
            raise ServiceError("unsupported_policy_schema", 422)
        for key in template:
            validate_shape(value[key], template[key], (*path, key))
    elif value != template or type(value) != type(template):
        raise ServiceError("unsupported_policy_semantics", 422)


def render(policy):
    r, f, replacement, spare, logistics = (policy[k] for k in
        ("return", "refund", "replacement", "spare_part", "logistics"))
    lines = [f"# 模拟售后政策草稿 {policy['version']}", "",
        f"政策编号：{policy['policy_id']}。来源：项目模拟规则。状态：未发布，仅供人工核对。",
        "品牌：" + "、".join(policy["brands"]) + "；市场：" + "、".join(policy["markets"]) + "。",
        "渠道：" + "、".join(policy["channels"]) + "；币种：" + "、".join(policy["currencies"]) + "。",
        "用途仅限 simulation，不能授权真实业务，不换汇。", policy["notice"], "",
        "## 订单、数量与客户选择", "",
        "准确订单、SKU、数量、受影响份额与实付金额必须核验。选择须来自可见客户消息；退款需明确金额和币种。",
        "地址须和当前客户选择版本一致；金额使用最小货币单位整数。", "",
        "## 退货退款", "",
        f"退货窗口：签收后 {r['window_days_after_delivery']} 天，含边界；窗口外交人工。",
        "需原因、数量；非质量退货须未使用且完整。质量问题商家承担寄回费用，其他退货客户自行安排邮资。",
        "寄回须有授权、地址、包装与邮资说明，商家付费时还须预付标签。",
        f"部分退款上限为受影响实付份额的 {f['partial_offer_max_basis_points']} 基点（{f['partial_offer_max_basis_points'] / 100:g}%），整数向下取整。",
        "全额退款前须有仓库收件与质检，数量覆盖受影响份额。例外交人工。",
        "可退余额扣除成功退款及处理中、未知占用；同一申请与执行只扣一次，未知先查原操作。",
        "退款回原支付渠道；内部申请不等于成功，不承诺固定到账日。", "",
        "## 换货补件", "",
        f"质量换货窗口：签收后 {replacement['defect_window_days_after_delivery']} 天；补件窗口：{spare['defect_window_days_after_delivery']} 天。",
        "换货需原准确SKU、库存、当前地址、寄回收件与质检，不先发后退；替代型号交人工核对。",
        "补件需部件/SKU、地区及硬件版本适配、数量、库存、客户选择和当前地址；安全关键部件交人工。",
        "购买备用件不构成免费售后资格。同订单行同份额跨退款、换货、补件检查重复补偿。", "",
        "## 物流和人工", "",
        f"轨迹 {logistics['stale_tracking_days']} 天未更新可查件；签收未收到须核对包裹，不保证到达日。",
        "建标签不等于发货；无记录、不可用、技术失败、未知分开显示。",
        "安全、冲突、未知适配、反复失败与例外交人工；结案须人工确认。", "",
        "## 逐项证据要求", ""]
    requirements = policy.get("evidence_requirements")
    if requirements:
        for code, rule in requirements.items():
            lines.append(f"- {rule['label']}（{code}）：允许 {', '.join(rule['allowed_kinds'])}；{rule['verification']}；缺失：{rule['on_missing']}。")
    else:
        lines.append("此v1规则没有视觉证据映射，图片不能升级为账本或交易资格。")
    return "\n".join(lines) + "\n"


def bundle(policy):
    if not isinstance(policy, dict) or policy.get("version") not in {"1.0.1", "2.0.0"}:
        raise ServiceError("unsupported_policy_schema", 422)
    root = FIXTURE_ROOT if policy["version"] == "1.0.1" else FIXTURE_ROOT.parent / "v2"
    template = json.loads((root / "policies/policy-profile.json").read_text(encoding="utf-8"))
    validate_shape(policy, template)
    schema = {"schema_version": "knowledge-policy/1", "shape": template,
        "editable_numbers": [{"path": list(path), "minimum": bounds[0], "maximum": bounds[1]}
            for path, bounds in EDITABLE.items()], "evidence_kinds": sorted(KINDS), "ledger_conditions": sorted(LEDGER)}
    description = render(policy)
    return {"rules": policy, "rule_schema": schema, "description": description,
        "rules_sha256": sha(canonical(policy)), "schema_sha256": sha(canonical(schema)),
        "description_sha256": sha(description.encode()), "generator_version": GENERATOR_VERSION}


def parse_policy(content: bytes):
    try:
        return bundle(json.loads(content.decode("utf-8")))
    except (ValueError, UnicodeError, TypeError, KeyError):
        raise ServiceError("invalid_policy_schema", 422) from None
