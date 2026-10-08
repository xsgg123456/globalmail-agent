"""Offline deterministic policy revision; never publish or rewrite the v1 bundle."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
GENERATOR_VERSION = "1.0.0"
SCHEMA_VERSION = "policy-profile/2.0"
RULE_SECTIONS = ("identity", "return", "refund", "replacement", "spare_part", "logistics",
                 "conflicts", "human_review")
CONDITIONS = ("order_identity", "quantity", "paid_amount", "customer_choice", "address",
              "reported_problem", "return_condition", "warehouse_receipt", "warehouse_inspection",
              "compatibility", "inventory", "compensation_ledger", "delivery_date", "safety")
KINDS = ("tool_fact", "verified_fixture", "human_decision", "customer_statement", "visual_observation")


def digest(content):
    return hashlib.sha256(content).hexdigest()


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def validate(policy, previous):
    if policy["version"] != "2.0.0" or policy["publication_status"] != "unpublished":
        raise ValueError("revision_must_remain_unpublished")
    if policy["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported_schema")
    # The revision adds evidence requirements; existing approved business rules stay exact.
    for section in RULE_SECTIONS:
        if json.dumps(policy.get(section), sort_keys=True) != json.dumps(previous[section], sort_keys=True):
            raise ValueError("v1_rule_changed:" + section)
    for key in ("brands", "markets", "channels", "currencies", "allowed_modes"):
        if policy[key] != previous[key]:
            raise ValueError("v1_scope_changed:" + key)
    if policy["supersedes"] != {"policy_id": previous["policy_id"], "version": previous["version"]}:
        raise ValueError("invalid_supersedes")
    requirements = policy.get("evidence_requirements", {})
    if set(requirements) != set(CONDITIONS):
        raise ValueError("incomplete_evidence_requirements")
    for code, requirement in requirements.items():
        if (not isinstance(requirement["allowed_kinds"], list) or not requirement["allowed_kinds"]
                or any(kind not in KINDS for kind in requirement["allowed_kinds"])
                or not isinstance(requirement["verification"], str) or not requirement["verification"]):
            raise ValueError("invalid_requirement:" + code)
        if requirement["on_missing"] not in ("needs_input", "requires_review"):
            raise ValueError("invalid_missing_disposition:" + code)
    for code in ("paid_amount", "warehouse_receipt", "warehouse_inspection", "compensation_ledger"):
        if "visual_observation" in requirements[code]["allowed_kinds"]:
            raise ValueError("visual_cannot_fulfill_ledger:" + code)


def rule_schema():
    requirement = {"type": "object", "additionalProperties": False,
        "required": ["label", "allowed_kinds", "verification", "on_missing"],
        "properties": {"label": {"type": "string", "minLength": 1},
            "allowed_kinds": {"type": "array", "minItems": 1, "uniqueItems": True,
                "items": {"enum": list(KINDS)}}, "verification": {"type": "string", "minLength": 1},
            "on_missing": {"enum": ["needs_input", "requires_review"]}}}
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object",
        "required": ["policy_id", "version", "schema_version", "publication_status", "effective_at",
            "supersedes", "evidence_requirements", *RULE_SECTIONS],
        "properties": {"policy_id": {"const": "SIM-AFTERSALES-2026-10-V2"}, "version": {"const": "2.0.0"},
            "schema_version": {"const": SCHEMA_VERSION}, "publication_status": {"const": "unpublished"},
            "effective_at": {"type": "string", "format": "date-time"},
            "evidence_requirements": {"type": "object", "required": list(CONDITIONS),
                "additionalProperties": False, "properties": {code: requirement for code in CONDITIONS}},
            "refund": {"type": "object", "properties": {"partial_offer_max_basis_points": {"type": "integer", "const": 2000}}},
            "return": {"type": "object", "properties": {"window_days_after_delivery": {"type": "integer", "const": 30}}},
            "replacement": {"type": "object", "properties": {"defect_window_days_after_delivery": {"type": "integer", "const": 365}}},
            "spare_part": {"type": "object", "properties": {"defect_window_days_after_delivery": {"type": "integer", "const": 365}}},
            "logistics": {"type": "object", "properties": {"stale_tracking_days": {"type": "integer", "const": 7}}}}}


def render(policy):
    r, f, replacement, spare, logistics = (policy[k] for k in
        ("return", "refund", "replacement", "spare_part", "logistics"))
    lines = [f"# 三品牌隔离试运行售后政策 {policy['version']}", "",
        f"政策编号：{policy['policy_id']}。来源：项目拟定模拟规则。状态：未发布，内容核对待完成。",
        f"本修订拟生效时间：{policy['effective_at']}；正式同版本发布前只供管理预览，不能授权申请或履约。",
        f"替代关系：{policy['supersedes']['policy_id']} / {policy['supersedes']['version']}；原场景继续固定 v1。",
        "这是独立政策修订包，不是完整知识包。技术检查通过不表示业务负责人已经核准。", "",
        "## 适用范围", "",
        "品牌：" + "、".join(policy["brands"]) + "。市场：" + "、".join(policy["markets"]) + "。",
        "渠道：" + "、".join(policy["channels"]) + "；币种：" + "、".join(policy["currencies"]) + "。",
        policy["notice"], "", "## 订单、选择与数量", "",
        "先由业务工具核验订单、准确商品、受影响数量和实付金额。多商品或数量份额不明确先补问。",
        "客户接受必须来自可见的客户消息，明确动作；退款须明确接受金额和币种。地址确认须与当前选择版本一致。",
        "客户材料和图片不改变业务账本。金额用最小货币单位整数，不换汇；比例上限用整数向下取整。", "",
        "## 退货与退款", "",
        f"退货窗口为签收后 {r['window_days_after_delivery']} 天，含边界日；窗口外交人工审查。需原因、数量；非质量退货须未使用且完整。",
        "质量问题由商家承担寄回费用；非质量退货由客户自行安排邮资，商家不报价额外标签费。",
        "寄回指引前须有退货授权、地址、包装和邮资说明；商家付费时须有预付标签。",
        f"部分退款上限为受影响份额实付的 {f['partial_offer_max_basis_points'] / 100:g}%（{f['partial_offer_max_basis_points']} 基点），客户须明确接受金额和币种。",
        "全额退款前须有仓库收件和质检记录，数量须覆盖此次受影响份额。例外仅由人工审查。",
        "可退余额扣除已成功退款和处理中、结果未知占用；同一申请与执行记录只扣一次，未知结果先查原操作。",
        "退款回原支付渠道；内部申请不等于退款成功。成功须来自关联执行回执，不承诺固定到账天数。", "",
        "## 换货与补件", "",
        f"质量换货和售后补件窗口为签收后 {replacement['defect_window_days_after_delivery']} 天；售后补件为 {spare['defect_window_days_after_delivery']} 天。",
        "换货默认原准确 SKU；需库存、当前地址确认、寄回收件与质检，不先发后退。替代型号须明确选择、核对兼容后交人工。",
        "补件须准确部件与 SKU、地区和硬件版本适配、数量、库存、客户选择及当前地址确认。安全关键部件交人工。",
        "购买备用件不表示免费售后资格。同订单行同份额的退款、换货和补件跨事项核对，不能换事项编号重复补偿。", "",
        "## 物流与人工审查", "",
        f"轨迹超过 {logistics['stale_tracking_days']} 天未更新可进入查件；显示签收但未收到先核对包裹，不保证到达日期。",
        "建标签不等于发货；查无记录、当时不可用、查询失败和未知结果分开显示。",
        "安全风险、规则冲突、未知兼容、反复失败或例外诉求交人工；人审中业务事件只记录，人工回复后的下一封客户来信才恢复。结案由人工确认。", "",
        "## 每项条件的证据要求", "",
        "图片可支持规则明确允许的客户申报或可见外观条件；订单、金额、选择、兼容和履约仍须各自核验。v1 无映射时不将视觉观察升级为工具事实。", "",
        "| 条件 | 允许来源 kind | 核验要求 | 缺失处理 |", "|---|---|---|---|"]
    for code, value in policy["evidence_requirements"].items():
        lines.append(f"| {value['label']}（{code}） | {', '.join(value['allowed_kinds'])} | {value['verification']} | {value['on_missing']} |")
    return ("\n".join(lines) + "\n").encode("utf-8")


def artifacts():
    policy = json.loads((ROOT / "authoring/policy-profile.json").read_text(encoding="utf-8"))
    previous_root = ROOT.parent / "v1"
    previous = json.loads((previous_root / "authoring/policy-profile.json").read_text(encoding="utf-8"))
    validate(policy, previous)
    rules, readable = json_bytes(policy), render(policy)
    bundle = {"bundle_id": "SIM-POLICY-BUNDLE-V2-2.0.0", "schema_version": SCHEMA_VERSION,
        "interpreter_version": "deterministic-eligibility/1.0", "generator_version": GENERATOR_VERSION,
        "generator_sha256": digest(Path(__file__).read_bytes()), "policy_id": policy["policy_id"],
        "version": policy["version"], "publication_status": "unpublished", "content_review_status": "pending",
        "scope": {k: policy[k] for k in ("allowed_modes", "brands", "markets", "channels", "currencies")},
        "usage_split": ["dev"], "effective_at": policy["effective_at"], "supersedes": policy["supersedes"],
        "rules": {"path": "policies/policy-profile.json", "sha256": digest(rules)},
        "readable": {"path": "policies/policy-profile.md", "version": policy["version"], "sha256": digest(readable)},
        "authoring_sha256": digest((ROOT / "authoring/policy-profile.json").read_bytes()),
        "v1_reference": {"policy_id": previous["policy_id"], "version": previous["version"],
            "path": "../v1", "files": {path: digest((previous_root / path).read_bytes()) for path in
                ("authoring/policy-profile.json", "policies/policy-profile.json", "policies/policy-profile.md")}},
        "schema": rule_schema(), "schema_sha256": digest(json_bytes(rule_schema()))}
    return {"policies/policy-profile.json": rules, "policies/policy-profile.md": readable,
            "policy-bundle.json": json_bytes(bundle)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify generated bytes without writing")
    args = parser.parse_args()
    outputs = artifacts()
    for name, content in outputs.items():
        path = ROOT / name
        if args.check:
            if not path.is_file() or path.read_bytes() != content:
                raise SystemExit("generated_artifact_mismatch:" + name)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    print(json.dumps({"status": "verified" if args.check else "generated", "publication_status": "unpublished",
        "artifacts": {name: digest(content) for name, content in outputs.items()}}, ensure_ascii=False))


if __name__ == "__main__":
    main()
