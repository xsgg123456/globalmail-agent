"""Message/attachment atomicity, immutable ordering, CID uniqueness and visible prefixes."""
from uuid import UUID, uuid4
from datetime import datetime, timedelta, timezone
from sqlalchemy import select, update
from globalmail_agent.adapters.attachment_schema import message_attachments
from globalmail_agent.adapters.conversation_schema import conversations, messages, jobs
from globalmail_agent.adapters.schema import objects
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.domain.conversation import AppendMessage, Takeover
from test_attachment_intake import AttachmentFixture
from test_attachment_validation import image_bytes


class AttachmentBindingTests(AttachmentFixture):
    def test_all_four_images_bind_in_client_order_and_retry_does_not_duplicate(self):
        cid, _ = self.create()
        rows = [self.stage(cid) for _ in range(4)]
        refs = [{"attachment_id": r["attachment_id"], "cid": "inline-" + str(i)} for i, r in enumerate(reversed(rows))]
        version = self.conversation(cid)["row_version"]
        command = AppendMessage(expected_version=version, body="", attachments=refs, source_message_id="photo-mail")
        key = uuid4().hex
        result = self.service.append(cid, command, key)
        self.assertEqual(result, self.service.append(cid, command, key))
        listed = self.images.listing(cid)["items"]
        self.assertEqual([r["attachment_id"] for r in listed], [r["attachment_id"] for r in refs])
        self.assertEqual([r["position"] for r in listed], list(range(4)))
        current = self.conversation(cid)["row_version"]
        retry = AppendMessage(expected_version=current, body="", attachments=refs, source_message_id="photo-mail")
        same = self.service.append(cid, retry, uuid4().hex)
        self.assertEqual(result["message_id"], same["message_id"])
        with self.assertRaises(ServiceError) as caught:
            self.service.append(cid, AppendMessage(expected_version=current, body="", attachments=list(reversed(refs)),
                source_message_id="photo-mail"), uuid4().hex)
        self.assertEqual(caught.exception.code, "source_message_conflict")
        with self.engine.connect() as conn:
            stored = conn.execute(select(message_attachments).where(message_attachments.c.conversation_id == cid)).mappings().all()
        self.assertTrue(all(r["manifest"]["message_id"] == result["message_id"] for r in stored))

    def test_cross_customer_expired_and_cancelled_bind_roll_back_message_and_body(self):
        cid, _ = self.create()
        other, _ = self.create("other@example.test")
        alien = self.stage(other)
        expired = self.stage(cid)
        cancelled = self.stage(cid)
        self.intake.cancel(UUID(cancelled["attachment_id"]))
        with self.engine.begin() as conn:
            conn.execute(update(message_attachments).where(message_attachments.c.id == UUID(expired["attachment_id"]))
                .values(expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
        before = self.count(messages), self.count(objects), len(list(self.store.root.iterdir()))
        for row, code in ((alien, "attachment_not_found"), (expired, "attachment_expired"), (cancelled, "attachment_not_ready")):
            with self.assertRaises(ServiceError) as caught:
                self.service.append(cid, AppendMessage(expected_version=self.conversation(cid)["row_version"],
                    body="Image only", attachments=[{"attachment_id": row["attachment_id"]}]), uuid4().hex)
            self.assertEqual(caught.exception.code, code)
            self.assertEqual((self.count(messages), self.count(objects), len(list(self.store.root.iterdir()))), before)
        with self.engine.connect() as conn:
            staged = conn.execute(select(message_attachments).where(message_attachments.c.message_id.is_(None))).mappings().all()
        self.assertEqual(len(staged), 3)

    def test_duplicate_id_cid_and_total_size_limit_are_explicit_and_atomic(self):
        cid, _ = self.create()
        rows = [self.stage(cid) for _ in range(2)]
        attempts = [[{"attachment_id": rows[0]["attachment_id"]}] * 2,
            [{"attachment_id": r["attachment_id"], "cid": "same-inline"} for r in rows]]
        for refs in attempts:
            rejected = self.post(f"/conversations/{cid}/messages", {"expected_version": self.conversation(cid)["row_version"],
                "body": "", "attachments": refs})
            self.assertEqual(rejected.status_code, 422, rejected.text)
            self.assertEqual(rejected.json()["msg"], "duplicate_attachment_reference")
        jpeg = image_bytes("JPEG")
        padded = jpeg + b"\x00" * (7 * 1024 * 1024 - len(jpeg))
        big = [self.stage(cid, content=padded, filename="large.jpg") for _ in range(3)]
        before = self.count(messages), self.count(objects)
        rejected = self.post(f"/conversations/{cid}/messages", {"expected_version": self.conversation(cid)["row_version"],
            "body": "", "attachments": [{"attachment_id": r["attachment_id"]} for r in big]})
        self.assertEqual(rejected.status_code, 422, rejected.text)
        self.assertEqual(rejected.json()["msg"], "attachment_total_size_limit")
        self.assertEqual((self.count(messages), self.count(objects)), before)

    def test_bound_image_cannot_be_rebound_cancelled_or_read_beyond_visible_prefix(self):
        cid, _ = self.create()
        row = self.stage(cid)
        result = self.service.append(cid, AppendMessage(expected_version=self.conversation(cid)["row_version"], body="",
            attachments=[{"attachment_id": row["attachment_id"]}]), uuid4().hex)
        aid = UUID(row["attachment_id"])
        with self.assertRaises(ServiceError) as caught:
            self.intake.cancel(aid)
        self.assertEqual(caught.exception.code, "attachment_already_bound")
        with self.assertRaises(ServiceError) as caught:
            self.service.append(cid, AppendMessage(expected_version=self.conversation(cid)["row_version"], body="",
                attachments=[{"attachment_id": aid}]), uuid4().hex)
        self.assertEqual(caught.exception.code, "attachment_already_bound")
        with self.engine.begin() as conn:
            conn.execute(update(conversations).where(conversations.c.id == cid).values(visible_message_seq=1))
        self.assertEqual(self.images.listing(cid)["items"], [])
        with self.assertRaises(ServiceError) as caught:
            self.images.preview(aid, cid, False)
        self.assertEqual(caught.exception.code, "attachment_not_visible")
        with self.engine.begin() as conn:
            conn.execute(update(conversations).where(conversations.c.id == cid).values(visible_message_seq=2))
            conn.execute(update(message_attachments).where(message_attachments.c.id == aid).values(status="revoked", evidence_epoch=1))
        self.assertEqual(self.images.listing(cid)["items"][0]["status"], "revoked")
        with self.assertRaises(ServiceError) as caught:
            self.images.preview(aid, cid)
        self.assertEqual(caught.exception.code, "attachment_revoked")

    def test_human_review_image_only_mail_is_accepted_without_automatic_model_work(self):
        cid, _ = self.create()
        self.service.takeover(cid, Takeover(
            expected_version=self.conversation(cid)["row_version"]), uuid4().hex)
        row = self.stage(cid)
        jobs_before = self.count(jobs)
        accepted = self.post(f"/conversations/{cid}/messages", {"expected_version": self.conversation(cid)["row_version"],
            "body": "", "attachments": [{"attachment_id": row["attachment_id"]}]})
        self.assertEqual(accepted.status_code, 202, accepted.text)
        self.assertEqual(self.conversation(cid)["processing_owner"], "human_review")
        self.assertEqual(self.count(jobs), jobs_before)
        self.assertFalse(self.model.mock_calls)
