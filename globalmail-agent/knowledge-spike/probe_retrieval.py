"""Actual provider embeddings on a frozen, developer-authored evidence set."""
import json
import time
from collections import Counter
from uuid import uuid4

import numpy as np
from chunking import eligible, verified_parent
from common import HERE, WORK, read, write, normalized, fingerprint, execute_report
from embedding_client import embed
from artifact_contract import current_inputs, MODELS


def evidence_covered(evidence, chunks):
    return any(c['document_id'] == evidence['document_id'] and
               any(normalized(needle) in normalized(c['text']) for needle in evidence['required_any'])
               for c in chunks)


def evaluate(chunks, vectors, queries, query_vectors, parents):
    matrix = np.asarray(vectors, dtype=np.float64)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    observations = []
    for query, vector in zip(queries, query_vectors):
        start = time.perf_counter()
        vector = np.asarray(vector, dtype=np.float64)
        scores = matrix @ (vector/np.linalg.norm(vector))
        allowed = [i for i,c in enumerate(chunks) if eligible(c, query)]
        ranked = sorted(allowed, key=lambda i: float(scores[i]), reverse=True)
        top = [chunks[i] for i in ranked[:5]]
        expanded = []
        seen = set()
        for c in top:
            if c['parent_id'] not in seen:
                seen.add(c['parent_id'])
                parent = verified_parent(c, parents, query)
                if parent is not None:
                    expanded.append({**c, 'text': parent['text']})
        item = {'query_id': query['query_id'], 'kind': query['kind'], 'language': query['language'],
                'candidate_count': len(allowed),
                'top5': [{'chunk_id': chunks[i]['chunk_id'], 'document_id': chunks[i]['document_id'],
                          'score': round(float(scores[i]), 6)} for i in ranked[:5]],
                'evidence_at1': [evidence_covered(e,top[:1]) for e in query['evidence']],
                'evidence_at5': [evidence_covered(e,top) for e in query['evidence']],
                'parent_evidence_at5': [evidence_covered(e,expanded) for e in query['evidence']],
                'local_search_ms': round((time.perf_counter()-start)*1000, 3)}
        observations.append(item)
    groups = {}
    for kind in ['positive','multi_evidence','boundary','unanswerable']:
        subset = [o for o in observations if o['kind'] == kind]
        groups[kind] = {'queries': len(subset)}
        if kind in {'positive','multi_evidence'}:
            for metric in ['evidence_at1','evidence_at5','parent_evidence_at5']:
                groups[kind][metric+'_all_hits'] = sum(all(o[metric]) for o in subset)
        else:
            groups[kind]['empty_candidates'] = sum(o['candidate_count'] == 0 for o in subset)
    return {'summary': groups, 'observations': observations,
            'local_search_p95_ms': float(np.percentile([o['local_search_ms'] for o in observations], 95))}


def main():
    queries, parents, strategies, snapshot = current_inputs()
    assert Counter(q['kind'] for q in queries) == {'positive':36,'boundary':12,'unanswerable':6,'multi_evidence':6}
    result = {'scope':'frozen_developer_queries_not_independent_evaluation', 'query_count':len(queries),
              'run_id':str(uuid4()), 'input_snapshot':snapshot,
              'query_fingerprint':fingerprint(queries), 'models':[],
              'limitations':['retrieval presence is not answer correctness',
                'parent expansion measured separately; no full Agent execution',
                'unanswerable may retrieve related text; abstention requires separate validation',
                'NumPy ranking here; PostgreSQL lifecycle is a separate probe']}
    text_inputs = [q['query'] for q in queries]
    offsets = {}
    for strategy,chunks in strategies.items():
        offsets[strategy] = len(text_inputs)
        text_inputs.extend(c['embedding_input'] for c in chunks)
    for model in MODELS:
        entry = {'model':model,'status':'running'}
        result['models'].append(entry)
        write(HERE/'retrieval-progress.json', result)
        try:
            vectors,meta = embed(text_inputs,model)
            entry.update(embedding_calls=meta,strategies={},artifact_fingerprints={})
            for strategy,chunks in strategies.items():
                subset = vectors[offsets[strategy]:offsets[strategy]+len(chunks)]
                score = evaluate(chunks,subset,queries,vectors[:len(queries)],parents)
                entry['strategies'][strategy] = score
                artifact = {'chunks':chunks,'vectors':subset,'queries':queries,'query_vectors':vectors[:len(queries)],
                            'profile':meta['profile'],'observations':score['observations'],
                            'run_id':result['run_id'],'input_snapshot':snapshot}
                write(WORK/f'retrieval-{model}-{strategy}.json',artifact)
                entry['artifact_fingerprints'][strategy] = fingerprint(artifact)
                print(json.dumps({'model':model,'strategy':strategy,**score['summary']}),flush=True)
            entry['status'] = 'completed'
        except Exception as exc:
            entry.update(status='failed',error_type=type(exc).__name__,http_status=getattr(exc,'status_code',None))
            print(json.dumps({'model':model,'status':'failed','error_type':type(exc).__name__}),flush=True)
        write(HERE/'retrieval-progress.json',result)
    result['baseline_available'] = result['models'][0]['status'] == 'completed'
    result['all_models_completed'] = all(m['status']=='completed' for m in result['models'])
    result['status'] = 'completed' if result['all_models_completed'] else 'failed'
    write(HERE/'retrieval-progress.json',result)
    return result


if __name__ == '__main__':
    result = execute_report('retrieval-results.json', main)
    if not result['all_models_completed']:
        raise SystemExit(1)
