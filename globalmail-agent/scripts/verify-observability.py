"""Paid Qwen observation proof in an existing disposable Phase11 session only."""
import argparse
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import sys
import time
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'globalmail-agent/backend/src'))


def private_environment():
    allowed = {'LLM_API_KEY', 'LLM_MODEL', 'LLM_BASE_URL', 'GLOBALMAIL_EMBEDDING_API_KEY',
        'GLOBALMAIL_EMBEDDING_BASE_URL', 'GLOBALMAIL_LANGFUSE_ENABLED', 'GLOBALMAIL_LANGFUSE_BASE_URL',
        'GLOBALMAIL_LANGFUSE_PUBLIC_KEY', 'GLOBALMAIL_LANGFUSE_SECRET_KEY', 'GLOBALMAIL_LANGFUSE_PROJECT_ID'}
    for path in (ROOT / '.env', ROOT / '.local-data/observability/backend.env'):
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            if '=' in line and not line.lstrip().startswith('#'):
                key, value = line.split('=', 1)
                if key in allowed:
                    os.environ[key] = value.strip().strip('"').strip("'")


def isolated_session(path):
    path = path.resolve()
    if not path.is_relative_to((ROOT / 'tmp').resolve()):
        raise ValueError('isolated_session_required')
    session = json.loads(path.read_text(encoding='utf-8'))
    if not re.fullmatch(r'phase11_browser_[0-9a-f]{32}', session['schema']):
        raise ValueError('phase11_session_required')
    from urllib.parse import urlsplit
    url = urlsplit(session['api'])
    if url.scheme != 'http' or url.hostname != '127.0.0.1' or not url.port:
        raise ValueError('loopback_session_required')
    return session, path.parent / 'objects'


def trace_read(settings, trace_id):
    import httpx
    auth = (settings.langfuse_public_key.get_secret_value(), settings.langfuse_secret_key.get_secret_value())
    now = datetime.now(timezone.utc)
    params = {'traceId': trace_id, 'fromStartTime': (now - timedelta(hours=1)).isoformat(),
        'toStartTime': (now + timedelta(minutes=1)).isoformat(),
        'fields': 'core,basic,usage,metadata,io', 'limit': 1000}
    with httpx.Client(base_url=settings.langfuse_base_url, auth=auth, timeout=5, trust_env=False) as client:
        for _ in range(30):
            response = client.get('/api/public/v2/observations', params=params)
            if response.status_code == 200:
                data = response.json()
                rows = data.get('data', [])
                if rows and any(row.get('isRootObservation') for row in rows):
                    if data.get('meta', {}).get('cursor'):
                        raise ValueError('unexpected_trace_pagination')
                    root = next(row for row in rows if row.get('isRootObservation'))
                    return {'id': trace_id, 'sessionId': root.get('sessionId'), 'observations': rows}
            else:
                raise ValueError('langfuse_trace_read_failed')
            time.sleep(1)
    raise ValueError('langfuse_trace_not_visible')


def execute(engine, store, settings, observer, run_id):
    from globalmail_agent.worker.leases import LeaseService
    from globalmail_agent.worker.agent_runner import AgentRunner
    from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
    from globalmail_agent.adapters.model_provider import ModelProvider
    from globalmail_agent.knowledge.embedding import EmbeddingGateway
    from globalmail_agent.application.run_records import RunRecords
    job = LeaseService(engine, DEFAULT_WORKSPACE_ID).claim('phase11_actual_qwen')
    if job is None or str(job['run_id']) != str(run_id):
        raise ValueError('unexpected_isolated_job')
    result = AgentRunner(engine, store, DEFAULT_WORKSPACE_ID, ModelProvider(settings),
        EmbeddingGateway(settings), observability=observer).execute(job)
    observer.flush(timeout=5)
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        state = observer.records.get(UUID(str(run_id)))
        if state['export_status'] != 'pending':
            break
        time.sleep(.2)
    detail = RunRecords(engine, store).get(UUID(str(run_id)))
    proof = {'run_id': str(run_id), 'conversation_id': str(detail['run']['conversation_id']),
        'business_result': result, 'export': state,
        'model_calls': [{'stage': item['stage'], 'status': item['status'],
            'provider_returned': bool(item['response']), 'input_tokens': item['input_tokens'],
            'output_tokens': item['output_tokens'], 'image_views': len((item['request'] or {}).get('image_views', []))}
            for item in detail['model_calls']],
        'tools': [{'name': item['name'], 'status': item['status']} for item in detail['tools']],
        'usage': detail['usage']}
    if state['export_status'] != 'exported':
        proof['observation_pass'] = False
        return proof
    return prove_remote(settings, proof)


