"""Independent production-normalized inputs; no database/provider access."""
import json
from globalmail_agent.knowledge.json_structure import validate_knowledge_structure
from globalmail_agent.knowledge.parser_contract import ParserBlock
from globalmail_agent.knowledge.chunking import chunks, proxy_tokens
from globalmail_agent.knowledge.index_profiles import chunker
from globalmail_agent.knowledge.commands import Applicability
from globalmail_agent.knowledge.validation import validate_bindings

A, B = "H-CTD16-US-BK", "H-CTD16-US-SGY"
def run(content, bindings):
    raw = json.dumps({"schema_version": "globalmail.knowledge/1",
        "document_type": "troubleshooting_md", "blocks": content}).encode()
    normalized = validate_knowledge_structure(raw, "json")
    values = []
    for value in normalized["blocks"]:
        parsed = ParserBlock.model_validate(value).model_dump()
        values.append({"block_key": parsed["id"], "section_id": parsed["section_id"],
            "page": parsed["page"], "text": parsed["text"], "structure": {k: parsed[k]
                for k in ("type", "bbox", "figure_id", "table_rows", "asset_ids")}})
    applies = [Applicability(**value).model_dump() for value in bindings]
    validate_bindings(applies, "OUTON", None)
    return chunks("独立排障核对", values, applies, set(), chunker("structure_v1_500"))

warning = "Warning:\nKeep hands dry.\nDisconnect the supply before these steps."
shared = run([{"section_id": "safety", "type": "paragraph", "text": warning},
    *[{"section_id": "operation", "type": "paragraph", "text": f"Step {i}: " + "b" * 350}
        for i in range(8)]], [
    {"section_id": "safety", "sku": A, "basis": "A独有前提"},
    {"section_id": "operation", "sku": A, "basis": "A明确操作"},
    {"section_id": "operation", "sku": B, "basis": "B共享操作"}])
operations = [p for p in shared if p["section_id"] == "operation"]
for parent in operations:
    skus = {a["sku"] for a in parent["applicability"]}
    assert len(skus) == 1
    assert (warning in parent["text"]) == (A in skus)
    assert all((warning in c["input_text"]) == (A in skus) for c in parent["children"])
    assert parent["proxy_tokens"] <= 2000
    assert all(proxy_tokens(c["input_text"]) <= 1000 for c in parent["children"])
    assert all(a["basis"] in {"A独有前提", "A明确操作"} for a in parent["applicability"]) if A in skus else all(a["basis"] == "B共享操作" for a in parent["applicability"])

heading = run([{"section_id": "precautions", "type": "heading", "text": "安全前提"},
    {"section_id": "precautions", "type": "paragraph", "text": "Keep hands dry. Wear protective gloves."},
    *[{"section_id": "operation", "type": "paragraph", "text": f"Step {i}: " + "x" * 350}
        for i in range(8)]], [
    {"section_id": "precautions", "sku": A, "basis": "标题涵盖的安全前提"},
    {"section_id": "operation", "sku": A, "basis": "独立操作依据"}])
for parent in [p for p in heading if p["section_id"] == "operation"]:
    assert "Wear protective gloves." in parent["text"]
    assert all("Wear protective gloves." in c["input_text"] for c in parent["children"])
    assert {l["section"] for l in parent["locations"]} == {"precautions", "operation"}

short = run([{"section_id": "prerequisites", "type": "paragraph", "text": warning},
    {"section_id": "operation", "type": "paragraph", "text": "1. Inspect the controller.\n2. Replace only the declared battery."},
    {"section_id": "stops", "type": "paragraph", "text": "Stop if damaged. Escalate to review."}], [
    {"section_id": s, "sku": A, "basis": "依据" + s} for s in ("prerequisites", "operation", "stops")])
assert len(short) == 1 and len(short[0]["children"]) == 1
assert len(short[0]["applicability"]) == 3
assert {l["section"] for l in short[0]["locations"]} == {"prerequisites", "operation", "stops"}
assert all(phrase in short[0]["text"] for phrase in (warning, "Replace only", "Stop if damaged"))
assert short[0]["proxy_tokens"] <= 2000
assert proxy_tokens(short[0]["children"][0]["input_text"]) <= 2500
late_warning = "Stop if a burning smell appears. Disconnect power and escalate. Applies to every step above."
late = run([*[{'section_id': 'operation', 'type': 'paragraph', 'text': f'Step {i}: ' + 'c' * 350}
             for i in range(8)],
    {'section_id': 'late', 'type': 'heading', 'text': '停止条件'},
    {'section_id': 'late', 'type': 'paragraph', 'text': late_warning}], [
    {'section_id': 'operation', 'sku': A, 'basis': 'A共享操作'},
    {'section_id': 'operation', 'sku': B, 'basis': 'B共享操作'},
    {'section_id': 'late', 'sku': A, 'basis': '只有A具备后置条件资格'}])
for parent in [p for p in late if p['section_id'] == 'operation']:
    skus = {a['sku'] for a in parent['applicability']}
    assert len(skus) == 1
    assert (late_warning in parent['text']) == (A in skus)
    assert all((late_warning in c['input_text']) == (A in skus) for c in parent['children'])
    assert parent['proxy_tokens'] <= 2000
    assert all(proxy_tokens(c['input_text']) <= 1000 for c in parent['children'])
print(json.dumps({"result": "PASS", "shared_operation_parent_count": len(operations),
    "a_only_warning_all_inputs": True, "b_no_a_warning_all_inputs": True,
    "full_warning_paragraph_preserved": True, "heading_scope_text_preserved": True,
    "short_same_sku_different_bindings_complete": True, "all_limits_verified": True,
    "late_a_only_condition_all_inputs": True, "late_b_no_a_condition": True, "late_parents": late,
    "shared_parents": shared, "heading_parents": heading, "short_parents": short}, ensure_ascii=False, indent=2))
