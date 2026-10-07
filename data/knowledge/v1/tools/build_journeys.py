"""Build isolated long-form customer journeys and human-readable review cards."""
import hashlib
import html
import json
from journey_common import OUT, read, rows, write, write_rows, prepare, replace_tree, event_time

AUTHORS = ['support-journeys.json', 'commerce-journeys.json']
BUSINESS = dict(zip([f'BIZ-{i:02d}' for i in range(1, 8)], ['产品咨询', '故障排查', '物流查询', '退款', '退货', '换货', '补寄配件']))
ACTORS = {'customer': '客户', 'agent_checkpoint': 'Agent 应判断', 'staff': '客服', 'warehouse': '仓库', 'carrier': '承运商', 'payment': '支付处理'}


def runtime_guards(step, item):
    """Declarative requirements for the future loader, not evaluated model claims."""
    gate = step['gate']
    record = step.get('record', {})
    selector = gate.get('operation_required') or record.get('operation_selector')
    gate['scope'] = {'branch_id': item['branch_id'], 'customer_id': item['access_scope']['customer_id']}
    if selector and step['kind'] == 'execution_record':
        gate['operation_required'] = selector
    guards = ['previous_step_committed', 'event_not_already_applied', 'record_scope_matches_branch']
    if step['kind'] == 'checkpoint':
        guards += ['actual_agent_run_completed', 'checkpoint_conditions_verified_by_controller', 'no_reference_reply_injection']
    if selector:
        guards += ['actual_internal_request_exists', 'result_matches_original_request', 'legal_execution_status_transition']
        if record.get('status') == 'cancelled':
            guards += ['cancellation_requested', 'no_dispatch_confirmed', 'release_original_reservations']
            gate['required_business_checks'] = guards
            return step
        if selector['kind'] == 'refund':
            guards += ['authorized_refund_amount_and_currency_match', 'no_duplicate_refund_result']
            if record.get('status') == 'accepted':
                guards += ['refund_balance_available', 'return_inspection_or_recorded_exception_for_full_refund',
                           'explicit_amount_acceptance_for_partial_refund']
        elif selector['kind'] in ['replacement', 'spare_part']:
            guards += ['exact_item_compatible']
            if record.get('status') == 'accepted':
                guards += ['customer_choice_valid', 'confirmed_current_address_version', 'stock_available_before_dispatch']
            if selector['kind'] == 'replacement' and record.get('status') == 'accepted':
                guards += ['return_inspection_or_recorded_exception_before_dispatch']
    if step['kind'] == 'human_close':
        guards += ['staff_identity_required', 'resolution_reason_recorded']
    gate['required_business_checks'] = guards
    return step


