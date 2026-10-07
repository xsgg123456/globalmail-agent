"""Bind dependent experiments to a successful run and current source snapshot."""
import json

from chunking import Budget, build_chunks, load_documents
from common import HERE, WORK, fingerprint, read
from embedding_client import validate

STRATEGIES = ('whole', 'fixed500', 'structured300', 'structured500')
MODELS = ('text-embedding-v4', 'qwen3.7-text-embedding')


def current_inputs():
    queries = [json.loads(line) for line in (HERE/'retrieval-queries.jsonl').read_text(encoding='utf-8').splitlines()
               if line.strip()]
    documents = load_documents()
    if read(WORK/'documents-normalized.json') != documents:
        raise ValueError('Normalized documents are stale; rerun chunking')
    strategies = {name:read(WORK/f'chunks-{name}.json') for name in STRATEGIES}
    for name,chunks in strategies.items():
        if chunks != build_chunks(documents,name,Budget()):
            raise ValueError('Chunks are stale; rerun chunking')
    snapshot = {'queries':fingerprint(queries), 'parents':fingerprint(documents),
                'strategies':{name:fingerprint(chunks) for name,chunks in strategies.items()}}
    return queries, {d['parent_id']:d for d in documents}, strategies, snapshot


def verify_dataset(report, data, model, strategy, snapshot):
    if report.get('status') != 'completed' or not report.get('all_models_completed'):
        raise ValueError('Upstream retrieval run did not complete')
    entries = {entry['model']:entry for entry in report['models']}
    entry = entries.get(model, {})
    if (entry.get('status') != 'completed' or report.get('input_snapshot') != snapshot
            or not report.get('run_id') or data.get('run_id') != report['run_id']
            or data.get('input_snapshot') != snapshot
            or entry.get('artifact_fingerprints', {}).get(strategy) != fingerprint(data)
            or data.get('profile', {}).get('model') != model
            or fingerprint(data['chunks']) != snapshot['strategies'][strategy]
            or fingerprint(data['queries']) != snapshot['queries']):
        raise ValueError('Retrieval artifact is stale or mismatched')
    if len(data['chunks']) != len(data['vectors']) or len(data['queries']) != len(data['query_vectors']):
        raise ValueError('Retrieval artifact vector count mismatch')
    for vector in data['vectors'] + data['query_vectors']:
        validate(vector)
    return data


def load_verified_dataset(model, strategy='structured500'):
    _, _, _, snapshot = current_inputs()
    report = read(HERE/'retrieval-results.json')
    data = read(WORK/f'retrieval-{model}-{strategy}.json')
    return verify_dataset(report,data,model,strategy,snapshot)
