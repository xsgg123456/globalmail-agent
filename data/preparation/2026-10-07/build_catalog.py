"""从本次只读生产目录生成候选清单；不连接生产、不生成知识正文。"""
import hashlib
import json
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SOURCE = HERE / "production-catalog.json"
data = json.loads(SOURCE.read_text(encoding="utf-8"))
assert data["transaction_read_only"] == "on"
assert data["transaction_isolation"] == "repeatable read"

definitions = [
    ("OUTON-01", "OUTON", "四按键朝天灯", "H-CTD16-", ["朝天灯"], "高频登记，兼有不同地区规格；优先整理使用、排障与补件原型"),
    ("OUTON-02", "OUTON", "带托盘三脚架灯", "H-SJJ0001-", ["三脚架"], "多地区规格、已有多轮候选及视频题名线索"),
    ("OUTON-03", "OUTON", "滑条遥控喇叭子母灯", "H-LBD05-", ["喇叭子母灯", "子母灯"], "支持遥控、使用指导及部件区分原型；视频版本仍需核对"),
    ("OUTONLIFE-01", "OUTONLIFE", "树形带灯书架", "F-SJ001-", [], "该品牌较集中且可关联会话的产品族，需自编适用知识"),
    ("OUTONLIFE-02", "OUTONLIFE", "ZZZ-02 杂志桌灯", "F-ZZZ0002-", [], "有美规/英规及结构变体，适合验证同系列不同规格不可混用"),
    ("BELEEV-01", "BELEEV", "A2 三轮滑板车", "SP-SLHBC01-", ["A2"], "产品名称与视频题名均有 A2 线索，补件/调节步骤待内容核对"),
    ("BELEEV-02", "BELEEV", "V2 带灯小两轮滑板车", "SP-XLLHBC02-", ["V2"], "登记频次和资料目录较充分，有多轮会话候选"),
    ("BELEEV-03", "BELEEV", "A9 带灯折叠三轮滑板车", "SP-SLHBC12-", ["A9"], "有已关联会话及灯带视频题名，适合部件与后续跟进原型"),
]
families = []
for family_id, brand, name, prefix, title_terms, reason in definitions:
    products = [p for p in data["products"] if p["brand"] == brand and p["sku"].startswith(prefix)]
    assert products, family_id
    videos = [v for v in data["videos"] if v["brand"] == brand and any(t.casefold() in v["title"].casefold() for t in title_terms)]
    conversation_ids = sorted({cid for p in products for cid in p["conversation_ids"] or []})
    families.append({
        "family_id": family_id, "brand": brand, "name": name, "selection_reason": reason,
        "selection_status": "project_initial_selection", "grouping_basis": "registered_sku_prefix_and_product_name",
        "sku_prefix": prefix, "skus": [p["sku"] for p in products],
        "product_names": sorted({name for p in products for name in p["product_names"] or []}),
        "sites": sorted({site for p in products for site in p["sites"] or []}),
        "registration_count": sum(p["registration_count"] for p in products),
        "reviewed_registration_count": sum(p["reviewed_registration_count"] for p in products),
        "conversation_ids": conversation_ids,
        "video_candidate_ids": [v["source_file_id"] for v in videos],
        "video_mapping_status": "title_candidate_only_not_compatibility_evidence",
        "missing": ["SKU/地区/结构变体与视频内容的适用核对", "知识正文与步骤依据", "配件兼容及库存的模拟数据", "多轮正文复核与用途分组"],
    })

products_by_key = {(p["brand"], p["sku"]): p for p in data["products"]}
cases = []
for raw in data["case_candidates"]:
    c = dict(raw)
    names = sorted({name for sku in (c["registration_skus"] or []) for name in products_by_key.get((c["brand"], sku), {}).get("product_names", [])})
    c["registered_product_names"] = names
    c["selected_family_ids"] = [f["family_id"] for f in families if f["brand"] == c["brand"] and set(f["skus"]) & set(c["registration_skus"] or [])]
    if c["brand"] == "BELEEV" and names and not any("滑板车" in n for n in names):
        c["scope_status"] = "excluded_non_scooter_product"
    elif c["brand"] in ("OUTON", "OUTONLIFE") and names and not any("灯" in n or "发光" in n for n in names):
        c["scope_status"] = "needs_product_scope_review"
    elif not names:
        c["scope_status"] = "needs_product_identity_review"
    else:
        c["scope_status"] = "target_product_candidate"
    c["usage_split"] = "unassigned_do_not_index"
    c["body_reviewed"] = False
    c["outcome_verified"] = False
    cases.append(c)

