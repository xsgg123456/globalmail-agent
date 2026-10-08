"""Independent real-source generator audit; no database or model request."""
import ast
import hashlib
import json
import subprocess
from pathlib import Path

from globalmail_agent.knowledge.policy_bundle import parse_policy, GENERATOR_VERSION, LEGACY_GENERATOR_VERSION
from globalmail_agent.knowledge.parser_profiles import fingerprint

ROOT = Path(__file__).resolve().parents[4]
REL = 'globalmail-agent/backend/src/globalmail_agent/knowledge/policy_bundle.py'
old = subprocess.check_output(['git', 'show', f'd0833a4:{REL}'], cwd=ROOT).decode('utf-8')
current = (ROOT / REL).read_text(encoding='utf-8').replace('\r\n', '\n')
def function_source(text, name):
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name)
    return '\n'.join(text.splitlines()[node.lineno - 1:node.end_lineno])
legacy_same = function_source(old, 'render').replace('def render(', 'def render_legacy(', 1) == function_source(current, 'render_legacy')
assert legacy_same, 'legacy render body changed'
records = []
for variant in ('v1', 'v2'):
    source = ROOT / 'data/knowledge' / variant / 'policies/policy-profile.json'
    raw = source.read_bytes()
    latest, legacy = parse_policy(raw), parse_policy(raw, generator_version=LEGACY_GENERATOR_VERSION)
    text = latest['description']
    facts = {
        'explicit_amount_currency_acceptance': '具体金额和币种，取得明确同意后再提交' in text,
        'asking_silence_not_acceptance': '询问金额、表达不满或没有回复，都不算接受' in text,
        'alternative_choice_compatibility_human': '客户明确选择并完成适配核验，再交人工确认' in text,
        'reconcile_prior_application_execution': '先查询原申请和已执行记录' in text,
        'cancel_and_prior_compensation': '检查补件能否取消以及是否已经产生补偿' in text,
        'receipt_inspection': '退件签收且验货通过' in text,
        'refund_request_not_success': '内部申请不等于成功' in text,
        'postage_responsibility': '由客户安排寄回邮资' in text and '退货标签费用由商家承担' in text,
        'label_not_carrier_receipt': '物流标签不等于承运商已收件' in text,
        'same_rules_schema': latest['rules'] == legacy['rules'] and latest['rule_schema'] == legacy['rule_schema'],
        'new_description_hash': latest['description_sha256'] != legacy['description_sha256'],
        'source_unchanged': raw == source.read_bytes(),
    }
    assert all(facts.values()), facts
    records.append({'variant': variant, 'source': source.relative_to(ROOT).as_posix(),
                    'source_sha256': hashlib.sha256(raw).hexdigest(), 'facts': facts,
                    'current_bundle': latest, 'legacy_bundle': legacy})
print(json.dumps({'legacy_render_source_identical_except_name': legacy_same,
                  'parser_fingerprint_includes_policy_bundle_source': '"policy_bundle.py"' in
                    (ROOT / 'globalmail-agent/backend/src/globalmail_agent/knowledge/parser_profiles.py').read_text(),
                  'policy_fingerprint': fingerprint('policy'), 'generator': GENERATOR_VERSION, 'records': records},
                 ensure_ascii=False, indent=2))
