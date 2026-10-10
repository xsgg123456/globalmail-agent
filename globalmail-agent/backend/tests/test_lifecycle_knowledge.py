"""Knowledge source and index deletion on isolated real PostgreSQL."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sqlalchemy as sa
from uuid import uuid4
from index_helpers import IndexFixture
from globalmail_agent.application.lifecycle import LifecycleService
from globalmail_agent.adapters import knowledge_schema as k, knowledge_index_schema as ix


class KnowledgeDeletionTests(IndexFixture):
    def test_replaying_applied_withdraw_does_not_undo_later_legal_republication(self):
        from globalmail_agent.knowledge.index_commands import WithdrawCommand
        did, vid, _ = self.reviewed_markdown('# LEGAL_REPUBLISH\nRetained information.')
        self.publish([self.build(vid)])
        current = self.releases.listing()['head']
        self.releases.withdraw(did, WithdrawCommand(expected_version=1,
            expected_release_epoch=current['epoch']), uuid4().hex)
        record = self.lifecycle.journal.read_verified()[0][0]
        self.publish([self.build(vid)])
        before = self.releases.listing()['head']
        self.assertTrue(self.lifecycle.replay(record)['already_applied'])
        self.assertEqual(self.releases.listing()['head'], before)
        with self.engine.connect() as conn:
            self.assertFalse(conn.execute(sa.select(k.documents.c.withdrawn).where(k.documents.c.id == did)).scalar_one())

    def test_deleting_one_published_document_preserves_other_eligible_release_entry(self):
        did, vid, _ = self.reviewed_markdown('# PRIVATE_DELETE\nOriginal private steps.')
        keep, keep_version, _ = self.reviewed_markdown('# PUBLIC_KEEP\nUnrelated legal information.')
        self.publish([self.build(vid), self.build(keep_version)])
        request = self.lifecycle.request('document', did, self.lifecycle.preview('document', did)['expected_version'])
        with patch('globalmail_agent.observability.purge.PurgeService.purge_runs', return_value=True):
            result = self.lifecycle.process(request['id'])
        self.assertEqual(result['status'], 'completed', result)
        from globalmail_agent.application.restore_checks import freeze_inherited_work, verify_restored_database
        freeze_inherited_work(self.engine)
        verify_restored_database(self.engine, self.store.root)
        from globalmail_agent.knowledge.release_queries import head
        with self.engine.connect() as conn:
            current = head(conn, self.lifecycle.workspace)
            kept = conn.execute(sa.select(ix.knowledge_release_items.c.document_id).where(
                ix.knowledge_release_items.c.release_id == current['release_id'])).scalars().all()
            self.assertEqual(kept, [keep])

    def setUp(self):
        super().setUp()
        self.lifecycle = LifecycleService(self.engine, self.store,
            SimpleNamespace(lifecycle_journal_root=None))

    def test_document_purge_removes_index_cache_and_manifest_body(self):
        did, vid, _ = self.reviewed_markdown("# DELETE_KNOWLEDGE_SENTINEL\nPrivate steps.")
        self.publish([self.build(vid)])
        preview = self.lifecycle.preview("document", did)
        request = self.lifecycle.request("document", did, preview["expected_version"])
        with patch("globalmail_agent.observability.purge.PurgeService.purge_runs", return_value=True):
            result = self.lifecycle.process(request["id"])
        self.assertEqual(result["status"], "completed", result)
        from globalmail_agent.application.restore_checks import verify_restored_database, freeze_inherited_work
        freeze_inherited_work(self.engine)
        verify_restored_database(self.engine, self.store.root)
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(sa.select(sa.func.count()).select_from(ix.index_chunks)).scalar_one(), 0)
            self.assertEqual(conn.execute(sa.select(sa.func.count()).select_from(ix.embedding_cache)).scalar_one(), 0)
            self.assertTrue(all(v == "" for v in conn.execute(sa.select(k.blocks.c.text)).scalars()))
            self.assertNotIn("DELETE_KNOWLEDGE_SENTINEL", str(list(conn.execute(sa.select(ix.knowledge_releases.c.manifest)).scalars())))

    def test_shared_source_blocks_without_deleting_other_original(self):
        did, vid, _ = self.markdown("# Shared private source")
        other, other_version, _ = self.markdown("# Other logical document")
        with self.engine.begin() as conn:
            original = conn.execute(sa.select(k.document_versions.c.object_id).where(k.document_versions.c.id == vid)).scalar_one()
            values = dict(conn.execute(sa.select(k.document_versions).where(k.document_versions.c.id == other_version)).mappings().one())
            conn.execute(k.documents.update().where(k.documents.c.id == other).values(current_version_id=None))
            conn.execute(k.applicabilities.delete().where(k.applicabilities.c.version_id == other_version))
            conn.execute(k.knowledge_audits.delete().where(k.knowledge_audits.c.document_id == other))
            conn.execute(k.document_versions.delete().where(k.document_versions.c.id == other_version))
            values["object_id"] = original
            conn.execute(k.document_versions.insert().values(**values))
        preview = self.lifecycle.preview("document", did)
        self.assertIn(str(other), preview["impact"]["blocked_document_ids"])
        request = self.lifecycle.request("document", did, preview["expected_version"])
        result = self.lifecycle.process(request["id"])
        self.assertEqual(result["status"], "blocked_dependencies")
        self.assertTrue(self.store._path(original).exists())
        with self.engine.connect() as conn:
            self.assertFalse(conn.execute(sa.select(k.documents.c.withdrawn).where(k.documents.c.id == other)).scalar_one())

    def test_replay_withdraw_restores_fence_without_deleting_retained_original(self):
        from globalmail_agent.adapters.lifecycle_schema import journal_receipts, deletion_requests
        did, vid, _ = self.reviewed_markdown()
        self.publish([self.build(vid)])
        self.lifecycle.journal.initialize()
        record = self.lifecycle.journal.append({"request_id": str(uuid4()), "target_type": "document",
            "target_id": str(did), "workspace_id": str(self.lifecycle.workspace), "action": "withdraw"})
        with self.lifecycle.journal.locked():
            result = self.lifecycle.replay(record)
        self.assertEqual(result["status"], "completed")
        self.assertEqual(self.lifecycle.replay(record)["status"], "completed")
        with self.engine.connect() as conn:
            doc = conn.execute(sa.select(k.documents).where(k.documents.c.id == did)).mappings().one()
            self.assertTrue(doc["withdrawn"])
            self.assertEqual(doc["revocation_epoch"], 1)
            self.assertEqual(conn.execute(sa.select(sa.func.count()).select_from(journal_receipts)).scalar_one(), 1)
            self.assertEqual(conn.execute(sa.select(sa.func.count()).select_from(deletion_requests)).scalar_one(), 0)
            original = conn.execute(sa.select(k.document_versions.c.object_id).where(k.document_versions.c.id == vid)).scalar_one()
        self.assertTrue(self.store._path(original).exists())
