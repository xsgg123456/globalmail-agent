"""Disposable PG/HTTP image staging, scope guards and model-free acceptance."""
from pathlib import Path
from uuid import UUID, uuid4
from unittest.mock import Mock
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from globalmail_agent.adapters.attachment_schema import message_attachments
from globalmail_agent.adapters.conversation_schema import conversations, messages, jobs
from globalmail_agent.adapters.schema import objects, content_dependencies
from globalmail_agent.api.attachments import attachment_router
from globalmail_agent.attachments.intake import AttachmentService
from globalmail_agent.attachments.queries import AttachmentQueries
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.domain.conversation import CreateConversation
from globalmail_agent.main import create_app
from globalmail_agent.settings import Settings
from test_protocol import ProtocolFixture
from test_attachment_validation import image_bytes


class AttachmentFixture(ProtocolFixture):
    def setUp(self):
        super().setUp()
        self.store = self.service.store
        self.intake = AttachmentService(self.engine, self.store)
        self.images = AttachmentQueries(self.engine, self.store)
        self.model = Mock()
        app = create_app(Settings(object_root=Path(self.temp.name)), engine=self.engine,
            start_worker=False, model_provider=self.model)
        if not any(getattr(route, "path", None) == "/api/v1/attachments/uploads" for route in app.routes):
            app.include_router(attachment_router(self.engine, self.store))
        self.client = TestClient(app, base_url="http://127.0.0.1:18080")
        self.addCleanup(self.client.close)
        self.headers = {"Origin": "http://127.0.0.1:15173"}

    def stage(self, cid=None, email=None, content=None, filename="photo.png", key=None):
        return self.intake.stage(filename, content if content is not None else image_bytes(), key or uuid4().hex,
            conversation_id=cid, sender_email=email)

    def post(self, path, payload, key=None):
        return self.client.post("/api/v1" + path, json=payload,
            headers={**self.headers, "Idempotency-Key": key or uuid4().hex})

    def upload(self, cid=None, email=None, content=None, filename="photo.png", key=None):
        target = {"filename": filename}
        target.update(conversation_id=str(cid)) if cid is not None else target.update(sender_email=email)
        return self.client.post("/api/v1/attachments/uploads", params=target, content=content or image_bytes(),
            headers={**self.headers, "Idempotency-Key": key or uuid4().hex, "Content-Type": "application/octet-stream"})


class AttachmentIntakeTests(AttachmentFixture):
    def test_new_email_stage_is_hidden_model_free_and_same_email_mail_reuses_scope(self):
        uploaded = self.upload(email=" A.b+tag@Example.TEST ")
        self.assertEqual(uploaded.status_code, 201, uploaded.text)
        data = uploaded.json()["data"]
        cid = UUID(data["conversation_id"])
        self.assertEqual(self.count(messages), 0)
        self.assertEqual(self.count(jobs), 0)
        self.assertEqual(self.count(objects), 2)
        self.assertEqual(self.count(content_dependencies), 1)
        self.assertEqual(self.service.list()["items"], [])
        self.assertEqual(self.conversation(cid)["input_revision"], 0)
        self.assertEqual(self.conversation(cid)["row_version"], 1)
        self.assertFalse(self.model.mock_calls)
        received = self.post("/conversations", {"expected_version": 0, "sender_email": "A.b+tag@example.test",
            "body": "", "attachments": [{"attachment_id": data["attachment_id"], "cid": "label@inline"}]})
        self.assertEqual(received.status_code, 202, received.text)
        self.assertEqual(received.json()["data"]["conversation_id"], str(cid))
        listed = self.images.listing(cid)["items"]
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["cid"], "label@inline")
        self.assertEqual(self.conversation(cid)["input_revision"], 1)
        self.assertFalse(self.model.mock_calls)
        self.assertFalse(any("path" in k or "url" in k or "object_id" in k for k in data))

    def test_idempotent_upload_and_concurrent_first_uploads_converge_without_messages(self):
        key = uuid4().hex
        first = self.stage(email="one@example.test", key=key)
        self.assertEqual(first, self.stage(email="one@example.test", key=key))
        with self.assertRaises(ServiceError) as caught:
            self.stage(email="other@example.test", key=key)
        self.assertEqual(caught.exception.code, "idempotency_conflict")
        with ThreadPoolExecutor(2) as executor:
            results = list(executor.map(lambda _: self.stage(email="parallel@example.test"), range(2)))
        self.assertEqual(results[0]["conversation_id"], results[1]["conversation_id"])
        self.assertEqual(self.count(conversations), 2)
        self.assertEqual(self.count(messages), 0)

    def test_existing_upload_preserves_version_and_preview_enforces_scope_and_integrity(self):
        cid, _ = self.create()
        before = self.conversation(cid)
        data = self.stage(cid)
        self.assertEqual(self.conversation(cid), before)
        aid = UUID(data["attachment_id"])
        source = self.client.get(f"/api/v1/attachments/{aid}/preview", params={"conversation_id": str(cid), "thumbnail": "false"})
        self.assertEqual(source.status_code, 200, source.text)
        self.assertEqual(source.content, image_bytes())
        self.assertEqual(source.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(source.headers["Cache-Control"], "no-store")
        thumbnail = self.client.get(f"/api/v1/attachments/{aid}/preview", params={"conversation_id": str(cid)})
        self.assertEqual(thumbnail.headers["Content-Type"], "image/jpeg")
        other, _ = self.create("other@example.test")
        rejected = self.client.get(f"/api/v1/attachments/{aid}/preview", params={"conversation_id": str(other)})
        self.assertEqual(rejected.status_code, 404)
        with self.engine.connect() as conn:
            row = conn.execute(select(message_attachments).where(message_attachments.c.id == aid)).mappings().one()
        self.store._path(row["source_object_id"]).write_bytes(b"corrupt")
        broken = self.client.get(f"/api/v1/attachments/{aid}/preview", params={"conversation_id": str(cid), "thumbnail": "false"})
        self.assertEqual(broken.status_code, 503)
        self.assertEqual(broken.json()["msg"], "attachment_integrity_error")

    def test_http_stream_limit_and_target_validation_leave_no_objects(self):
        for payload in ({"filename": "x.png"}, {"filename": "x.png", "sender_email": "bad"}):
            response = self.client.post("/api/v1/attachments/uploads", params=payload, content=image_bytes(),
                headers={**self.headers, "Idempotency-Key": uuid4().hex, "Content-Type": "application/octet-stream"})
            self.assertEqual(response.status_code, 422)
        oversized = self.upload(email="x@example.test", content=b"x" * (10 * 1024 * 1024 + 1))
        self.assertEqual(oversized.status_code, 422)
        self.assertEqual(oversized.json()["msg"], "image_too_large")
        self.assertEqual(self.count(objects), 0)
        self.assertEqual(self.count(conversations), 0)
