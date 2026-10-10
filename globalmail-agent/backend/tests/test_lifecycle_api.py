"""Real HTTP confirmation, body fences and closed recovery in isolated PostgreSQL."""
from pathlib import Path
from uuid import uuid4
import sqlalchemy as sa
from fastapi.testclient import TestClient
from test_protocol import ProtocolFixture
from globalmail_agent.adapters.lifecycle_schema import deletion_requests
from globalmail_agent.main import create_app
from globalmail_agent.settings import Settings
from globalmail_agent.adapters.deletion_journal import DeletionJournal
from globalmail_agent.application.restore import restore_state_path


class LifecycleApiTests(ProtocolFixture):
    def client(self):
        root = Path(self.temp.name)
        settings = Settings(object_root=root, lifecycle_journal_root=root / 'journal')
        client = TestClient(create_app(settings, engine=self.engine, start_worker=False),
            base_url='http://127.0.0.1', headers={'Origin': 'http://127.0.0.1:15173'})
        return client

    def test_preview_cancel_confirm_retry_and_deleted_read(self):
        cid, _ = self.create()
        with self.client() as client:
            impact = client.get(f'/api/v1/lifecycle/conversation/{cid}/impact')
            self.assertEqual(impact.status_code, 200)
            self.assertEqual(self.count(deletion_requests), 0)
            self.assertEqual(client.get(f'/api/v1/conversations/{cid}').status_code, 200)
            version = impact.json()['data']['expected_version']
            stale = client.post(f'/api/v1/lifecycle/conversation/{cid}', json={'expected_version': version+1})
            self.assertEqual(stale.status_code, 409)
            self.assertEqual(self.count(deletion_requests), 0)
            created = client.post(f'/api/v1/lifecycle/conversation/{cid}', json={'expected_version': version})
            self.assertEqual(created.status_code, 202, created.text)
            identity = created.json()['data']['id']
            self.assertEqual(client.get(f'/api/v1/conversations/{cid}').status_code, 404)
            completed = client.post(f'/api/v1/lifecycle/requests/{identity}/retry', json={})
            self.assertEqual(completed.json()['data']['status'], 'completed', completed.text)
            self.assertEqual(client.get('/api/v1/lifecycle/requests').json()['data']['items'][0]['id'], identity)

    def test_uncommitted_external_tombstone_closes_http(self):
        cid, _ = self.create()
        root = Path(self.temp.name)
        journal = DeletionJournal(root / 'journal')
        journal.initialize()
        journal.append({'action':'delete','target_type':'conversation','target_id':str(cid),
            'workspace_id':'00000000-0000-0000-0000-000000000001','request_id':str(uuid4())})
        with self.client() as client:
            self.assertEqual(client.get('/api/v1/health/live').status_code, 200)
            self.assertEqual(client.get('/api/v1/conversations').status_code, 503)
            self.assertEqual(client.get('/api/v1/health/ready').status_code, 503)

    def test_restore_marker_blocks_reads_and_writes(self):
        cid, _ = self.create()
        marker = restore_state_path(Path(self.temp.name))
        self.addCleanup(marker.unlink, missing_ok=True)
        marker.write_text('{"status":"closed"}', encoding='utf-8')
        with self.client() as client:
            self.assertEqual(client.get(f'/api/v1/conversations/{cid}').status_code, 503)
            self.assertEqual(client.post(f'/api/v1/lifecycle/conversation/{cid}', json={'expected_version':1}).status_code, 503)
