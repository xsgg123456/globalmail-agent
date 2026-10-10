"""Real persisted browser invalidation and automatic cleanup without model calls."""
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4
from unittest.mock import patch
import time
import sqlalchemy as sa
from vision_fixture import VisionFixture
from globalmail_agent.application.lifecycle import LifecycleService
from globalmail_agent.adapters.conversation_schema import ui_events
from globalmail_agent.domain.conversation import Takeover, ReviewDraft
from globalmail_agent.worker.cleanup_runner import CleanupRunner


class ContentInvalidationTests(VisionFixture):
    def lifecycle(self):
        return LifecycleService(self.engine, self.service.store,
            SimpleNamespace(lifecycle_journal_root=Path(self.temp.name) / 'journal'))

    def test_revoked_review_hidden_before_purge_watermark_and_event_survive_completion(self):
        cid, images = self.image_mail()
        other, _ = self.image_mail()
        self.service.takeover(cid, Takeover(expected_version=self.conversation(cid)['row_version']), uuid4().hex)
        review = self.service.detail(cid)['review']
        self.service.save_review(review['id'], ReviewDraft(expected_version=review['version'],
            expected_input_revision=self.conversation(cid)['input_revision'],
            draft='PRIVATE_IMAGE_DRAFT', note='PRIVATE_IMAGE_NOTE'), uuid4().hex)
        self.assertIn('PRIVATE_IMAGE_DRAFT', str(self.service.detail(cid)))
        lifecycle = self.lifecycle()
        image_id = UUID(images[0]['attachment_id'])
        preview = lifecycle.preview('attachment', image_id)
        self.assertEqual(preview['impact']['conversation_ids'], [str(cid)])
        request = lifecycle.request('attachment', image_id, preview['expected_version'])
        self.assertEqual(request['status'], 'revoked')
        self.assertGreater(request['journal_seq'], 0)
        detail = self.service.detail(cid)
        self.assertIsNone(detail['review'])
        self.assertNotIn('PRIVATE_IMAGE', str(detail))
        self.assertEqual(detail['conversation']['content_revision'], request['journal_seq'])
        self.assertEqual(self.service.detail(other)['conversation']['content_revision'], 0)
        with patch('globalmail_agent.observability.purge.PurgeService.purge_runs', return_value=True):
            self.assertEqual(lifecycle.process(request['id'])['status'], 'completed')
        with self.engine.connect() as conn:
            event = conn.execute(sa.select(ui_events).where(ui_events.c.conversation_id == cid,
                ui_events.c.kind == 'content.revoked')).mappings().one()
            self.assertEqual(event['payload'], {})
            self.assertEqual(event['conversation_id'], cid)
        listing = self.service.list()['items']
        self.assertEqual(next(row for row in listing if row['id'] == cid)['content_revision'], request['journal_seq'])
        self.service.takeover(cid, Takeover(expected_version=self.conversation(cid)['row_version']), uuid4().hex)
        self.assertIsNotNone(self.service.detail(cid)['review'])

    def test_pending_request_is_completed_by_cleanup_worker(self):
        cid, _ = self.image_mail()
        lifecycle = self.lifecycle()
        request = lifecycle.request('conversation', cid, lifecycle.preview('conversation', cid)['expected_version'])
        runner = CleanupRunner(lifecycle)
        with patch('globalmail_agent.observability.purge.PurgeService.purge_runs', return_value=True):
            runner.start()
            try:
                deadline = time.monotonic() + 10
                while time.monotonic() < deadline and lifecycle.get(request['id'])['status'] != 'completed':
                    time.sleep(.1)
                self.assertEqual(lifecycle.get(request['id'])['status'], 'completed')
            finally:
                runner.close()
