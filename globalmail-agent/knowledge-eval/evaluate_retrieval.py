"""Private PG + production services + actual parser/embedding; frozen developer queries."""
import hashlib
import json
from pathlib import Path
import time
from uuid import UUID, uuid4
import sqlalchemy as sa
from pydantic import ValidationError
from globalmail_agent.adapters.conversation_schema import jobs
from globalmail_agent.adapters.knowledge_schema import documents, parse_caches
from globalmail_agent.adapters.knowledge_index_schema import embedding_cache, index_builds
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.knowledge.commands import Command, ReviewCommand
from globalmail_agent.knowledge.prepared import PreparedImport
from globalmail_agent.knowledge.builds import BuildService
from globalmail_agent.knowledge.releases import ReleaseService
from globalmail_agent.knowledge.retrieval import KnowledgeSearch
from globalmail_agent.knowledge.index_commands import BuildCommand, ReleaseCommand, SearchCommand
from globalmail_agent.knowledge.embedding import EmbeddingGateway
from globalmail_agent.worker.knowledge_runner import KnowledgeRunner
from knowledge_helpers import KnowledgeFixture
from provider_config import ROOT, configured_settings, isolated_database_environment, write_json

HERE = Path(__file__).resolve().parent
QUERY_FILES = [ROOT / 'globalmail-agent/knowledge-spike/retrieval-queries.jsonl', HERE / 'extra-queries.jsonl']


def normalized(text):
    return ''.join(text.split()).casefold()


