"""Deterministic draft rules and description; this never changes active policies."""
import json
from datetime import datetime
from pathlib import Path
from globalmail_agent.adapters.fixture_loader import FIXTURE_ROOT
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.base import canonical, sha

LEGACY_GENERATOR_VERSION = "knowledge-policy/1.0"
GENERATOR_VERSION = "knowledge-policy/1.1"
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


def render_legacy(policy):
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


def render(policy):
    text = render_legacy(policy)
    r, f = policy['return'], policy['refund']
    replacements = {
        f"退货窗口：签收后 {r['window_days_after_delivery']} 天，含边界；窗口外交人工。":
            f"签收后 {r['window_days_after_delivery']} 天内（含第 {r['window_days_after_delivery']} 天）核对退货原因；窗口外交人工。",
        "需原因、数量；非质量退货须未使用且完整。质量问题商家承担寄回费用，其他退货客户自行安排邮资。":
            "需原因、数量；非质量问题要求商品未使用且配件完整，由客户安排寄回邮资；质量问题的退货标签费用由商家承担。",
        f"部分退款上限为受影响实付份额的 {f['partial_offer_max_basis_points']} 基点（{f['partial_offer_max_basis_points'] / 100:g}%），整数向下取整。":
            f"部分退款方案最高为对应商品实付的 {f['partial_offer_max_basis_points'] / 100:g}%（{f['partial_offer_max_basis_points']} 基点），以受影响份额计算、最小货币单位整数向下取整。先说明具体金额和币种，取得明确同意后再提交；客户询问金额、表达不满或没有回复，都不算接受。",
        "全额退款前须有仓库收件与质检，数量覆盖受影响份额。例外交人工。":
            "全额退款默认在退件签收且验货通过后安排，数量覆盖受影响份额。例外交人工。",
        "退款回原支付渠道；内部申请不等于成功，不承诺固定到账日。":
            "退款回原支付渠道；客服在原销售渠道执行退款后，再依据实际回执通知客户。内部申请不等于成功，不承诺固定到账日。",
        "换货需原准确SKU、库存、当前地址、寄回收件与质检，不先发后退；替代型号交人工核对。":
            "默认更换相同商品编码的产品，核对库存和当前地址，并在退件验货通过后安排换出。缺货时先说明情况，不擅自改颜色、地区版本或型号。替代SKU须客户明确选择并完成适配核验，再交人工确认；不先发后退，例外交人工。",
        "购买备用件不构成免费售后资格。同订单行同份额跨退款、换货、补件检查重复补偿。":
            "购买备用配件不自动成为免费补寄申请。同订单行同份额跨退款、换货、补件检查重复补偿。改方案先查询原申请和已执行记录，检查补件能否取消以及是否已经产生补偿；先核对并处理旧事项，不同时安排两份补偿。",
        f"轨迹 {policy['logistics']['stale_tracking_days']} 天未更新可查件；签收未收到须核对包裹，不保证到达日。":
            f"连续 {policy['logistics']['stale_tracking_days']} 天未更新时进入查件判断；签收未收到须核对包裹，不保证到达日。",
        "建标签不等于发货；无记录、不可用、技术失败、未知分开显示。":
            "生成单号或物流标签不等于承运商已收件；无记录、不可用、技术失败、未知分开显示。"
    }
    for previous, replacement in replacements.items():
        if text.count(previous) != 1:
            raise ServiceError('policy_description_mismatch', 503)
        text = text.replace(previous, replacement)
    return text


def bundle(policy, *, generator_version=GENERATOR_VERSION):
    if not isinstance(policy, dict) or policy.get("version") not in {"1.0.1", "2.0.0"}:
        raise ServiceError("unsupported_policy_schema", 422)
    root = FIXTURE_ROOT if policy["version"] == "1.0.1" else FIXTURE_ROOT.parent / "v2"
    template = json.loads((root / "policies/policy-profile.json").read_text(encoding="utf-8"))
    validate_shape(policy, template)
    schema = {"schema_version": "knowledge-policy/1", "shape": template,
        "editable_numbers": [{"path": list(path), "minimum": bounds[0], "maximum": bounds[1]}
            for path, bounds in EDITABLE.items()], "evidence_kinds": sorted(KINDS), "ledger_conditions": sorted(LEDGER)}
    if generator_version not in {GENERATOR_VERSION, LEGACY_GENERATOR_VERSION}:
        raise ServiceError("unsupported_policy_generator", 422)
    description = render(policy) if generator_version == GENERATOR_VERSION else render_legacy(policy)
    return {"rules": policy, "rule_schema": schema, "description": description,
        "rules_sha256": sha(canonical(policy)), "schema_sha256": sha(canonical(schema)),
        "description_sha256": sha(description.encode()), "generator_version": generator_version}


def parse_policy(content: bytes, *, generator_version=GENERATOR_VERSION):
    try:
        return bundle(json.loads(content.decode("utf-8")), generator_version=generator_version)
    except (ValueError, UnicodeError, TypeError, KeyError):
        raise ServiceError("invalid_policy_schema", 422) from None
