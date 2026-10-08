"""Read-only independent valid structured inputs; no database or provider call."""
import json
from globalmail_agent.knowledge.json_structure import validate_knowledge_structure
from globalmail_agent.knowledge.parser_contract import ParserBlock
from globalmail_agent.knowledge.chunking import chunks
from globalmail_agent.knowledge.index_profiles import chunker
from globalmail_agent.knowledge.commands import Applicability
from globalmail_agent.knowledge.validation import validate_bindings

content = [{"section_id": "safety", "type": "paragraph", "text": "Warning: unplug power before performing any following operation. Stop if damaged."},
           *[{"section_id": "operation", "type": "paragraph", "text": f"Step {i}: " + "a" * 350} for i in range(9)]]
raw = json.dumps({"schema_version": "globalmail.knowledge/1", "document_type": "troubleshooting_md", "blocks": content}).encode()
normalized = validate_knowledge_structure(raw, "json")
blocks = []
for value in normalized["blocks"]:
    parsed = ParserBlock.model_validate(value).model_dump()
    blocks.append({"block_key": parsed["id"], "section_id": parsed["section_id"], "page": parsed["page"], "text": parsed["text"],
                   "structure": {k: parsed[k] for k in ("type", "bbox", "figure_id", "table_rows", "asset_ids")}})
bindings = [Applicability(section_id="safety", sku="H-CTD16-US-BK", basis="A型号共同安全前提").model_dump(),
            Applicability(section_id="operation", sku="H-CTD16-US-BK", basis="A型号操作步骤").model_dump()]
validate_bindings(bindings, "OUTON", None)
parents = chunks("A型号排障", blocks, bindings, set(), chunker("structure_v1_500"))
operations = [p for p in parents if p["section_id"] == "operation"]
summary = {"validated_content": True, "validated_bindings": True, "parent_count": len(parents), "operation_parents": len(operations),
           "operation_warning_present": ["unplug power" in p["text"] for p in operations],
           "operation_embedding_warning_present": [["unplug power" in c["input_text"] for c in p["children"]] for p in operations],
           "parents": parents}
print(json.dumps(summary, ensure_ascii=False, indent=2))
