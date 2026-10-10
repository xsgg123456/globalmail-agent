"""Image deletion closes old writers while preserving unrelated source mail."""
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4
from unittest.mock import patch
import sqlalchemy as sa
from vision_fixture import VisionFixture
from globalmail_agent.adapters.attachment_schema import message_attachments
from globalmail_agent.adapters.conversation_schema import agent_runs
from globalmail_agent.application.lifecycle import LifecycleService


class AttachmentDeletionTests(VisionFixture):
    def test_remaining_image_and_conversation_continue_after_related_derived_content_is_deleted(self):
        from vision_fixture import VisionModel, image_output, handoff
        from globalmail_agent.attachments.corrections import EvidenceService, Correction
        from globalmail_agent.attachments.evidence import evidence_listing
        from globalmail_agent.adapters.conversation_schema import conversations
        cid, images = self.image_mail(number=2)
        self.execute(VisionModel(image_output, handoff()))
        other = UUID(images[1]['attachment_id'])
        conv = self.conversation(cid)
        EvidenceService(self.engine, self.service.store).mutate(other, Correction(
            expected_version=conv['row_version'], expected_input_revision=conv['input_revision'],
            evidence_revision=0, kind='observation', value='PRIVATE_OLD_CORRECTION', reason='inspect original'), uuid4().hex)
        store = self.service.store
        service = LifecycleService(self.engine, store,
            SimpleNamespace(lifecycle_journal_root=Path(self.temp.name) / 'journal'))
        identity = UUID(images[0]['attachment_id'])
        request = service.request('attachment', identity, service.preview('attachment', identity)['expected_version'])
        with patch('globalmail_agent.observability.purge.PurgeService.purge_runs', return_value=True):
            self.assertEqual(service.process(request['id'])['status'], 'completed')
        with self.engine.connect() as conn:
            conv = conn.execute(sa.select(conversations).where(conversations.c.id == cid)).mappings().one()
            remaining = evidence_listing(conn, store, conv, other)
            self.assertEqual(remaining['items'], [])
            self.assertIsNone(remaining['coverage'])
        self.service.detail(cid)
        from globalmail_agent.domain.conversation import Takeover, HumanReply
        conv = self.conversation(cid)
        self.service.takeover(cid, Takeover(expected_version=conv['row_version']), uuid4().hex)
        conv = self.conversation(cid)
        self.service.human_reply(cid, HumanReply(expected_version=conv['row_version'],
            expected_input_revision=conv['input_revision'], body='Please send a new detail.'), uuid4().hex)
        self.append_mail(cid, 'New customer message after deletion')
        from globalmail_agent.agent.context import load_context
        from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
        context = load_context(self.engine, store, DEFAULT_WORKSPACE_ID, self.claimed())
        self.assertNotIn('PRIVATE_OLD_CORRECTION', str(context.payload))
        self.assertIn('New customer message after deletion', str(context.payload))

    def test_replay_revoke_is_idempotent_and_retains_local_bytes(self):
        cid, images = self.image_mail()
        store = self.service.store
        service = LifecycleService(self.engine, store,
            SimpleNamespace(lifecycle_journal_root=Path(self.temp.name) / "journal"))
        identity = UUID(images[0]["attachment_id"])
        service.journal.initialize()
        record = service.journal.append({"request_id": str(uuid4()), "target_type": "attachment",
            "target_id": str(identity), "workspace_id": str(service.workspace), "action": "revoke"})
        with service.journal.locked():
            self.assertEqual(service.replay(record)["status"], "completed")
        self.assertEqual(service.replay(record)["status"], "completed")
        with self.engine.connect() as conn:
            row = conn.execute(sa.select(message_attachments).where(message_attachments.c.id == identity)).mappings().one()
        self.assertEqual(row["status"], "revoked")
        self.assertEqual(row["evidence_epoch"], 1)
        self.assertTrue(store._path(row["source_object_id"]).exists())

    def test_attachment_delete_purges_original_and_fences_every_case_run(self):
        cid, images = self.image_mail()
        store = self.service.store
        service = LifecycleService(self.engine, store,
            SimpleNamespace(lifecycle_journal_root=Path(self.temp.name) / "journal"))
        identity = UUID(images[0]["attachment_id"])
        with self.engine.connect() as conn:
            original = conn.execute(sa.select(message_attachments.c.source_object_id)
                .where(message_attachments.c.id == identity)).scalar_one()
        preview = service.preview("attachment", identity)
        request = service.request("attachment", identity, preview["expected_version"])
        with patch("globalmail_agent.observability.purge.PurgeService.purge_runs", return_value=True):
            result = service.process(request["id"])
        self.assertEqual(result["status"], "completed", result)
        self.assertFalse(store._path(original).exists())
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(sa.select(message_attachments.c.status)
                .where(message_attachments.c.id == identity)).scalar_one(), "revoked")
            self.assertFalse(any(conn.execute(sa.select(agent_runs.c.checkpoint_writable)
                .where(agent_runs.c.conversation_id == cid)).scalars()))
