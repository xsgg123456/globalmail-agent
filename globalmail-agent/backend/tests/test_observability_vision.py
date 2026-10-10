"""Actual authorized image preparation and revocation never export media."""
import json
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from vision_fixture import VisionFixture, VisionModel, image_output, handoff
from test_observability import FakeTransport
from globalmail_agent.observability.sdk_export import SdkExport
from globalmail_agent.observability.service import ObservabilityService
from globalmail_agent.worker.agent_runner import AgentRunner
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
from globalmail_agent.attachments.corrections import EvidenceService, EvidenceCommand
from globalmail_agent.settings import Settings


class VisionObservationTests(VisionFixture):
    def test_actual_media_is_blocked_before_sdk_and_revocation_blocks_pending_export(self):
        settings = Settings(object_root=Path(self.temp.name), langfuse_enabled=True,
            langfuse_public_key="pk-lf-" + uuid4().hex, langfuse_secret_key="image-test-only")
        observer = ObservabilityService(self.engine, self.store, settings, transport=FakeTransport())
        self.addCleanup(observer.close)
        cid, attachments = self.image_mail()
        job, model = self.claimed(), VisionModel(image_output, handoff())
        result = AgentRunner(self.engine, self.store, DEFAULT_WORKSPACE_ID, model, None,
            observability=observer).execute(job)
        self.assertNotIn("error_code", result)
        self.assertEqual(len(model.image_requests[0]["bytes"]), 1)
        trace, value = observer.records.payload(job["run_id"])
        prepared = next(row for row in value["observations"] if row["node"] == "attachment_prepare")
        self.assertEqual(prepared["attachment_ids"], [attachments[0]["attachment_id"]])
        self.assertEqual((prepared["image_count"], prepared["view_count"]), (1, 1))
        transport = SdkExport(settings)
        self.addCleanup(transport.close)
        media = transport.client._resources._media_manager
        with patch.object(media, "_find_and_process_media", wraps=media._find_and_process_media) as traversal:
            spans = transport.build(trace["trace_id"], value)
            self.assertGreater(traversal.call_count, 0)
            self.assertNotIn("data:image", repr(traversal.call_args_list))
            self.assertNotIn("base64", repr(traversal.call_args_list))
        wire = encode_spans(spans).SerializeToString()
        self.assertNotIn(model.image_requests[0]["bytes"][0], wire)
        self.assertNotIn(b"http://", wire)
        self.assertNotIn(b"https://", wire)
        conv = self.conversation(cid)
        EvidenceService(self.engine, self.store).mutate(UUID(attachments[0]["attachment_id"]),
            EvidenceCommand(expected_version=conv["row_version"], expected_input_revision=conv["input_revision"],
                evidence_revision=0), uuid4().hex, revoke=True)
        summary = observer.records.get(job["run_id"])
        self.assertEqual(summary["export_status"], "revoked")
        self.assertIsNone(summary["trace_url"])
        observer.exporter.export_one(job["run_id"])
        self.assertEqual(observer.exporter.transport.payloads, [])
        self.assertEqual(len(model.requests), 2)
