"""Actual local parser, qualified whole guide, stopping conditions after long steps."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from globalmail_agent.knowledge.parser_process import parse_bytes
from globalmail_agent.knowledge.chunking import chunks
from globalmail_agent.knowledge.index_profiles import chunker
from globalmail_agent.knowledge.commands import Applicability
from globalmail_agent.knowledge.validation import validate_bindings

stop = '出现焦味时立即停止操作，断电并交人工。此停止条件适用于上述所有检查步骤。'
source = {'schema_version': 'globalmail.knowledge/1', 'document_type': 'troubleshooting_md', 'blocks': [
    {'section_id': 'operation', 'type': 'heading', 'text': '完整检查步骤'},
    *[{'section_id': 'operation', 'type': 'paragraph', 'text': f'Step {i}: ' + 'a' * 350} for i in range(9)],
    {'section_id': 'stops', 'type': 'heading', 'text': '停止条件'},
    {'section_id': 'stops', 'type': 'paragraph', 'text': stop}]}
bindings = [Applicability(section_id=s, sku='H-CTD16-US-BK', basis='自编整份指南相同SKU范围').model_dump()
            for s in ('operation', 'stops')]
validate_bindings(bindings, 'OUTON', None)
with TemporaryDirectory(prefix='review_closed_stop_') as temp:
    parsed = parse_bytes(json.dumps(source, ensure_ascii=False).encode(), 'json', 'markdown', Path(temp), lambda: True)
blocks = [{'block_key': b.id, 'section_id': b.section_id, 'page': b.page, 'text': b.text, 'type': b.type,
           'structure': {k: getattr(b, k) for k in ('bbox', 'figure_id', 'table_rows', 'asset_ids')}} for b in parsed.blocks]
parents = chunks('独立长排障停止条件反例', blocks, bindings, set(), chunker('structure_v1_500'))
operations = [p for p in parents if p['section_id'] == 'operation']
print(json.dumps({'source': source, 'parser_versions': parsed.parser_versions, 'diagnostics': [d.model_dump() for d in parsed.diagnostics],
                  'operation_parent_count': len(operations),
                  'operation_parents_have_required_stop': [stop in p['text'] for p in operations],
                  'operation_inputs_have_required_stop': [stop in c['input_text'] for p in operations for c in p['children']],
                  'parents': parents}, ensure_ascii=False, indent=2))