def return_artifact(jid, step, record, cache):
    """A local readable shipping-reference sample, never a live carrier label."""
    if not record.get('instructions') and not record.get('label_artifact_id'):
        return None
    record.setdefault('return_reference', f'RT-720{int(jid[-2:]):04d}')
    version = record.get('document_version', record.get('label_version', 1))
    fields = {k: v for k, v in record.items() if k in {
        'instructions', 'return_reference', 'return_address', 'warehouse_address', 'address',
        'recipient', 'postage_payer', 'postage_arranged_by', 'carrier', 'expires_at', 'label_status', 'tracking_number'}}
    fields['document_version'] = version
    fingerprint = json.dumps(fields, ensure_ascii=False, sort_keys=True)
    if fingerprint in cache:
        record['instruction_artifact_path'] = cache[fingerprint]['path']
        record['instruction_artifact_id'] = cache[fingerprint]['artifact_id']
        record['artifact_scope'] = 'local_simulation_only_not_a_live_carrier_label'
        return None
    relative = f'scenarios/journeys/return-documents/{jid}-{step["id"]}.html'
    artifact_id = f'{jid}-return-document-v{version}-{step["id"]}'
    cache[fingerprint] = {'path': relative, 'artifact_id': artifact_id}
    path = OUT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    labels = {'instructions': 'Packing and return instructions', 'return_id': 'Return reference', 'return_reference': 'Return reference',
              'return_address': 'Return address', 'warehouse_address': 'Return address', 'recipient': 'Recipient',
              'postage_payer': 'Postage paid by', 'postage_arranged_by': 'Postage arranged by', 'carrier': 'Carrier',
              'expires_at': 'Valid until', 'label_status': 'Document status', 'tracking_number': 'Return tracking',
              'fee_payer': 'Postage paid by', 'quantity': 'Quantity', 'packing': 'Packing', 'handoff': 'Handing over the parcel', 'deadline': 'Please return by',
              'document_version': 'Document version', 'line1': 'Street address', 'line2': 'Building / unit', 'postal_code': 'Postal code'}
    def render(key, value):
        if isinstance(value, dict):
            return ''.join(render(k, v) for k, v in value.items() if k not in ['label_reference', 'source_kind'])
        if isinstance(value, list):
            value = '\n'.join(str(v) for v in value)
        if key == 'return_id':
            value = f'RT-720{int(jid[-2:]):04d}'
        if value in ['merchant', 'customer']:
            value = {'merchant': 'Our support team', 'customer': 'Customer'}[value]
        return f'<dt>{html.escape(labels.get(key, key.replace("_", " ").capitalize()))}</dt><dd>{html.escape(str(value))}</dd>'
    body = ''.join(render(k, v) for k, v in fields.items())
    path.write_text('<!doctype html><html lang="zh"><meta charset="utf-8"><title>退货寄件资料</title>'
        '<style>body{max-width:760px;margin:40px auto;font:16px/1.7 sans-serif;color:#222}dt{font-weight:bold;margin-top:16px}'
        'dd{margin:0;white-space:pre-wrap}.notice{padding:12px;background:#fff0cc}</style>'
        '<p class="notice">售后流程演练资料。地址、退货编号和运单均为虚构，不可实际寄件；本页不是承运商可扫描面单。</p>'
        f'<h1>Return instructions</h1><dl>{body}</dl></html>', encoding='utf-8')
    record['instruction_artifact_path'] = relative
    record['instruction_artifact_id'] = artifact_id
    record['artifact_scope'] = 'local_simulation_only_not_a_live_carrier_label'
    return {'path': relative, 'artifact_id': artifact_id, 'document_version': version, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'scenario_id': jid,
            'available_after_step': step['id'], 'purpose': 'customer_return_instructions', 'indexable': False,
            'live_shipping_valid': False}


