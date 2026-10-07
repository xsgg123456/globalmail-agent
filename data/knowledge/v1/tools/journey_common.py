"""Shared deterministic preparation helpers; no network or Agent execution."""
import copy
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

OUT = Path(__file__).resolve().parents[1]
ROOT = OUT.parents[2]


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows(path):
    return [json.loads(line) for line in path.read_text('utf-8').splitlines() if line.strip()]


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def write_rows(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(''.join(json.dumps(v, ensure_ascii=False) + '\n' for v in values), encoding='utf-8')


def merge(base, patch):
    result = copy.deepcopy(base)
    for key, value in patch.items():
        result[key] = merge(result[key], value) if isinstance(value, dict) and isinstance(result.get(key), dict) else copy.deepcopy(value)
    return result


def replace_tree(value, replacements, strict=False):
    if isinstance(value, dict):
        return {k: replace_tree(v, replacements, strict) for k, v in value.items()}
    if isinstance(value, list):
        return [replace_tree(v, replacements, strict) for v in value]
    if not isinstance(value, str):
        return value
    if value in replacements:
        return copy.deepcopy(replacements[value])
    result = value
    for key in sorted(replacements, key=len, reverse=True):
        result = result.replace(key, str(replacements[key]))
    if strict and re.search(r'\$[a-z_]+', result):
        raise ValueError(f'Unresolved symbol: {result}')
    return result


def prepare(journey, seed):
    jid = journey['journey_id']
    item = replace_tree(copy.deepcopy(seed), {seed['scenario_id']: jid})
    state = {k: copy.deepcopy(item['initial_state'][k]) for k in ['orders', 'conversation', 'address_confirmation']}
    order = state['orders'][0]
    order.update(refunded_minor=0, pending_refund_minor=0)
    order['display_order_number'] = f'999-72{int(jid[-2:]):05d}-8200000'
    for key in ['operations', 'execution_records', 'shipments', 'returns', 'customer_choices', 'attempted_steps', 'tool_overrides']:
        state[key] = []
    for key in ['confirmed_missing_part_id', 'defect_confirmed_in_simulation']:
        state.pop(key, None)
    parts = {r['part_id']: r for r in read(OUT / 'parts.json')}
    compatible = [r['part_id'] for r in read(OUT / 'compatibility.json') if r['sku'] == order['lines'][0]['sku']]
    part = next((p for p in compatible if parts[p]['customer_replaceable']), compatible[0])
    state['inventory'] = [{'item_id': order['lines'][0]['sku'], 'on_hand': 5, 'reserved': 0},
                          {'item_id': part, 'on_hand': 8, 'reserved': 0}]
    amount = order['paid_minor']
    partial = amount * 2000 // 10000
    money = lambda v: f"{order['currency']} {v / 100:.2f}"
    n = int(jid[-2:])
    def tracking(suffix):
        if order['market'] == 'GB':
            return f'AB720{n:04d}{suffix:02d}GB'
        if order['market'] == 'DE':
            return f'003404720000{n:06d}{suffix:02d}'
        return f'94001000000000{n:06d}{suffix:02d}'
    symbols = {
        '$order': order['order_id'], '$line': order['lines'][0]['line_id'],
        '$customer': item['access_scope']['customer_id'], '$issue': item['issue_id'],
        '$sku': order['lines'][0]['sku'], '$part': part, '$amount': amount,
        '$partial': partial, '$currency': order['currency'],
        '$order_number': order['display_order_number'], '$price_text': money(amount),
        '$partial_text': money(partial), '$return': f'SIM-RMA-{jid}',
        '$execution': f'SIM-EX-{jid}', '$parcel': f'SIM-PKG-{jid}',
        '$return_parcel': f'SIM-RET-PKG-{jid}', '$tracking': tracking(1),
        '$return_tracking': tracking(2), '$address': f'SIM-ADDRESS-{jid}',
    }
    state['conversation'].update(processing_owner='agent', status='open', human_reply_sent=False,
                                 resume_on_next_customer_message=False, known_order_ids=[order['order_id']])
    state['address_confirmation'].update(confirmed=False)
    item['initial_state'] = merge(state, replace_tree(journey.get('initial_state_patch', {}), symbols, True))
    item.update(schema_version='journey-1.0', scenario_id=jid, source_kind='authored_business_journey',
                business_categories=[journey['business']], mode='simulation', usage_split='dev',
                provenance={'seed_scenario_id': seed['scenario_id'], 'identity_and_price_basis': 'existing_product_and_price_prototype',
                            'correspondence_and_fulfilment': 'fictional', 'live_connector_allowed': False},
                controller_events_ref=f'controller-events.jsonl#{jid}',
                controller_visibility='external_controller_only_never_agent_context')
    opening = journey['initial_message']
    item['initial_messages'] = [{'message_id': f'SIM-M-{jid}-1', 'direction': 'INBOUND',
        'received_at': item['clock'], 'language': 'en', 'body': replace_tree(opening, symbols, True)}]
    return item, symbols


def event_time(clock, hours):
    return (datetime.fromisoformat(clock) + timedelta(hours=hours)).isoformat()


def walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from walk_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from walk_strings(item)
