"""Validate prepared timelines, not model decisions or runtime execution."""
import hashlib
import re
from collections import Counter
from datetime import datetime
from journey_common import OUT, read, rows, write, walk_strings
from journey_fact_checks import fact_checks


def inspect(inputs, events, assertions, manifest, artifacts):
    checks = []
    def check(name, ok, details=''):
        checks.append({'name': name, 'passed': bool(ok), 'detail': details})
    ids = {i['scenario_id'] for i in inputs}
    byid = {i['scenario_id']: i for i in inputs}
    eids = {e['event_id'] for e in events}
    check('21 unique continuous journeys', len(inputs) == len(ids) == 21 and ids == {f'JRN-{i:02d}' for i in range(1, 22)})
    check('seven primary journeys and fourteen branches', Counter(m['variant'] for m in manifest) == {'main': 7, 'branch': 14})
    check('three journeys for every business', Counter(m['business'] for m in manifest) == {f'BIZ-{i:02d}': 3 for i in range(1, 8)})
    check('three brands represented', {i['initial_state']['orders'][0]['brand'] for i in inputs} == {'OUTON', 'OUTONLIFE', 'BELEEV'})
    check('all inputs explicitly fictional isolated development data', all(i['mode'] == 'simulation' and i['usage_split'] == 'dev' and i['provenance']['live_connector_allowed'] is False for i in inputs))
    check('all steps have separately stored evaluation entries', len(eids) == len(events) == len(assertions) and eids == {a['event_id'] for a in assertions})
    check('reference replies and expected actions absent from inputs and controller events', all(not re.search(r'"(?:reference_reply|expected_actions|forbidden_actions)"', __import__('json').dumps(x)) for x in inputs + events))
    check('reference replies not preloaded as outbound history', all(all(m['direction'] == 'INBOUND' for m in i['initial_messages']) for i in inputs))
    order_numbers = [o['display_order_number'] for i in inputs for o in i['initial_state']['orders']]
    check('journey order display numbers unique', len(order_numbers) == len(set(order_numbers)))
    check('opening order numbers refer to current journey', all(set(re.findall(r'\b\d{3}-\d{7}-\d{7}\b', i['initial_messages'][0]['body'])) <= {o['display_order_number'] for o in i['initial_state']['orders']} for i in inputs))
    check('evaluation explicitly not run and not indexable', all(a['execution_status'] == 'not_run' and a['usage_split'] == 'dev_assertions_never_index' for a in assertions) and all(not m['indexable'] for m in manifest))
    products = {p['sku']: p for p in read(OUT / 'products.json')}
    compat = {(c['sku'], c['part_id']) for c in read(OUT / 'compatibility.json')}
    chronology, human_close, enough_mail, factual_refs, balances, identity, parts = [], [], [], [], [], [], []
    guarded, refund_ok, shipment_ok, stock_ok, close_evidence, no_premature_human_resume = [], [], [], [], [], []
    for sid in sorted(ids):
        item = byid[sid]
        state = item['initial_state']
        orders = {o['order_id']: o for o in state['orders']}
        order = state['orders'][0]
        sku = order['lines'][0]['sku']
        identity.append(sku in products and order['customer_id'] == item['access_scope']['customer_id'] and set(orders) == set(item['access_scope']['allowed_order_ids']))
        balances.append(order['paid_minor'] == sum(l['paid_minor'] for l in order['lines']) and 0 <= order['refunded_minor'] + order['pending_refund_minor'] <= order['paid_minor'])
        parts.append(all((sku, s['item_id']) in compat for s in state['inventory'] if s['item_id'].startswith('SIM-')))
        steps = [e for e in events if e['scenario_id'] == sid]
        last_time = datetime.fromisoformat(item['clock'])
        prev = None
        for e in steps:
            at = datetime.fromisoformat(e['not_before'])
            chronology.append(at >= last_time and e['requires_event_id'] == prev)
            last_time, prev = at, e['event_id']
        human_close.append(bool(steps) and steps[-1]['kind'] == 'human_close' and steps[-1]['actor'] == 'staff')
        enough_mail.append(sum(e['kind'] == 'customer_message' for e in steps) + len(item['initial_messages']) >= 2)
        prior_records = {}
        successful = {}
        customer_after_human = True
        for e in steps:
            record = e['payload']['record']
            if e['kind'] == 'human_reply':
                customer_after_human = False
            if e['kind'] == 'customer_message':
                customer_after_human = True
            if e['kind'] == 'checkpoint' and not customer_after_human:
                no_premature_human_resume.append(e['gate'].get('record_only_during_human_wait') is True)
            for key in ['order_id']:
                if record.get(key):
                    factual_refs.append(record[key] in orders)
            if record.get('order_line_id'):
                factual_refs.append(record['order_line_id'] in {l['line_id'] for o in orders.values() for l in o['lines']})
            selector = record.get('operation_selector') or e['gate'].get('operation_required')
            if selector:
                factual_refs.append(selector.get('order_id') in orders and selector.get('order_line_id') == order['lines'][0]['line_id'])
            if e['kind'] == 'execution_record':
                guarded.append(bool(selector) and bool(e['gate'].get('operation_required')))
                key = record.get('execution_id')
                refund = record.get('kind') == 'refund' or (selector or {}).get('kind') == 'refund'
                if refund and record.get('status') == 'succeeded':
                    amount = record.get('amount_minor')
                    refund_ok.append(isinstance(amount, int) and 0 < amount <= order['paid_minor'] and record.get('currency') == order['currency'])
                    if key in successful:
                        refund_ok.append(successful[key] == amount)
                    successful[key] = amount if isinstance(amount, int) else 0
                if key:
                    prior_records[key] = record
            if e['kind'] == 'shipment_update':
                shipment_ok.append(bool(record.get('parcel_id')) and bool(record.get('tracking_number')) and bool(record.get('carrier')) and record.get('status') in ['label_created', 'in_transit', 'delivered', 'delivery_exception'])
                if record.get('execution_id'):
                    factual_refs.append(record['execution_id'] in prior_records)
            if e['kind'] == 'inventory_update':
                stock_ok.append(isinstance(record.get('on_hand'), int) and 0 <= record.get('reserved', 0) <= record['on_hand'])
        refund_ok.append(sum(successful.values()) + order['refunded_minor'] <= order['paid_minor'])
        close_evidence.append(any(e['kind'] == 'customer_message' for e in steps[:-1]) and bool(steps[-1]['payload']['text']))
    for name, values in [('chronological dependent events', chronology), ('all journeys end with human closure', human_close),
                         ('all journeys include customer follow-up', enough_mail), ('record order and execution references resolve', factual_refs),
                         ('initial order amounts balanced', balances), ('customer product scope exact', identity), ('initial parts match SKU', parts),
                         ('external execution waits for actual internal request', guarded), ('refund amount currency and total consistent', refund_ok),
                         ('shipment observations have parcel carrier tracking and status', shipment_ok), ('stock quantities valid', stock_ok),
                         ('closure has customer follow-up and human reason', close_evidence), ('no automatic resume immediately after human reply', no_premature_human_resume)]:
        check(name, all(values))
    business_text = [m['body'] for i in inputs for m in i['initial_messages']]
    business_text += [e['payload']['text'] for e in events if e['kind'] in ['customer_message', 'human_reply']]
    business_text += [a['reference_reply'] for a in assertions if a['reference_reply']]
    bad_text = [t for t in business_text if re.search(r'SIM-|BIZ-|SCN-|JRN-|\bHITL\b|\bRAG\b|fixture|pgvector|mock', t, re.I)]
    check('customer facing correspondence contains no test vocabulary', not bad_text, str(bad_text[:2]))
    check('no unresolved authoring symbols', not any(re.search(r'\$[a-z_]+', s) for x in inputs + events + assertions for s in walk_strings(x)))
    check('return instruction files exist and match hashes', bool(artifacts) and all((OUT/a['path']).is_file() and hashlib.sha256((OUT/a['path']).read_bytes()).hexdigest() == a['sha256'] and not a['indexable'] and not a['live_shipping_valid'] for a in artifacts))
    check('all controller events are external only', all(e['agent_can_create'] is False for e in events))
    return checks + fact_checks(inputs, events, assertions, artifacts)