def prove_remote(settings, proof):
    state = proof['export']
    if state['export_status'] != 'exported':
        proof['observation_pass'] = False
        return proof
    remote = trace_read(settings, state['trace_id'])
    observations = remote.get('observations', [])
    proof['remote'] = {'trace_id': remote['id'], 'session_id': remote.get('sessionId'),
        'observations': [{'id': item['id'], 'type': item.get('type'), 'name': item.get('name'),
            'parent_id': item.get('parentObservationId'), 'input_tokens': item.get('inputUsage', 0),
            'output_tokens': item.get('outputUsage', 0)} for item in observations]}
    ids = {row['id'] for row in observations}
    generations = [row for row in observations if row.get('type') == 'GENERATION']
    roots = [row for row in observations if row.get('isRootObservation')]
    def expected_parent(row):
        parent = (row.get('metadata') or {}).get('parent_observation_id')
        return f'{UUID(parent).int & ((1 << 64) - 1):016x}' if parent else roots[0]['id']
    proof['parent_links_match_receipts_pass'] = (len(roots) == 1 and all(
        row.get('parentObservationId') == expected_parent(row) for row in observations if not row.get('isRootObservation')))
    proof['hierarchy_pass'] = (len(ids) == len(observations)
        and sum(row.get('isRootObservation', False) for row in observations) == 1
        and all(row.get('parentObservationId') in ids for row in observations if not row.get('isRootObservation'))
        and all(row['traceId'] == state['trace_id'] and row['projectId'] == settings.langfuse_project_id for row in observations)
        and proof['parent_links_match_receipts_pass'])
    proof['usage_projection_pass'] = (len(generations) == len(proof['model_calls'])
        and sum(row.get('inputUsage', 0) for row in generations) == sum(row['input_tokens'] or 0 for row in proof['model_calls'])
        and sum(row.get('outputUsage', 0) for row in generations) == sum(row['output_tokens'] or 0 for row in proof['model_calls']))
    serialized = json.dumps(remote)
    proof['remote_sensitive_marker_absent'] = all(marker not in serialized for marker in
        ('phase11-sensitive@example.invalid', 'data:image', 'base64', 'image_url', 'api_key', 'sk-lf-'))
    proof['observation_pass'] = (remote['id'] == state['trace_id'] and proof['hierarchy_pass'] and proof['usage_projection_pass']
        and proof['remote_sensitive_marker_absent'] and any(row['provider_returned'] for row in proof['model_calls']))
    return proof


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--existing-report', type=Path, help='Read back existing real runs without any model reexecution')
    args = parser.parse_args()
    private_environment()
    session, object_root = isolated_session(args.session)
    import sqlalchemy as sa
    from globalmail_agent.settings import Settings
    from globalmail_agent.adapters.object_store import ObjectStore
    from globalmail_agent.adapters.fixture_loader import FixturePackage
    from globalmail_agent.application.fixture_conversations import FixtureConversations
    from globalmail_agent.application.conversations import ConversationService
    from globalmail_agent.domain.conversation import Command, AppendMessage
    from globalmail_agent.attachments.intake import AttachmentService
    from globalmail_agent.observability.service import ObservabilityService
    private = json.loads((ROOT / '.local-data/runtime/settings.json').read_text(encoding='utf-8-sig'))
    engine = sa.create_engine(private['database_url'], hide_parameters=True,
        connect_args={'options': '-csearch_path=' + session['schema']})
    store = ObjectStore(object_root, engine)
    settings = Settings.from_env()
    if not settings.langfuse_enabled or not settings.model_api_key.get_secret_value():
        raise ValueError('model_and_observability_configuration_required')
    observer = ObservabilityService(engine, store, settings)
    report = {'source': 'isolated synthetic scenarios with actual Qwen calls', 'schema': session['schema'],
        'scope': 'Phase11 observation, not Phase13 semantic acceptance', 'runs': []}
    try:
        if args.existing_report:
            from globalmail_agent.application.run_records import RunRecords
            report = json.loads(args.existing_report.read_text(encoding='utf-8'))
            if report['schema'] != session['schema']:
                raise ValueError('same_isolated_schema_required')
            report['readback_without_reexecution'] = True
            for row in report['runs']:
                run_id = UUID(row['run_id'])
                detail = RunRecords(engine, store).get(run_id)
                if detail['usage'] != row['usage'] or len(detail['model_calls']) != len(row['model_calls']):
                    raise ValueError('usage_changed_during_export_recovery')
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    row['export'] = observer.records.get(run_id)
                    if row['export']['export_status'] != 'pending':
                        break
                    time.sleep(.2)
                prove_remote(settings, row)
        else:
            observer.start()
            package = FixturePackage()
            first = FixtureConversations(engine, store, package).create('BASE-OUTON-03', Command(expected_version=0), uuid4().hex)
            report['runs'].append(execute(engine, store, settings, observer, first['run_id']))
            second = FixtureConversations(engine, store, deepcopy(package)).create('BASE-OUTON-06', Command(expected_version=0), uuid4().hex)
            cid = UUID(second['conversation_id'])
            photo = ROOT / 'data/visual/v1/images/normal.png'
            staged = AttachmentService(engine, store).stage('normal.png', photo.read_bytes(), uuid4().hex, conversation_id=cid)
            service = ConversationService(engine, store)
            current = service.detail(cid)['conversation']
            appended = service.append(cid, AppendMessage(expected_version=current['row_version'],
                body='Here is the lamp photo for my replacement request. Please check my order 999-7100006-8100000. '
                    'My synthetic contact is phase11-sensitive@example.invalid.',
                attachments=[{'attachment_id': staged['attachment_id']}]), uuid4().hex)
            proof = execute(engine, store, settings, observer, appended['run_id'])
            proof['image_source'] = 'data/visual/v1/images/normal.png (AI synthetic)'
            report['runs'].append(proof)
        report['text_multi_tool'] = len(report['runs'][0]['tools']) >= 2
        report['actual_image_request'] = any(row['image_views'] > 0 for row in report['runs'][1]['model_calls'])
        report['observation_pass'] = (all(item['observation_pass'] for item in report['runs'])
            and report['text_multi_tool'] and report['actual_image_request'])
    finally:
        observer.close()
        engine.dispose()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str) + '\n', encoding='utf-8')
    print(json.dumps({'observation_pass': report['observation_pass'],
        'runs': [{'run_id': row['run_id'], 'export_status': row['export']['export_status'],
            'model_calls': len(row['model_calls']), 'tools': len(row['tools'])} for row in report['runs']]}))
    return 0 if report['observation_pass'] else 1


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as error:
        # Provider and database exceptions may contain private connection details.
        print(json.dumps({'status': 'failed', 'error_type': type(error).__name__}), file=sys.stderr)
        sys.exit(1)
