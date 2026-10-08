"""Independently recalculate frozen labels against complete actual returned text."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
HERE = ROOT / 'globalmail-agent/knowledge-eval'
paths = [ROOT / 'globalmail-agent/knowledge-spike/retrieval-queries.jsonl', HERE / 'extra-queries.jsonl']
freeze = json.loads((HERE / 'query-freeze.json').read_text(encoding='utf-8'))['snapshot']
snapshot = {p.name: {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                     'count': len(p.read_text(encoding='utf-8').splitlines())} for p in paths}
labels = {q['query_id']: q for p in paths for line in p.read_text(encoding='utf-8').splitlines()
          for q in [json.loads(line)]}


def normalized(value):
    return ''.join(value.split()).casefold()


def proxy(value):
    return sum(1 if ord(char) < 128 else 2 for char in value)


audits = {}
for name in ('retrieval-results-policy-1.0.json', 'retrieval-results.json'):
    result = json.loads((HERE / name).read_text(encoding='utf-8'))
    rows, mismatch, failures = result['observations'], [], []
    counts = {}
    for row in rows:
        label = labels[row['query_id']]
        expected = [any(e['document_id'] == item['document_id'] and
                        any(normalized(needle) in normalized(e['text']) for needle in item['required_any'])
                        for e in row['top5']) for item in label['evidence']]
        if expected != row['evidence_at5']:
            mismatch.append(row['query_id'])
        kind = row['kind']
        value = counts.setdefault(kind, {'queries': 0, 'all_evidence': 0, 'facts': 0, 'expected_facts': 0,
                                         'zero_evidence': 0})
        value['queries'] += 1
        value['all_evidence'] += bool(expected) and all(expected)
        value['facts'] += sum(expected)
        value['expected_facts'] += len(expected)
        value['zero_evidence'] += not row['top5']
        if kind in ('positive', 'multi_evidence') and not all(expected):
            failures.append({'id': row['query_id'], 'covered': expected, 'expected': label['evidence'],
                             'returned_documents': [e['document_id'] for e in row['top5']]})
    audits[name] = {'status': result['status'], 'cleanup': result.get('cleanup'),
        'snapshot_matches_frozen_bytes': result['snapshot'] == freeze == snapshot,
        'observations': len(rows), 'label_recalculation_mismatches': mismatch,
        'all_candidate_counts_at_most_20': all(r['candidate_count'] <= 20 for r in rows),
        'all_evidence_counts_at_most_5': all(len(r['top5']) <= 5 for r in rows),
        'all_expanded_context_within_4500_proxy': all(sum(proxy(e['text']) for e in r['top5']) <= 4500 for r in rows),
        'max_expanded_context_proxy': max(sum(proxy(e['text']) for e in r['top5']) for r in rows),
        'counts': counts, 'strict_failures': failures,
        'legacy_historical_mode_rejection': [{'id': r['query_id'], 'reason': r['reason'],
                                             'diagnostics': r['diagnostics']} for r in rows
                                            if r['query_id'].replace('-', '') in ('KQ041', 'KQ042', 'KQ043', 'KQ044')],
        'critical_policy_full_returned_text': {r['query_id']: r['top5'] for r in rows
            if r['query_id'].replace('-', '') in ('KQ033', 'KQ034', 'KQ035', 'KQ036', 'KQ056', 'KQ058', 'P6Q009', 'P6Q010')}}
print(json.dumps({'scope': 'read-only audit, no new model run', 'audits': audits}, ensure_ascii=False, indent=2))
