"""Run real-vector lifecycle contracts in an owned, disposable PostgreSQL container."""
import copy
import hashlib
import json
import secrets
import subprocess
import sys
import time
import traceback
from pathlib import Path

import psycopg

from lifecycle_store import ContractError, Store, digest, validate_vectors
from artifact_contract import load_verified_dataset, MODELS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
WORK = ROOT/'tmp/knowledge-spike'
REPORT = HERE/'lifecycle-results.json'
IMAGE = 'pgvector/pgvector@sha256:78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff'
sys.path.insert(0, str(HERE.parent/'tech-spike'))
from probe_support import cleanup_database, run_reported
from test_lifecycle_contract import run_suite


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True, encoding='utf-8',
                                   stderr=subprocess.PIPE, timeout=60).strip()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rejected(fn, code):
    try:
        fn()
    except ContractError as exc:
        assert str(exc) == code, 'Unexpected rejection code'
        return
    raise AssertionError('Expected contract rejection did not occur')


def check_versions(rows, build, version):
    assert rows and {r['build'] for r in rows} == {build}
    assert {r['version'] for r in rows} == {version}


def exercise(store, first, second, record):
    chunks, vectors = first['chunks'], first['vectors']
    assert chunks == second['chunks'], 'Model comparison must use identical chunks'
    assert first['queries'] == second['queries'], 'Query inputs must match across profiles'
    for data in (first, second):
        validate_vectors(data['query_vectors'],len(data['queries']),data['profile']['dimensions'])
    profiles = [{**d['profile'], 'parser':'normalized-source-v1', 'splitter':'structured500'}
                for d in (first, second)]
    p1, p2 = map(digest, profiles)
    assert p1 != p2 and profiles[0]['dimensions'] == profiles[1]['dimensions']
    registry = {p['sku']:p['brand'] for p in read(ROOT/'data/knowledge/v1/products.json')}
    store.register_products(registry)
    queries = [{**q, 'brand':registry.get(q['sku'], '__unknown__'), 'knowledge_split':'rag'}
               for q in first['queries']]
    q, vq = queries[0], first['query_vectors'][0]
    def search(profile=p1, vector=vq, query=q):
        with store.connect() as conn:
            return store.search(conn, profile, query, vector)
    epoch = store.epoch()
    store.prepare('baseline', 'content-v1', profiles[0], chunks, vectors, epoch)
    store.finish('baseline', chunks, vectors, epoch)
    store.prepare('baseline', 'content-v1', profiles[0], chunks, vectors, epoch)
    store.finish('baseline', chunks, vectors, epoch)
    with store.connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM chunks WHERE build='baseline'").fetchone()['n'] == len(chunks)
    changed = copy.deepcopy(chunks)
    changed[0]['text'] += '\nSynthetic payload-conflict marker; never embedded or published.'
    rejected(lambda:store.prepare('baseline','content-v1',profiles[0],changed,vectors,epoch),
             'idempotency_payload_conflict')
    epoch = store.publish('baseline', epoch)
    initial = search()
    check_versions(initial, 'baseline', 'content-v1')
    assert store.guard(initial, q)
    record('initial_publish_real_vectors_and_idempotent_build',
           {'chunks':len(chunks), 'dimensions':profiles[0]['dimensions'], 'model':profiles[0]['model'],
            'repeat_build_rows':len(chunks), 'conflicting_payload_rejected':True})

    by_id = {c['chunk_id']:c for c in chunks}
    for query, vector in zip(queries, first['query_vectors']):
        rows = search(query=query, vector=vector)
        for row in rows:
            c = by_id[row['id']]
            assert query['sku'] in c['skus'] and query['brand'] in c['brands']
            assert query['mode'] in c['allowed_modes'] and c['usage_split'] == query['knowledge_split']
        if query['kind'] == 'boundary':
            assert not rows
    negatives = {'sku':'UNREGISTERED-SKU', 'brand':'BELEEV', 'mode':'historical_eval',
                 'knowledge_split':'eval_holdout', 'as_of':'2000-01-01T00:00:00+08:00'}
    for field, value in negatives.items():
        assert not search(query={**q, field:value}), field
    record('sql_scope_before_vector_ranking', {'developer_queries':len(queries),
        'negative_fields':list(negatives), 'candidate_cte':'MATERIALIZED; filters precede ORDER BY/LIMIT',
        'query_split':'dev is query-set membership; knowledge_split=rag is retrieval authorization',
        'brand_source':'registered products.json SKU mapping; no SKU-prefix inference'})

    store.prepare('replacement', 'content-v2', profiles[0], chunks, vectors, epoch)
    rejected(lambda:store.publish('replacement', epoch), 'build_not_ready_or_reviewed')
    check_versions(search(), 'baseline', 'content-v1')
    store.finish('replacement', chunks, vectors, epoch)
    record('unready_replacement_preserves_previous_release', {'rejected':True, 'active':'baseline'})
    with store.connect() as old, old.transaction():
        old.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        cached = store.search(old, p1, q, vq)
        check_versions(cached, 'baseline', 'content-v1')
        epoch = store.publish('replacement', epoch)
        check_versions(store.search(old,p1,q,vq), 'baseline','content-v1')
        check_versions(search(), 'replacement','content-v2')
        assert not store.guard(cached, q)
    epoch = store.publish('baseline', epoch, action='rollback')
    check_versions(search(), 'baseline','content-v1')
    record('atomic_publication_rollback_and_two_connection_snapshot',
           {'old_transaction':'content-v1', 'new_transaction':'content-v2', 'rollback':'content-v1',
            'old_reference_guard':False, 'version_variant':'synthetic version labels; unchanged real text/vectors'})

    store.prepare('new-model', 'content-v1', profiles[1], second['chunks'], second['vectors'], epoch)
    rejected(lambda:store.finish('new-model',chunks,second['vectors'][:-1],epoch),'vector_count')
    rejected(lambda:store.publish('new-model', epoch), 'build_not_ready_or_reviewed')
    check_versions(search(), 'baseline','content-v1')
    store.finish('new-model', second['chunks'], second['vectors'], epoch)
    with store.connect() as old, old.transaction():
        old.execute('SET TRANSACTION ISOLATION LEVEL REPEATABLE READ')
        before = store.search(old,p1,q,vq)
        epoch = store.publish('new-model', epoch)
        check_versions(store.search(old,p1,q,vq), 'baseline','content-v1')
        assert not search()
        new = search(p2,second['query_vectors'][0])
        check_versions(new, 'new-model','content-v1')
        assert {r['profile'] for r in new} == {p2} and not store.guard(before,q)
    epoch = store.publish('baseline', epoch, action='rollback')
    check_versions(search(), 'baseline','content-v1')
    record('real_same_dimension_profile_switch_failure_and_rollback',
           {'models':[p['model'] for p in profiles], 'dimensions':profiles[0]['dimensions'],
            'old_profile_on_new_release_rows':0, 'old_transaction_keeps_old_space':True,
            'new_transaction_only_new_space':True, 'failed_build_keeps_old_profile':True,
            'injected_completion_failure':'missing vector rejected as vector_count'})

    stale_epoch = epoch
    store.prepare('late-task', 'content-v3', profiles[0], chunks, vectors, epoch)
    cached = search()
    docs = sorted({c['document_id'] for c in chunks})
    epoch = store.revoke(docs, epoch)
    assert not search() and not store.guard(cached,q)
    rejected(lambda:store.finish('late-task',chunks,vectors,stale_epoch),'stale_epoch')
    rejected(lambda:store.publish('baseline',stale_epoch),'stale_epoch')
    record('disable_invalidates_new_search_cache_reply_and_late_task',
           {'documents':len(docs), 'cached_epoch':stale_epoch, 'live_epoch':epoch,
            'new_rows':0, 'reply_guard':False, 'late_completion_and_publish':'stale_epoch'})

    epoch = store.revoke(docs, epoch, delete=True)
    with store.connect() as conn:
        remaining = conn.execute('SELECT count(*) AS n FROM chunks WHERE document=ANY(%s)', (docs,)).fetchone()['n']
        tombstones = conn.execute('SELECT count(*) AS n FROM documents WHERE tombstone AND id=ANY(%s)', (docs,)).fetchone()['n']
    assert remaining == 0 and tombstones == len(docs)
    rejected(lambda:store.prepare('reborn','content-v4',profiles[0],chunks,vectors,epoch),
             'document_revoked_or_deleted')
    rejected(lambda:store.publish('baseline',epoch),'document_revoked_or_deleted')
    assert not search() and not store.guard(cached,q)
    record('content_vectors_deleted_tombstone_blocks_rebuild_and_republish',
           {'remaining_content_vector_rows':remaining, 'tombstones':tombstones,
            'scope':'database rows only; no object store, checkpoint, trace or backup cleanup'})


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    nonce = secrets.token_hex(6)
    name = 'globalmail-knowledge-lifecycle-'+nonce
    env_file = WORK/('lifecycle-db-'+nonce+'.env')
    container_id = None
    launch_attempted = False
    result = {'scope':'isolated_minimum_lifecycle_contract_not_product_acceptance', 'image':IMAGE,
              'passed':False, 'checks':[], 'stage':'load_real_vectors',
              'limitations':['No API, UI, worker leases, bounded retries or production service.',
                'No policy-rule/explanation atomic bundle or embedding cache reuse implementation.',
                'Deletion covers experiment database content/vector rows only; no privacy cleanup or restore claim.',
                'Retained MVCC snapshots can see old rows; guard uses a fresh transaction before submission.']}
    result['vector_provenance'] = {'retrieval_and_profile_switch':'real provider vectors from existing frozen inputs',
        'content_version_change':'synthetic version labels; unchanged real content and embeddings',
        'failure_and_concurrency_tests':'explicit three-dimensional synthetic fixtures'}
    def record(name, detail):
        result['checks'].append({'name':name,'passed':True,'detail':detail})
        print(json.dumps({'check':name,'passed':True}), flush=True)
    try:
        paths = [WORK/f'retrieval-{model}-structured500.json'
                 for model in ('text-embedding-v4','qwen3.7-text-embedding')]
        datasets = [load_verified_dataset(model) for model in MODELS]
        result['inputs'] = [{'file':path.name,'file_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                            'fingerprint':digest(data), 'profile':data['profile']}
                            for path,data in zip(paths,datasets)]
        result['stage'] = 'temporary_database_start'
        password = secrets.token_hex(24)
        env_file.write_text('POSTGRES_PASSWORD='+password+'\nPOSTGRES_DB=knowledge_lifecycle\n',encoding='utf-8')
        launch_attempted = True
        container_id = docker('run','--detach','--rm','--name',name,'--label','globalmail.tech-spike='+nonce,
            '--memory','1g','--tmpfs','/var/lib/postgresql:rw','--publish','127.0.0.1::5432',
            '--env-file',str(env_file),IMAGE)
        port = docker('port',container_id,'5432/tcp').rsplit(':',1)[1]
        dsn = f'postgresql://postgres:{password}@127.0.0.1:{port}/knowledge_lifecycle'
        for _ in range(30):
            try:
                with psycopg.connect(dsn,connect_timeout=2) as conn:
                    conn.execute('SELECT 1')
                break
            except psycopg.OperationalError:
                time.sleep(1)
        else:
            raise RuntimeError('Temporary database readiness timeout')
        store = Store(dsn)
        store.initialize()
        result['psycopg'] = psycopg.__version__
        with store.connect() as conn:
            result['postgresql'] = conn.execute('SHOW server_version').fetchone()['server_version']
            result['pgvector'] = conn.execute("SELECT extversion FROM pg_extension WHERE extname='vector'").fetchone()['extversion']
        result['stage'] = 'lifecycle_checks'
        exercise(store,*datasets,record)
        result['stage'] = 'failure_and_concurrency_regressions'
        result['contract_tests'] = run_suite(dsn)
        assert result['contract_tests']['passed'], 'Failure or concurrency regression failed'
        result.update(passed=True, stage='completed')
    except BaseException as exc:
        result.update(passed=False,error_type=type(exc).__name__)
        result['failure_frames'] = [{'file':Path(f.filename).name,'line':f.lineno,'function':f.name}
                                    for f in traceback.extract_tb(exc.__traceback__)]
        raise
    finally:
        # Unknown docker-run outcome still attempts name+ownership-label cleanup, never all containers.
        owned_target = container_id or (name if launch_attempted else None)
        cleaned = cleanup_database(docker,owned_target,nonce,env_file,result)
        REPORT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        if not cleaned:
            raise RuntimeError('Temporary resource cleanup incomplete; report contains safe flags')


if __name__ == '__main__':
    run_reported(REPORT,main)