def snapshot():
    return {p.name: {'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                    'count': len(p.read_text(encoding='utf-8').splitlines())} for p in QUERY_FILES}


def drain(fixture, runner, limit=900):
    deadline = time.monotonic() + limit
    while time.monotonic() < deadline:
        job = runner.jobs.claim(runner.owner)
        if job:
            try: runner.execute(job)
            except ServiceError as error:
                runner.safe_fail(job, error.code, error.status == 503)
            except Exception as error:
                runner.safe_fail(job, getattr(error, 'code', 'evaluation_worker_error'), False)
            print(json.dumps({'stage': 'worker', 'operation': job['knowledge_operation'], 'version_id': str(job['knowledge_version_id'])}), flush=True)
        with fixture.engine.connect() as conn:
            active = conn.execute(sa.select(sa.func.count()).select_from(jobs).where(jobs.c.status.in_(['queued', 'running']))).scalar_one()
        if not active: return
        time.sleep(.2)
    raise RuntimeError('isolated_worker_deadline')


def summarize(observations):
    groups = {}
    for kind in ('positive', 'multi_evidence', 'boundary', 'unanswerable'):
        subset = [o for o in observations if o['kind'] == kind]
        groups[kind] = {'queries': len(subset)}
        if kind in ('positive', 'multi_evidence'):
            groups[kind].update(all_key_evidence_at5=sum(all(o['evidence_at5']) for o in subset),
                recalled_evidence=sum(sum(o['evidence_at5']) for o in subset),
                expected_evidence=sum(len(o['evidence_at5']) for o in subset))
        elif kind == 'boundary': groups[kind]['zero_evidence'] = sum(o['evidence_count'] == 0 for o in subset)
        else: groups[kind]['related_candidates'] = sum(o['evidence_count'] > 0 for o in subset)
    return groups


def evaluate(fixture, runner, gateway):
    imported = PreparedImport(fixture.engine, fixture.store).importing(Command(expected_version=0), uuid4().hex)
    drain(fixture, runner)
    versions, exclusions = [], {}
    for raw_id in imported['version_ids']:
        identity = UUID(raw_id)
        detail = fixture.queries.version_detail(identity)
        v = detail['version']
        if v['status'] != 'needs_review': raise RuntimeError('prepared_parse_not_completed')
        excluded = sorted({b for d in detail['diagnostics'] if d.get('blocks_review') or d.get('severity') == 'error'
                           for b in d.get('block_ids', [])})
        # Test-only review: unresolved diagram meaning is explicitly excluded, never asserted understood.
        fixture.reviews.review(identity, ReviewCommand.model_validate({**fixture.review_payload(identity),
            'note': '隔离评测夹具核对：沿用Phase5已核验的固定正文与页范围；未覆盖图意块明确排除。不代表正式知识发布批准。',
            'excluded_block_ids': excluded, 'exclusion_reason': '本轮只验文本检索，图意未覆盖块排除。' if excluded else None}), uuid4().hex)
        exclusions[raw_id] = excluded
        versions.append(identity)
    builds = BuildService(fixture.engine, fixture.store, gateway)
    created = []
    for identity in versions:
        v = fixture.queries.version_detail(identity)['version']
        created.append(builds.enqueue_build(identity, BuildCommand(expected_version=v['row_version'],
            embedding_profile_key='qwen3.7-text-embedding', chunking_profile_key='structure_v1_500'), uuid4().hex))
    drain(fixture, runner)
    states = [builds.status(identity) for identity in versions]
    if not all(s['builds'][0]['status'] == 'ready' and s['builds'][0]['eligible'] for s in states):
        write_json(HERE / 'failed-builds.json', states)
        raise RuntimeError('prepared_index_not_completed')
    release = ReleaseService(fixture.engine, fixture.store).publish(ReleaseCommand(expected_release_epoch=0,
        build_ids=[UUID(b['build_id']) for b in created]), uuid4().hex)
    with fixture.engine.connect() as conn:
        doc_ids = {str(r.id): r.prepared_id for r in conn.execute(sa.select(documents.c.id, documents.c.prepared_id))}
        counts = {t.name: conn.execute(sa.select(sa.func.count()).select_from(t)).scalar_one()
                  for t in (parse_caches, embedding_cache, index_builds)}
    search = KnowledgeSearch(fixture.engine, fixture.store, gateway)
    observations = []
    for path in QUERY_FILES:
        for row in path.read_text(encoding='utf-8').splitlines():
            query = json.loads(row)
            started = time.monotonic()
            payload = {k: query[k] for k in ('query', 'sku', 'mode', 'as_of')}
            try:
                command = SearchCommand.model_validate(payload)
            except ValidationError:
                response = fixture.post('/knowledge/search', payload)
                if query['kind'] != 'boundary' or response.status_code != 422:
                    raise RuntimeError('unexpected_query_validation_failure')
                output = {'reason': 'invalid_input_rejected', 'candidate_count': 0, 'evidence': [],
                          'usage': None, 'diagnostics': [{'http_status': response.status_code}]}
            else:
                output = search.search(command)
            evidence = [{**e, 'prepared_id': doc_ids[e['document_id']]} for e in output['evidence']]
            covered = [any(e['prepared_id'] == label['document_id'] and any(normalized(needle) in normalized(e['text'])
                       for needle in label['required_any']) for e in evidence) for label in query['evidence']]
            item = {'query_id': query['query_id'], 'kind': query['kind'], 'split': query['split'],
                'reason': output['reason'], 'candidate_count': output['candidate_count'], 'evidence_count': len(evidence),
                'evidence_at5': covered, 'expected_evidence': query['evidence'],
                'top5': [{'document_id': e['prepared_id'], 'score': round(e['score'], 6), 'page': e['page'],
                         'section': e['section'], 'version_number': e['version_number'], 'text': e['text']} for e in evidence],
                'usage': output['usage'], 'diagnostics': output['diagnostics'], 'seconds': round(time.monotonic() - started, 3)}
            observations.append(item)
            print(json.dumps({'query': item['query_id'], 'reason': item['reason'], 'hits': covered}), flush=True)
            write_json(HERE / 'retrieval-progress.json', {'snapshot': snapshot(), 'observations': observations})
    return {'scope': 'developer_queries_actual_pg_not_production_accuracy', 'status': 'completed',
        'profile': gateway.profiles()[0], 'snapshot': snapshot(), 'document_count': len(versions), 'counts': counts,
        'release_epoch': release['head']['epoch'], 'excluded_unverified_diagram_blocks': exclusions,
        'builds': [s['builds'][0] for s in states], 'summary': summarize(observations),
        'original_60': summarize([o for o in observations if o['split'] == 'dev']),
        'new_12': summarize([o for o in observations if o['split'] != 'dev']), 'observations': observations,
        'limits': ['Fixture author knew the materials; new queries are not independent business holdout.',
                   'Related evidence for missing facts does not prove abstention or correct final answers.',
                   'Actual provider embeddings and exact PG cosine; no chat model, Agent or mailbox run.',
                   'Unverified diagram-only blocks excluded; no claim of diagram comprehension.']}


def main():
    frozen = json.loads((HERE / 'query-freeze.json').read_text(encoding='utf-8'))
    if frozen['snapshot'] != snapshot(): raise RuntimeError('query_set_changed_after_freeze')
    isolated_database_environment()
    fixture = KnowledgeFixture('runTest')
    try:
        fixture.setUp()
        gateway = EmbeddingGateway(configured_settings())
        runner = KnowledgeRunner(fixture.engine, fixture.store, DEFAULT_WORKSPACE_ID, gateway)
        result = evaluate(fixture, runner, gateway)
    finally: fixture.doCleanups()
    result['cleanup'] = 'owned_schema_and_objects_removed'
    write_json(HERE / 'retrieval-results.json', result)
    print(json.dumps(result['summary'], ensure_ascii=False))


if __name__ == '__main__': main()
