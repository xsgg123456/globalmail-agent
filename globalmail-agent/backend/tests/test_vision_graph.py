"""Real graph/PG/checkpoint integration with controlled actual image bytes."""
import json
from uuid import UUID, uuid4
import sqlalchemy as sa
from vision_fixture import VisionFixture, VisionModel, image_output, handoff
from globalmail_agent.adapters.attachment_schema import message_attachments, visual_analyses, visual_evidence
from globalmail_agent.adapters.agent_schema import understanding_results, usage_records
from globalmail_agent.adapters.body_store import read_body
from globalmail_agent.adapters.checkpoint_repository import CheckpointRepository
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.domain.conversation import Command, Takeover
from globalmail_agent.attachments.corrections import EvidenceService, EvidenceCommand


class VisionGraphTests(VisionFixture):
    def test_revoking_one_joint_image_keeps_other_preview_but_invalidates_shared_evidence(self):
        cid, images = self.image_mail(2)
        result, _ = self.execute(VisionModel(image_output, handoff()))
        self.assertNotIn("error_code", result, result)
        conv = self.conversation(cid)
        EvidenceService(self.engine, self.store).mutate(UUID(images[0]["attachment_id"]), EvidenceCommand(
            expected_version=conv["row_version"], expected_input_revision=conv["input_revision"],
            evidence_revision=0), uuid4().hex, revoke=True)
        second = images[1]["attachment_id"]
        preview = self.client.get(f"/api/v1/attachments/{second}/preview",
            params={"conversation_id": str(cid), "thumbnail": "false"})
        self.assertEqual(preview.status_code, 200, preview.text)
        self.assertTrue(preview.content.startswith(b"\x89PNG"))
        evidence = self.client.get(f"/api/v1/conversations/{cid}/visual-evidence", params={"attachment_id": second})
        self.assertEqual(evidence.status_code, 410, evidence.text)
        self.assertEqual(evidence.json()["msg"], "image_content_revoked")
        self.assertNotIn("visible mark", evidence.text)
        state = self.conversation(cid)
        corrected = self.post(f"/attachments/{second}/corrections", {
            "expected_version": state["row_version"], "expected_input_revision": state["input_revision"],
            "evidence_revision": 0, "kind": "observation", "value": "人工核对本张原图", "reason": "联合分析已失效"})
        self.assertEqual(corrected.status_code, 410, corrected.text)
        self.assertEqual(corrected.json()["msg"], "image_content_revoked")
        self.assertEqual(self.conversation(cid)["row_version"], state["row_version"])
        self.assertEqual(self.images.listing(cid)["items"][1]["evidence_epoch"], 0)
        self.assertEqual(self.conversation(cid)["processing_owner"], "human_review")
        self.assertIsNone(self.leases.claim("no_automatic_resume"))

    def test_joint_request_persists_per_image_evidence_without_binary_checkpoint(self):
        cid, images = self.image_mail(2)
        model = VisionModel(image_output, handoff())
        result, job = self.execute(model)
        self.assertNotIn("error_code", result, result)
        self.assertEqual(self.count(visual_analyses), 1)
        self.assertEqual(self.count(visual_evidence), 4)
        self.assertEqual(len(model.image_requests), 1)
        self.assertEqual(len(model.image_requests[0]["bytes"]), 2)
        self.assertTrue(all(b.startswith(b"\x89PNG") for b in model.image_requests[0]["bytes"]))
        self.assertEqual(self.budget_row(job)["image_views"], 2)
        self.assertEqual(self.budget_row(job)["model_requests"], 2)
        self.assertEqual(self.outbound(cid), [])
        for row in self.images.listing(cid)["items"]:
            self.assertEqual(row["status"], "understood")
        states = list(CheckpointRepository(self.engine, self.service.workspace_id, job, self.store).list(None))
        serialized = json.dumps([s.checkpoint for s in states], default=str)
        self.assertNotIn("base64,", serialized)
        self.assertNotIn("image_url", serialized)
        self.assertTrue(all(i["attachment_id"] in serialized for i in images))
        with self.engine.connect() as conn:
            row = conn.execute(sa.select(message_attachments)).mappings().first()
            self.assertNotIn("analysis_id", row["manifest"])
            self.assertEqual(row["manifest"]["source_sha256"], row["source_sha256"])

    def test_visual_risk_goes_directly_to_atomic_hitl_with_no_second_model(self):
        cid, _ = self.image_mail()
        def risky(messages):
            value = image_output(messages)
            value["images"][0]["risk_flags"] = ["fire"]
            return value
        model = VisionModel(risky)
        result, job = self.execute(model)
        self.assertNotIn("error_code", result, result)
        self.assertEqual(len(model.requests), 1)
        self.assertEqual(self.conversation(cid)["processing_owner"], "human_review")
        self.assertEqual(self.count(understanding_results), 1)
        self.assertEqual(self.count(visual_analyses), 1)
        self.assertEqual(self.service.detail(cid)["active_risks"][0]["kind"], "fire")
        self.assertEqual(self.outbound(cid), [])

    def test_network_retry_charges_views_unknown_usage_and_stops_over_six(self):
        cid, _ = self.image_mail(4)
        model = VisionModel(ServiceError("model_timeout", 503), image_output)
        result, job = self.execute(model)
        self.assertEqual(result["error_code"], "image_view_budget_exceeded")
        row = self.budget_row(job)
        self.assertEqual(row["image_views"], 4)
        self.assertEqual(row["model_requests"], 1)
        self.assertEqual(self.count(visual_analyses), 0)
        self.assertTrue(all(r["status"] == "failed" for r in self.images.listing(cid)["items"]))
        with self.engine.connect() as conn:
            usage = conn.execute(sa.select(usage_records)).mappings().one()
        self.assertEqual(usage["status"], "unknown")
        self.assertGreater(usage["estimated_input"], sum(r["visual_token_upper"] for r in model.image_requests[0]["refs"]))

    def test_stop_takeover_new_input_and_revoke_during_vision_reject_late_output(self):
        for action in ("stop", "takeover", "input", "revoke"):
            with self.subTest(action=action):
                cid, images = self.image_mail()
                def late(messages):
                    conv = self.conversation(cid)
                    if action == "stop":
                        self.controls.control(job["run_id"], "stop", Command(expected_version=conv["row_version"]), uuid4().hex)
                    elif action == "takeover":
                        self.service.takeover(cid, Takeover(expected_version=conv["row_version"]), uuid4().hex)
                    elif action == "input":
                        self.append_mail(cid, "New input while reading image")
                    else:
                        EvidenceService(self.engine, self.store).mutate(UUID(images[0]["attachment_id"]), EvidenceCommand(
                            expected_version=conv["row_version"], expected_input_revision=conv["input_revision"], evidence_revision=0),
                            uuid4().hex, revoke=True)
                    return image_output(messages)
                job = self.claimed()
                result, _ = self.execute(VisionModel(late), job)
                self.assertIn("error_code", result)
                self.assertEqual(self.count(visual_analyses), 0)
                self.assertEqual(self.count(understanding_results), 0)
                self.assertEqual(self.outbound(cid), [])
                self.assertNotEqual(self.images.listing(cid)["items"][-1]["status"], "processing")
                # Finish any replacement queued by the input case before next subcase.
                pending = self.leases.claim("dispose_replacement")
                if pending:
                    self.controls.control(pending["run_id"], "stop", Command(expected_version=self.conversation(cid)["row_version"]), uuid4().hex)

    def test_revoke_blocks_prior_analysis_context_checkpoint_and_preview_immediately(self):
        cid, images = self.image_mail()
        result, job = self.execute(VisionModel(image_output, handoff()))
        self.assertNotIn("error_code", result, result)
        conv = self.conversation(cid)
        with self.engine.connect() as conn:
            analysis = conn.execute(sa.select(visual_analyses)).mappings().one()
        service = EvidenceService(self.engine, self.store)
        service.mutate(UUID(images[0]["attachment_id"]), EvidenceCommand(expected_version=conv["row_version"],
            expected_input_revision=conv["input_revision"], evidence_revision=0), uuid4().hex, revoke=True)
        with self.engine.connect() as conn:
            from globalmail_agent.attachments.revocation import REDACTED
            from globalmail_agent.adapters.conversation_schema import conversations
            raw = conn.execute(sa.select(conversations).where(conversations.c.id == cid)).mappings().one()
            self.assertEqual(read_body(conn, self.store, raw, analysis["body_object_id"]), REDACTED)
        with self.assertRaises(ServiceError) as error:
            list(CheckpointRepository(self.engine, self.service.workspace_id, job, self.store).list(None))
        self.assertEqual(error.exception.code, "image_content_revoked")
        self.assertEqual(self.conversation(cid)["processing_owner"], "human_review")
        self.assertIsNone(self.leases.claim("no_automatic_resume"))