def main():
    inputs = rows(OUT / 'scenarios/journeys/inputs.jsonl')
    events = rows(OUT / 'scenarios/journeys/controller-events.jsonl')
    assertions = rows(OUT / 'evaluation/journey-assertions.jsonl')
    manifest = read(OUT / 'scenarios/journeys/manifest.json')
    artifacts = read(OUT / 'scenarios/journeys/artifacts.json')
    checks = inspect(inputs, events, assertions, manifest, artifacts)
    counts = {'journeys': len(inputs), 'main_journeys': sum(m['variant'] == 'main' for m in manifest),
              'branch_journeys': sum(m['variant'] == 'branch' for m in manifest), 'timeline_steps': len(events),
              'customer_messages': sum(len(i['initial_messages']) for i in inputs) + sum(e['kind'] == 'customer_message' for e in events),
              'reference_replies': sum(bool(a['reference_reply']) for a in assertions), 'return_documents': len(artifacts),
              'original_step_scenarios': 51, 'total_scenario_inputs': 51 + len(inputs)}
    report = {'validation_kind': 'offline_prepared_data_consistency_not_runtime', 'passed': all(c['passed'] for c in checks),
              'checks': checks, 'counts': counts, 'not_run': ['Agent execution', 'RAG retrieval', 'business state machine execution', 'production actions']}
    write(OUT / 'journey-validation-report.json', report)
    print(__import__('json').dumps({'passed': report['passed'], 'checks': len(checks), 'counts': counts}, ensure_ascii=False))
    for check in checks:
        if not check['passed']:
            print('FAIL', check['name'], check['detail'])
    if not report['passed']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
