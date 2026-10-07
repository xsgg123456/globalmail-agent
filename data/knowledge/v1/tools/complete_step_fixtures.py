"""Correct incomplete business wording in the original 51 step fixtures."""
import hashlib
from journey_common import OUT, read, rows, write, write_rows


def build():
    policy = read(OUT / 'authoring/policy-profile.json')
    write(OUT / 'policies/policy-profile.json', policy)
    p = OUT / 'policies/policy-profile.md'
    content = p.read_text('utf-8').replace('规则版本：1.0.0', f'规则版本：{policy["version"]}')
    note = '寄回资料应包含退货编号、准确收件地址、包装要求与邮费承担。商家承担邮费时另需有效预付标签；客户自付邮资的退货可以凭完整寄回指引自行寄件，不要求商家提供预付标签。'
    if note not in content:
        content += '\n## 寄回资料\n\n' + note + '\n'
    p.write_text(content, encoding='utf-8')
    write(OUT / 'sources/policy-render.json', {'canonical_sha256': hashlib.sha256((OUT / 'authoring/policy-profile.json').read_bytes()).hexdigest(),
        'readable_sha256': hashlib.sha256(p.read_bytes()).hexdigest(), 'generated_by': 'tools/complete_step_fixtures.py', 'rule_version': policy['version']})
    docs = read(OUT / 'documents.json')
    bindings = read(OUT / 'knowledge-bindings.json')
    for doc in docs:
        if doc['document_type'] == 'policy_md':
            doc.update(version=policy['version'], source_hash=hashlib.sha256(p.read_bytes()).hexdigest())
    for binding in bindings:
        if binding['document_id'] == 'POL-SIM-V1':
            binding['document_version'] = policy['version']
    write(OUT / 'documents.json', docs)
    write(OUT / 'knowledge-bindings.json', bindings)
    inputs = {r['scenario_id']: r for r in rows(OUT / 'scenarios/inputs.jsonl')}
    events = rows(OUT / 'scenarios/controller-events.jsonl')
    assertions = rows(OUT / 'evaluation/scenario-assertions.jsonl')
    for item in assertions:
        if item['scenario_id'] == 'SCN-004':
            item['expected_actions'] = ['retrieve_applicable_reference', 'check_step_evidence_and_revision',
                                        'ask_missing_observation_or_human_review_when_unverified']
            item['forbidden_actions'] = ['invent_pairing_success', 'send_unverified_pairing_sequence']
    addresses = {
        'US': 'Returns Department, 18 Willow Commerce Drive, Columbus, OH 43228, United States',
        'GB': 'Returns Department, Unit 8, Willow Trading Estate, Birmingham B24 9QA, United Kingdom',
        'DE': 'Retourenabteilung, Lagerhalle 4, Lindenweg 18, 90451 Nuernberg, Germany',
        'AU': 'Returns Department, Unit 4, 18 Willow Road, Dandenong VIC 3175, Australia',
    }
    for event in events:
        if event['kind'] != 'return_authorized':
            continue
        order = inputs[event['scenario_id']]['initial_state']['orders'][0]
        reference = 'RT-' + order['display_order_number'].split('-')[1]
        address = addresses[order['market']]
        event['payload'].update(return_reference=reference, return_address=address,
            return_document_status='issued', return_document_source='authored_simulation_only',
            live_shipping_valid=False, postage_arranged_by='customer', prepaid_label_provided=False,
            instructions=f'Your return reference is {reference}. Please pack the unused item with all accessories, '
                f'include a note with your order number and return reference, and send it to: {address}. '
                'For this change-of-mind return, please arrange and pay for tracked postage yourself. '
                'Keep the posting receipt and reply with the carrier and tracking number. '
                'We will confirm receipt and check the contents before arranging your refund. '
                'Please do not send it to the address printed on the original delivery box.')
    write_rows(OUT / 'scenarios/controller-events.jsonl', events)
    write_rows(OUT / 'evaluation/scenario-assertions.jsonl', assertions)
    print('Updated original return instructions and evidence-aware troubleshooting expectations.')


if __name__ == '__main__':
    build()
