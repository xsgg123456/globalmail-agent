"""Deletion cannot complete while a real worker owns old model input."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Event
from types import SimpleNamespace
from unittest.mock import patch
import sqlalchemy as sa
from agent_fixture import AgentFixture, ScriptedModel, understanding
from globalmail_agent.adapters.schema import objects
from globalmail_agent.adapters.conversation_schema import messages
from globalmail_agent.application.lifecycle import LifecycleService


class WriterDrainTests(AgentFixture):
    def test_inflight_model_drains_before_deleted_content_can_complete(self):
        entered, release = Event(), Event()
        cid, _ = self.create_mail(body='PRIVATE_INFLIGHT_MODEL')
        service = LifecycleService(self.engine, self.store,
            SimpleNamespace(lifecycle_journal_root=Path(self.temp.name) / 'journal'))
        with self.engine.connect() as conn:
            identity = conn.execute(sa.select(messages.c.body_object_id).where(messages.c.conversation_id == cid)).scalar_one()

        def delayed_model(payload):
            entered.set()
            if not release.wait(20):
                raise AssertionError('test_model_release_missing')
            return understanding(payload)

        with ThreadPoolExecutor(max_workers=1) as pool:
            worker = pool.submit(self.execute, ScriptedModel(delayed_model))
            try:
                self.assertTrue(entered.wait(10))
                preview = service.preview('conversation', cid)
                request = service.request('conversation', cid, preview['expected_version'])
                pending = service.process(request['id'])
                self.assertEqual(pending['status'], 'cleanup_failed')
                self.assertEqual(pending['error_code'], 'writer_inflight')
                self.assertTrue(self.store._path(identity).exists())
            finally:
                release.set()
            result, _ = worker.result(timeout=15)
            self.assertIn('error_code', result)
        with patch('globalmail_agent.observability.purge.PurgeService.purge_runs', return_value=True):
            self.assertEqual(service.process(request['id'])['status'], 'completed')
        with self.engine.connect() as conn:
            identities = conn.execute(sa.select(objects.c.id)).scalars().all()
        self.assertTrue(all(not self.store._path(value).exists() for value in identities))
