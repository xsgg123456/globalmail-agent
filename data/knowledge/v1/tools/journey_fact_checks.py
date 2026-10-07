"""Offline causal checks over authored facts and isolated evaluation annotations."""


def fact_checks(inputs, events, assertions, artifacts):
    results = {name: [] for name in [
        'full refunds and replacement follow warehouse inspection',
        'partial refunds follow explicit amount acceptance within policy cap',
        'dispatch uses confirmed current address with customer evidence',
        'fulfilment stock available in authored facts',
        'reissued return document versions remain distinct and attachment resolves',
    ]}
    def check(name, value):
        results[name].append(bool(value))
    aby = {a['event_id']: a for a in assertions}
    artifact_by = {a['artifact_id']: a for a in artifacts}
    for item in inputs:
        sid = item['scenario_id']
        state = item['initial_state']
        order = state['orders'][0]
        paid = order['paid_minor']
        address = state['address_confirmation']
        stock = {x['item_id']: x['on_hand'] - x['reserved'] for x in state['inventory']}
        returns = {r['return_id']: r for r in state['returns']}
        seen = {'initial_message': {'kind': 'customer_message'}}
        choices = []
        execution_addresses = {}
        return_versions = {}
        for e in [e for e in events if e['scenario_id'] == sid]:
            r = e['payload']['record']
            step = aby[e['event_id']]['step_id']
            decision = aby[e['event_id']].get('evaluation_facts', {}).get('customer_acceptance')
            if decision:
                check('partial refunds follow explicit amount acceptance within policy cap', e['kind'] == 'customer_message')
                choices.append(decision)
            if e['kind'] == 'return_update':
                returns[r['return_id']] = r
                if r.get('instruction_artifact_id'):
                    version = r.get('document_version', r.get('label_version', 1))
                    key = (r['return_id'], version)
                    return_versions[key] = r['instruction_artifact_id']
            if e['kind'] == 'address_update':
                source = r.get('source_step')
                check('dispatch uses confirmed current address with customer evidence',
                      r['version'] >= address.get('version', 0) and source in seen and seen[source]['kind'] == 'customer_message')
                address = r
            if e['kind'] == 'inventory_update':
                stock[r['item_id']] = r['on_hand'] - r.get('reserved', 0)
            selector = r.get('operation_selector') or e['gate'].get('operation_required', {})
            kind = r.get('kind') or selector.get('kind')
            if e['kind'] == 'execution_record' and r.get('status') in ['accepted', 'succeeded']:
                passed_return = any(x.get('received') is True and x.get('inspection') == 'passed' and
                    x.get('order_id') == order['order_id'] and x.get('order_line_id', x.get('line_id')) == order['lines'][0]['line_id'] for x in returns.values())
                if kind == 'replacement' or (kind == 'refund' and r.get('amount_minor') == paid):
                    check('full refunds and replacement follow warehouse inspection', passed_return)
                if kind == 'refund' and r.get('amount_minor', paid) < paid:
                    amount = r['amount_minor']
                    check('partial refunds follow explicit amount acceptance within policy cap',
                          0 < amount <= paid * 2000 // 10000 and any(c['kind'] == 'refund' and c['amount_minor'] == amount and c['currency'] == r.get('currency') for c in choices))
                if kind in ['replacement', 'spare_part']:
                    current = r.get('address_version', address.get('version'))
                    check('dispatch uses confirmed current address with customer evidence', address.get('confirmed') is True and current == address.get('version'))
                    execution_addresses[r['execution_id']] = current
                    item_id = r.get('item_id', r.get('part_id')) or (order['lines'][0]['sku'] if kind == 'replacement' else state['inventory'][1]['item_id'])
                    check('fulfilment stock available in authored facts', stock.get(item_id, 0) >= r.get('quantity', 1))
            if e['kind'] == 'shipment_update' and r.get('purpose') in ['replacement', 'spare_part'] and r.get('status') in ['label_created', 'in_transit']:
                version = r.get('address_version', execution_addresses.get(r.get('execution_id')))
                check('dispatch uses confirmed current address with customer evidence', address.get('confirmed') is True and version == address.get('version'))
            if r.get('attachment_artifact_id'):
                artifact = artifact_by.get(r['attachment_artifact_id'])
                check('reissued return document versions remain distinct and attachment resolves', artifact and artifact['scenario_id'] == sid and artifact['document_version'] == r.get('document_version', 1))
            seen[step] = e
        by_return = {}
        for (rid, version), aid in return_versions.items():
            by_return.setdefault(rid, []).append((version, aid))
        for versions in by_return.values():
            check('reissued return document versions remain distinct and attachment resolves', len({a for _, a in versions}) == len(versions))
    return [{'name': n, 'passed': all(values), 'detail': ''} for n, values in results.items()]
