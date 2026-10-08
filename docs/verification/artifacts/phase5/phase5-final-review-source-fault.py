"""Independent reachable object-store fault in disposable PG schema only."""
import json
import time
from uuid import UUID, uuid4
from knowledge_helpers import KnowledgeFixture
from globalmail_agent.worker.knowledge_runner import KnowledgeRunner

fixture = KnowledgeFixture(methodName='runTest')
fixture.setUp()
try:
    jobs = []
    versions = []
    for name in ('broken', 'healthy'):
        _, _, payload = fixture.markdown(content='# ' + name + '\n先断电，输入24 V。')
        payload['title'] = name + '-source-fault'
        created = fixture.post('/knowledge/documents', payload)
        assert created.status_code == 202, created.text
        vid = created.json()['data']['version_id']
        queued = fixture.post('/knowledge/versions/' + vid + '/parse',
                              {'expected_version': 1, 'parser_profile_id': 'markdown'})
        assert queued.status_code == 202, queued.text
        jobs.append(queued.json()['data']['job_id'])
        versions.append(UUID(vid))
    with fixture.engine.connect() as conn:
        from globalmail_agent.knowledge.base import version
        source = version(conn, fixture.docs.workspace_id, versions[0])['object_id']
    path = fixture.store._path(source)
    assert path.parent == fixture.store.root and path.exists()
    path.unlink()
    runner = KnowledgeRunner(fixture.engine, fixture.store, fixture.docs.workspace_id)
    runner.start()
    try:
        time.sleep(1.4)
    finally:
        runner.close()
    for attempt in range(3):
        try:
            runner.jobs.claim('independent_claim_check')
        except Exception as error:
            print(json.dumps({'claim_check': attempt + 1, 'error_code': getattr(error, 'code', type(error).__name__)}))
    detail_response = fixture.client.get('/api/v1/knowledge/versions/' + str(versions[0]))
    print(json.dumps({'broken_detail_http': detail_response.status_code,
                      'error_code': detail_response.json()['msg']}))
    for name, jid, vid in zip(('broken', 'healthy'), jobs, versions):
        response = fixture.client.get('/api/v1/jobs/' + jid)
        assert response.status_code == 200, response.text
        job = response.json()['data']['job']
        with fixture.engine.connect() as conn:
            current = version(conn, fixture.docs.workspace_id, vid)
        print(json.dumps({'document': name, 'job_status': job['status'], 'stage': job['stage'],
                          'error_code': job['error_code'], 'attempt_no': job['attempt_no'],
                          'retryable': job['retryable'], 'version_status': current['status']}))
    cancel = fixture.post('/jobs/' + jobs[0] + '/cancel', {'expected_version': 1})
    assert cancel.status_code == 202, cancel.text
    runner = KnowledgeRunner(fixture.engine, fixture.store, fixture.docs.workspace_id)
    runner.start()
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            healthy = fixture.client.get('/api/v1/jobs/' + jobs[1]).json()['data']['job']
            if healthy['status'] == 'completed':
                break
            time.sleep(.1)
        print(json.dumps({'after_manual_cancel': healthy['status'], 'stage': healthy['stage']}))
    finally:
        runner.close()
finally:
    fixture.doCleanups()
