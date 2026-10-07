"""Offline fixture validation and human-review checklist; no provider calls."""
import hashlib
import json
from pathlib import Path
from prepare_views import DATA, prepare


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines()]


def main():
    rows = read_rows(DATA / 'manifest.jsonl')
    labels = read_rows(DATA / 'evaluation/labels.jsonl')
    freeze = json.loads((DATA / 'freeze.json').read_text(encoding='utf-8'))
    for key, name in [('manifest_sha256', 'manifest.jsonl'), ('labels_sha256', 'evaluation/labels.jsonl'),
                      ('branch_matrix_sha256', 'branch-matrix.json'), ('provenance_sha256', 'source-provenance.json')]:
        assert hashlib.sha256((DATA / name).read_bytes()).hexdigest() == freeze[key], name
    ids = [r['id'] for r in rows]
    assert len(ids) == len(set(ids))
    assert set(ids) == {label['id'] for label in labels}
    assert {r['brand'] for r in rows} == {'OUTON', 'OUTONLIFE', 'BELEEV'}
    checks = []
    for row in rows:
        assert not {'expected_fields', 'allowed_routes', 'expected_observation', 'expected_risk', 'reference_reply'} & row.keys()
        views, coverage = prepare(row)
        assert views or row['body'], row['id']
        checks.append({'id': row['id'], 'views': len(views), 'coverage': coverage})
    output = {'fixture_checks': 'passed', 'cases': len(rows),
              'human_review': 'pending', 'product_acceptance': 'not_run', 'checks': checks}
    (DATA / 'validation.json').write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'fixture_checks': 'passed', 'cases': len(rows), 'human_review': 'pending'}))


if __name__ == '__main__':
    main()
