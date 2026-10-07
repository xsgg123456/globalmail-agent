"""Archive compact, reproducible evidence; never promote it to human acceptance."""
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    runs = []
    for directory in sorted((ROOT / 'tmp/vision-spike').iterdir()):
        source = directory / 'results.json'
        if not source.exists():
            continue
        result = json.loads(source.read_text(encoding='utf-8'))
        records = result.get('records', [])
        usages = [r['usage'] for r in records if r.get('usage')]
        evaluation = directory / 'evaluation.json'
        entry = {'run': directory.name, 'status': result.get('status'),
                 'source_sha256': sha(source), 'records': len(records),
                 'technical_status_counts': dict(Counter(r['status'] for r in records)),
                 'known_total_tokens': sum(u.get('total_tokens', 0) for u in usages),
                 'unknown_usage_records': sum(r.get('usage') is None for r in records),
                 'interrupted_inflight_usage': 'unknown' if 'interrupt' in result.get('status', '') else 'not_asserted',
                 'max_input_tokens': max((u.get('prompt_tokens', 0) for u in usages), default=0),
                 'max_output_tokens': max((u.get('completion_tokens', 0) for u in usages), default=0),
                 'elapsed_seconds_range': [min((r['elapsed_seconds'] for r in records), default=0),
                                           max((r['elapsed_seconds'] for r in records), default=0)]}
        if evaluation.exists():
            scored = json.loads(evaluation.read_text(encoding='utf-8'))
            entry['evaluation'] = {k: v for k, v in scored.items() if k != 'scores'}
            entry['request_checks'] = scored['scores']
        semantic_path = HERE / ('semantic-review-' + directory.name.removeprefix('final-') + '.json')
        if semantic_path.exists():
            semantic = json.loads(semantic_path.read_text(encoding='utf-8'))
            if semantic.get('source_sha256') == entry['source_sha256']:
                entry['independent_agent_semantic_review'] = {k: v for k, v in semantic.items() if k != 'records'}
        runs.append(entry)
    output = {'status': 'phase_1_acceptance_failed', 'human_label_review': 'pending',
              'production_acceptance': 'not_run', 'runs': runs,
              'current_source_sha256': {p.name: sha(p) for p in sorted(HERE.glob('*.py'))}}
    target = HERE / 'results-summary.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps([{k: v for k, v in r.items() if k not in ('request_checks', 'evaluation')} for r in runs], ensure_ascii=False))


if __name__ == '__main__':
    main()