assert len({c["conversation_id"] for c in cases}) == len(cases)
assert len({f["family_id"] for f in families}) == 8
assert set(f["brand"] for f in families) == {"OUTON", "OUTONLIFE", "BELEEV"}
assert all(2 <= sum(x["brand"] == b for x in families) <= 3 for b in {"OUTON", "OUTONLIFE", "BELEEV"})
assert all(c["usage_split"] == "unassigned_do_not_index" for c in cases)

def save(name, value):
    (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

save("selected-product-families.json", families)
save("case-review-queue.json", cases)
save("video-directory.json", data["videos"])
source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
scope_counts = Counter(c["scope_status"] for c in cases)
summary = {
    "observed_at_beijing": data["observed_at_beijing"], "source_sha256": source_hash,
    "selected_families": len(families), "selected_skus": sum(len(f["skus"]) for f in families),
    "selected_family_registrations": sum(f["registration_count"] for f in families),
    "candidate_cases": len(cases), "case_scope_counts": dict(scope_counts),
    "first_contact_multiturn_candidates": sum(c["complete_history_candidate"] for c in cases),
    "selected_family_case_candidates": sum(bool(c["selected_family_ids"]) for c in cases),
    "video_counts": dict(Counter(v["brand"] for v in data["videos"])),
    "knowledge_bodies_created": 0, "case_bodies_exported": 0, "rag_index_created": False,
}
save("catalog-summary.json", summary)

lines = [
    "# 三品牌产品、案例与资料候选目录", "",
    "版本：v1.0；日期：2026-10-07；对应 Product-Spec v1.6。", "",
    f"生产只读观察时间：{data['observed_at_beijing']}（北京时间），REPEATABLE READ / READ ONLY。源数据摘要：`{source_hash}`。", "",
    "本轮完成目录与取样定位，不制作说明书、知识卡、模拟库存/政策/物流数据或 RAG 索引。目录中的产品族是项目初始选择，视频对应是题名线索，案例类别是关键词候选，均不冒充已确认适用性或业务结果。", "",
    "## 1. 范围与材料含义", "",
    "- 售后登记：首封正文及订单/商品关联；已核对只反映正文和关联核对。", 
    "- 快捷回复：客服常用表达，不是政策、执行凭证或正确答案。",
    "- 视频：客户操作/排障参考链接；本轮未观看内容，未确认 SKU 适配。",
    "- 会话：优先 FIRST_CONFIRMED 且至少 2 次非自动入站、1 次非自动出站；这只是多轮候选筛选，不证明历史完整或问题已解决。",
    "- 单据和结果：后续由模拟业务系统建立，Agent 查询；生产 ERP 能力验证不作为前置。", "",
    "## 2. 初始产品族", "",
    "选择考虑登记频次、关联会话及视频线索；地区、颜色、结构变体保留独立 SKU。SKU 前缀归组只服务取样，不表示部件通用。", "",
    "| 品牌 | 产品族 | SKU 数 | 登记条数 | 关联会话数 | 视频题名候选数 |",
    "|---|---|---:|---:|---:|---:|",
]
for f in families:
    lines.append(f"| {f['brand']} | {f['name']}（`{f['sku_prefix']}…`） | {len(f['skus'])} | {f['registration_count']} | {len(f['conversation_ids'])} | {len(f['video_candidate_ids'])} |")
lines += ["", "OUTONLIFE 当前目录没有本品牌视频；后续自编其知识，不能因同属灯具就套用 OUTON 视频。BELEEV 资料中包含露营车，保留来源目录但排除在本项目滑板车知识范围之外。", "",
    "## 3. 案例候选与筛选限制", "",
    f"原始目录含 {len(data['products'])} 个品牌—SKU 组合、{len(data['videos'])} 条视频、{len(data['quick_reply_catalog'])} 条快捷回复目录。按七类关键词每品牌优先取前三，并补入选定产品族直接关联会话，去重得到 {len(cases)} 个候选；其中 {summary['first_contact_multiturn_candidates']} 个符合首封多轮初筛，{summary['selected_family_case_candidates']} 个关联选定产品族。", "",
    "| 范围检查 | 数量 | 用途 |", "|---|---:|---|",
]
scope_labels = {
    "target_product_candidate": ("登记商品属于灯具/滑板车候选", "正文及结果仍待复核"),
    "excluded_non_scooter_product": ("登记为 BELEEV 非滑板车商品", "排除本项目案例提炼"),
    "needs_product_scope_review": ("登记名称不足以确定灯具范围", "先核对商品范围"),
    "needs_product_identity_review": ("仅有邮箱品牌等身份线索", "不能当已确认品牌/SKU 案例"),
}
for key, count in sorted(scope_counts.items()):
    label, purpose = scope_labels[key]
    lines.append(f"| {label} | {count} | {purpose} |")
lines += ["", "以下数量是生产候选池的关键词命中数，允许重复，也可能包含引用、否定、跨类用词及范围外商品；不能作为真实业务分布、七类覆盖验收或成功率。退款/退货较少的品牌直接补模拟场景，不为凑数误标历史。", "",
    "| 业务 | OUTON | OUTONLIFE | BELEEV |", "|---|---:|---:|---:|",
]
biz_names = {"BIZ-01":"产品咨询","BIZ-02":"故障排查","BIZ-03":"物流查询","BIZ-04":"退款","BIZ-05":"退货","BIZ-06":"换货","BIZ-07":"补寄配件"}
for biz, name in biz_names.items():
    counts = [next((x["keyword_candidate_count"] for x in data["coverage"] if x["category"] == biz and x["brand"] == b), 0) for b in ("OUTON","OUTONLIFE","BELEEV")]
    lines.append(f"| {name} | {' | '.join(map(str, counts))} |")
lines += ["", "案例队列没有客户身份和正文，因此尚未按同一发信人、关联订单或近重复内容划分 rag/dev/eval。正式正文提炼前完成稳定去标识客户映射和用途分组；当前目录一律 `unassigned_do_not_index`。", "",
    "## 4. 下一步材料清单", "",
    "| 材料 | 已有依据 | 后续补齐 |", "|---|---|---|",
    "| 产品卡、部件卡 | 8 个产品族的真实 SKU/名称/地区线索 | 结构变体、模拟部件编号及兼容关系；明确哪些是项目设定 |",
    "| 操作与排障知识卡 | 视频目录及待复核邮件案例 | 视频能读取时整理实际内容；读不到则只留链接，自编测试步骤单独标记 |",
    "| 多轮案例卡 | 去重后的会话来源 ID 与消息计数 | 受控读取正文、去标识、去引用、标注已尝试步骤与未知结果；先划用途再提炼 |",
    "| 模拟政策 | 七类流程和人工分工已明确 | 按适用品牌/地区/渠道设置规则，不把客服话术当政策；数值由团队拟定 |",
    "| 模拟业务数据 | 真实订单/商品结构可作原型 | 订单 → 内部待办 → 人工模拟执行单 → 物流/退款结果的关联和状态事件 |",
    "| 验收样本 | SCN-001 至 SCN-030 | 正常、缺信息、异常、方案变更和重复事件；三品牌七类都可模拟覆盖 |", "",
    "## 5. 文件与可复核性", "",
    "目录：`data/preparation/2026-10-07/`。", "",
    "- `catalog-query.sql`：只读生产查询，正文仅在数据库内用于关键词匹配，不返回原文。",
    "- `production-catalog.json`：带时间的本轮原始目录，包括产品、视频、快捷回复目录和候选案例元数据。",
    "- `selected-product-families.json`：8 个产品族及来源 SKU、会话和视频候选 ID。",
    "- `case-review-queue.json`：案例来源、范围检查、历史完整性线索及待复核状态。",
    "- `video-directory.json`：45 条启用视频链接；本轮未检查链接可播放性或观看内容。",
    "- `catalog-summary.json`：计数与源文件 SHA-256；`build_catalog.py` 可离线重建派生目录。", "",
    "业务源 ID 为内部回溯用途，目录不作为公开发布素材。若准备包需分享，另行去除内部回溯信息。", "",
]
(ROOT / "DATA-CATALOG.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=True))