def build():
    old_artifacts = read(OUT / 'scenarios/journeys/artifacts.json') if (OUT / 'scenarios/journeys/artifacts.json').exists() else []
    seeds = {s['scenario_id']: s for s in rows(OUT / 'scenarios/inputs.jsonl')}
    authors = [j for name in AUTHORS for j in read(OUT / 'authoring' / name)]
    authors.sort(key=lambda j: j['journey_id'])
    inputs, events, assertions, manifest, artifacts = [], [], [], [], []
    summary = ['# 连续售后流程资料', '', '以下客户、往来及履约记录均为围绕现有商品编写的虚构业务故事，仅在隔离环境演练。',
               '客服参考回复供审阅，不会当成 Agent 已发送邮件；后续结果由外部事件按顺序提供。', '',
               '| 编号 | 业务 | 场景 | 类型 |', '|---|---|---|---|']
    for j in authors:
        item, symbols = prepare(j, seeds[j['seed_scenario_id']])
        item['policy_profile_version'] = read(OUT / 'policies/policy-profile.json')['version']
        jid = j['journey_id']
        inputs.append(item)
        opening = item['initial_messages'][0]['body']
        card = [f'# {j["title"]}', '', '编写的业务演练案例，不是真实客户历史；商品与金额沿用已有原型。', '',
                f'业务：{BUSINESS[j["business"]]}；订单：{symbols["$order_number"]}；商品：{symbols["$sku"]}；实付：{symbols["$price_text"]}。', '',
                f'资料依据与边界：{j["knowledge_note"]}', '', '## 首封来信', '', opening, '', '## 后续往来与处理', '']
        prev = 'initial_message'
        artifact_cache = {}
        artifact_aliases = {}
        for num, source_step in enumerate(j['steps'], 1):
            step = replace_tree(source_step, symbols, True)
            step = runtime_guards(step, item)
            eid = f'{jid}-{step["id"]}'
            gate = step['gate']
            if gate.get('after_step') != prev:
                raise ValueError(f'{eid}: gate must follow previous step {prev}')
            record = step.get('record', {})
            if record:
                record.setdefault('source_kind', 'authored_simulation_record')
            logical_artifact_alias = record.get('label_artifact_id', 'return-label')
            artifact = return_artifact(jid, step, record, artifact_cache)
            if artifact:
                artifacts.append(artifact)
            if record.get('instruction_artifact_id'):
                artifact_aliases[logical_artifact_alias] = {
                    'artifact_id': record['instruction_artifact_id'], 'path': record['instruction_artifact_path']}
                if record.get('label_artifact_id'):
                    record['label_artifact_id'] = record['instruction_artifact_id']
                if record.get('prepaid_postage_record'):
                    record['prepaid_postage_record']['artifact_id'] = record['instruction_artifact_id']
            for field in ['attachment_artifact_id']:
                if record.get(field):
                    alias = artifact_aliases[record[field]]
                    record[field] = alias['artifact_id']
                    record['attachment_path'] = alias['path']
            payload = {'text': step['text'], 'record': record}
            if step['kind'] == 'customer_message':
                payload.update(message_id=f'SIM-M-{jid}-{step["id"]}', direction='INBOUND', language='en', body=step['text'])
            if step['kind'] == 'human_reply':
                payload['resume_on_next_customer_message'] = True
            events.append({'event_id': eid, 'sequence': num, 'scenario_id': jid, 'source_kind': 'authored_business_journey',
                'actor': step['actor'], 'kind': step['kind'], 'not_before': event_time(item['clock'], step['after_hours']),
                'requires_event_id': f'{jid}-{prev}' if prev != 'initial_message' else None,
                'gate': gate, 'payload': payload, 'agent_can_create': False,
                'delivery_semantics': 'checkpoint_barrier_no_prefilled_agent_output' if step['kind'] == 'checkpoint' else 'external_fact_after_gate'})
            assertions.append({'scenario_id': jid, 'step_id': step['id'], 'event_id': eid,
                'expected_actions': step.get('expected_actions', []), 'forbidden_actions': step.get('forbidden_actions', []),
                'reference_reply': step.get('reference_reply', ''), 'reference_reply_semantics': 'example_not_exact_match_not_sent',
                'evaluation_facts': step.get('evaluation_facts', {}),
                'usage_split': 'dev_assertions_never_index', 'execution_status': 'not_run'})
            card += [f'### 第 {num} 步 · {ACTORS[step["actor"]]} · 来信后 {step["after_hours"]} 小时', '', step['text'], '']
            if step.get('reference_reply'):
                card += ['客服参考回复：', '', step['reference_reply'], '']
            if step.get('expected_actions'):
                card += ['这一轮应处理：' + '；'.join(step['expected_actions']) + '。', '']
            prev = step['id']
        card += ['## 处理结果', '', j['outcome'], '', '## 本例覆盖', '', '、'.join(j['tags']), '']
        path = OUT / f'scenarios/journeys/readable/{jid}.md'
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(card), encoding='utf-8')
        summary.append(f'| [{jid}](readable/{jid}.md) | {BUSINESS[j["business"]]} | {j["title"]} | {"主流程" if j["variant"] == "main" else "分支"} |')
        manifest.append({'scenario_id': jid, 'title': j['title'], 'business': j['business'], 'variant': j['variant'],
                         'seed_scenario_id': j['seed_scenario_id'], 'tags': j['tags'], 'step_count': len(j['steps']),
                         'outcome': j['outcome'], 'indexable': False, 'execution_status': 'not_run'})
    write_rows(OUT / 'scenarios/journeys/inputs.jsonl', inputs)
    write_rows(OUT / 'scenarios/journeys/controller-events.jsonl', events)
    write_rows(OUT / 'evaluation/journey-assertions.jsonl', assertions)
    write(OUT / 'scenarios/journeys/manifest.json', manifest)
    write(OUT / 'scenarios/journeys/artifacts.json', artifacts)
    current_paths = {a['path'] for a in artifacts}
    artifact_root = (OUT / 'scenarios/journeys/return-documents').resolve()
    for old in old_artifacts:
        target = (OUT / old['path']).resolve()
        if old['path'] not in current_paths and target.parent == artifact_root and target.suffix == '.html':
            target.unlink(missing_ok=True)
    summary += ['', f'共 {len(inputs)} 条连续流程，{len(events)} 个后续步骤，{len(artifacts)} 份寄回资料。原 51 个环节样例另行保留。', '',
                '所有流程尚未运行 Agent。主流程完成指数据中已描述到人工结案，不表示系统已经通过功能验收。', '',
                '运行数据见 inputs.jsonl；未来事件见 controller-events.jsonl；参考回复与预期动作仅在 evaluation/journey-assertions.jsonl。',
                '不要把本目录可读案例、编辑源或未来事件导入 RAG。']
    (OUT / 'scenarios/journeys/README.md').write_text('\n'.join(summary) + '\n', encoding='utf-8')
    print(f'Prepared {len(inputs)} journeys, {len(events)} steps, {len(artifacts)} return documents; Agent not run.')


if __name__ == '__main__':
    build()
