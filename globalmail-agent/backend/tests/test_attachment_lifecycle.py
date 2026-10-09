"""Only unbound, unreferenced staged objects can expire or be cancelled."""
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from unittest.mock import patch
from sqlalchemy import select, update
from globalmail_agent.adapters.body_store import BodyWriter
from globalmail_agent.adapters.attachment_schema import message_attachments
from globalmail_agent.adapters.schema import objects, content_dependencies, deletion_journal, SCOPE_KEYS
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.domain.conversation import AppendMessage
from globalmail_agent.attachments.queries import authorize_attachment
from test_attachment_intake import AttachmentFixture


class AttachmentLifecycleTests(AttachmentFixture):
    def test_cancel_is_idempotent_and_cleanup_preserves_bound_and_referenced_sources(self):
        cid, _ = self.create()
        rows = [self.stage(cid) for _ in range(3)]
        aids = [UUID(r["attachment_id"]) for r in rows]
        self.service.append(cid, AppendMessage(expected_version=self.conversation(cid)["row_version"],
            body="", attachments=[{"attachment_id": aids[0]}]), uuid4().hex)
        with self.engine.begin() as conn, BodyWriter(self.store) as writer:
            conversation = self.service.lock(conn, cid)
            sources = conn.execute(select(message_attachments).where(message_attachments.c.id.in_(aids))).mappings().all()
            ids = {r["id"]: r["source_object_id"] for r in sources}
            dependent = writer.put(conn, conversation, "额外有引用的派生内容", "test_dependent", derived_from=(ids[aids[1]],))
            conn.execute(update(message_attachments).where(message_attachments.c.id.in_(aids))
                .values(expires_at=datetime.now(timezone.utc) - timedelta(days=1)))
        first = self.intake.cancel(aids[2])
        self.assertEqual(first, self.intake.cancel(aids[2]))
        removed = self.intake.cleanup_expired()["removed"]
        self.assertEqual(removed, [str(aids[2])])
        self.assertTrue(self.store._path(ids[aids[0]]).exists())
        self.assertTrue(self.store._path(ids[aids[1]]).exists())
        self.assertTrue(self.store._path(dependent).exists())
        self.assertFalse(self.store._path(ids[aids[2]]).exists())
        self.assertEqual(self.intake.cleanup_expired()["removed"], [])
        self.assertEqual(len(self.images.listing(cid)["items"]), 1)

    def test_expired_preview_and_upload_retry_cannot_revive_cancelled_source(self):
        key = uuid4().hex
        row = self.stage(email="preview@example.test", key=key)
        aid, cid = UUID(row["attachment_id"]), UUID(row["conversation_id"])
        with self.engine.begin() as conn:
            conn.execute(update(message_attachments).where(message_attachments.c.id == aid)
                .values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        with self.assertRaises(ServiceError) as caught:
            self.images.preview(aid, cid)
        self.assertEqual(caught.exception.code, "attachment_expired")
        self.intake.cancel(aid)
        with self.assertRaises(ServiceError) as caught:
            self.stage(email="preview@example.test", key=key)
        self.assertEqual(caught.exception.code, "attachment_revoked")
        self.assertEqual(self.count(message_attachments), 1)

    def test_storage_failure_rolls_back_registry_identity_and_disk_files(self):
        original = BodyWriter.put_bytes
        count = 0
        def failed(writer, conn, conversation, content, source, derived_from=()):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("test-only disk full")
            return original(writer, conn, conversation, content, source, derived_from)
        with patch.object(BodyWriter, "put_bytes", failed), self.assertRaises(OSError):
            self.stage(email="rollback@example.test")
        self.assertEqual(self.count(objects), 0)
        self.assertEqual(self.count(message_attachments), 0)
        self.assertEqual(list(self.store.root.iterdir()), [])
        with patch.object(BodyWriter, "put_bytes", side_effect=OSError("PRIVATE_PATH/test-only")):
            response = self.upload(email="rollback-http@example.test")
        self.assertEqual(response.status_code, 503, response.text)
        self.assertEqual(response.json()["msg"], "attachment_storage_unavailable")
        self.assertNotIn("PRIVATE_PATH", response.text)

    def test_deletion_journal_blocks_original_and_thumbnail_reads(self):
        row = self.stage(email="journal@example.test")
        aid, cid = UUID(row["attachment_id"]), UUID(row["conversation_id"])
        with self.engine.begin() as conn:
            conversation = self.service.lock(conn, cid)
            stored = conn.execute(select(message_attachments).where(message_attachments.c.id == aid)).mappings().one()
            conn.execute(deletion_journal.insert().values(id=uuid4(), **{k: conversation[k] for k in SCOPE_KEYS},
                target_object_id=stored["source_object_id"], generation=1, state="revoked"))
        for thumbnail in (False, True):
            with self.assertRaises(ServiceError) as caught:
                self.images.preview(aid, cid, thumbnail)
            self.assertEqual(caught.exception.code, "attachment_revoked")

    def test_all_scope_dimensions_are_rechecked_even_for_a_known_attachment_id(self):
        row = self.stage(email="scope@example.test")
        aid, cid = UUID(row["attachment_id"]), UUID(row["conversation_id"])
        with self.engine.begin() as conn:
            conversation = self.service.lock(conn, cid)
            for key, value in (("workspace_id", uuid4()), ("customer_id", uuid4()), ("branch_id", uuid4()),
                    ("mode", "historical_replay"), ("purpose", "rag")):
                with self.assertRaises(ServiceError) as caught:
                    authorize_attachment(conn, {**conversation, key: value}, aid, allow_staged=True)
                self.assertEqual(caught.exception.code, "attachment_not_found", key)
