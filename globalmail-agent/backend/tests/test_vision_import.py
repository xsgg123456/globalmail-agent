"""Controlled images and absent metadata preserve per-message historical visibility."""
import hashlib
import json
from pathlib import Path
from uuid import UUID, uuid4
from vision_fixture import VisionFixture
from test_attachment_validation import image_bytes
from globalmail_agent.adapters.fixture_loader import FixturePackage
from globalmail_agent.application.fixture_conversations import FixtureConversations
from globalmail_agent.domain.conversation import Command, AppendMessage, ImportCase
from globalmail_agent.agent.context import load_context
from globalmail_agent.attachments.importing import package_bytes
from globalmail_agent.application.conversation_lock import ServiceError


class VisionImportTests(VisionFixture):
    def test_known_missing_case_metadata_is_visible_unread_and_cannot_be_used_as_image_input(self):
        cid, _ = self.scene("SCN-020")
        images = self.images.listing(cid)["items"]
        self.assertEqual([(r["filename"], r["status"]) for r in images], [("missing-part.jpg", "missing")])
        job, context, budget, gateway = self.components()
        self.assertEqual(len(context.payload["unread_attachments"]), 1)
        from globalmail_agent.attachments.views import prepare_authorized_image_views
        self.assertEqual(prepare_authorized_image_views(self.engine, self.store, context, job), [])
        self.assertEqual(self.budget_row(job)["image_views"], 0)
        self.assertEqual(self.outbound(cid), [])

    def test_public_metadata_is_atomic_idempotent_and_no_bytes_do_not_allow_image_only_mail(self):
        cid, _ = self.create()
        command = AppendMessage(expected_version=self.conversation(cid)["row_version"], body="Photo unavailable",
            attachment_metadata=[{"filename": "x.png", "mime_type": "image/png", "cid": "inline-one"},
                {"filename": "video.mp4", "mime_type": "video/mp4"}], source_message_id="metadata-mail")
        first = self.service.append(cid, command, uuid4().hex)
        again = command.model_copy(update={"expected_version": self.conversation(cid)["row_version"]})
        self.assertEqual(self.service.append(cid, again, uuid4().hex)["message_id"], first["message_id"])
        rows = self.images.listing(cid)["items"]
        self.assertEqual([r["status"] for r in rows], ["missing", "unsupported"])
        from pydantic import ValidationError
        with self.assertRaises(ValidationError):
            AppendMessage(expected_version=1, body="", attachment_metadata=[{"filename": "x.png"}])
        with self.assertRaises(ValidationError):
            AppendMessage(expected_version=1, body="body", attachment_metadata=[{"filename": "x.png", "url": "http://invalid"}])

    def test_controlled_package_hash_verified_bytes_bind_and_bad_path_is_rejected(self):
        package = FixturePackage()
        directory = Path(self.temp.name) / "package" / "attachments"
        directory.mkdir(parents=True)
        content = image_bytes()
        (directory / "photo.png").write_bytes(content)
        manifest = {"controlled-one": {"path": "photo.png", "sha256": hashlib.sha256(content).hexdigest()}}
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        package.root = directory.parent
        scenario = package.scenarios["BASE-OUTON-01"]
        scenario["initial_messages"][0]["attachments"] = [{"filename": "photo.png", "content_id": "controlled-one", "cid": "inline-photo"}]
        result = FixtureConversations(self.engine, self.store, package).create("BASE-OUTON-01", Command(expected_version=0), uuid4().hex)
        cid = UUID(result["conversation_id"])
        row = self.images.listing(cid)["items"][0]
        self.assertEqual(row["status"], "ready")
        self.assertEqual(self.images.preview(UUID(row["attachment_id"]), cid, False)[0], content)
        manifest["controlled-one"]["path"] = "../private.png"
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        self.assert_error("fixture_attachment_path_denied", lambda: package_bytes(package, "controlled-one"))

    def test_historical_import_hides_future_metadata_until_actual_customer_prefix(self):
        result = self.service.import_case(ImportCase(expected_version=0, source_ref="approved-history", source_conversation_id="image-history",
            split="dev", messages=[{"source_message_id": "first", "sender": "customer", "sent_at": "2026-10-01T10:00:00Z", "body": "Initial text"},
                {"source_message_id": "future", "sender": "customer", "sent_at": "2026-10-02T10:00:00Z", "body": "Later photo",
                 "attachment_metadata": [{"filename": "future.png", "mime_type": "image/png"}]}]), uuid4().hex)
        cid = UUID(result["conversation_id"])
        self.assertEqual(self.images.listing(cid)["items"], [])
        job = self.claimed()
        context = load_context(self.engine, self.store, self.service.workspace_id, job)
        self.assertEqual(context.payload["attachments"], [])
