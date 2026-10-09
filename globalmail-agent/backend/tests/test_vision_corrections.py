"""Human authority and immediate revocation use actual PG/HTTP and scoped objects."""
import json
from uuid import UUID, uuid4
import sqlalchemy as sa
from vision_fixture import VisionFixture, VisionModel, image_output, handoff
from globalmail_agent.attachments.corrections import EvidenceService, Correction, EvidenceCommand
from globalmail_agent.domain.conversation import HumanReply
from globalmail_agent.adapters.attachment_schema import message_attachments
from globalmail_agent.adapters.conversation_schema import conversations
from globalmail_agent.attachments.evidence import evidence_listing
from globalmail_agent.agent.context import load_context
from globalmail_agent.application.conversation_lock import ServiceError


class VisionCorrectionTests(VisionFixture):
    def test_all_manual_fields_hide_conflicting_automatic_facts_fields_and_source_projection(self):
        from globalmail_agent.attachments.understanding import VisualUnderstanding, apply_manual_corrections, visual_sources
        from agent_fixture import understanding
        for key in ("sku", "model", "error_code", "order_number"):
            with self.subTest(key=key):
                value = VisualUnderstanding.model_validate({**understanding([]), "facts": [{"key": key,
                    "value": "OLD", "kind": "model_inference", "sources": [{"message_id": "image:one", "quote": "OLD"}]}],
                    "images": [{"attachment_id": "one", "status": "understood", "coverage": "整图", "quality": "清晰",
                        "field_candidates": [{"key": key, "raw_text": "OLD", "value": "OLD", "ambiguous_characters": []}],
                        "observations": [], "hypotheses": [], "uncertainties": [], "risk_flags": []}]})
                payload = {"visual_sources": {"manual": {"attachment_id": "one", "kind": "manual_image_correction",
                    "evidence_kind": "field_candidate", "correction": {"key": key, "value": "NEW"}}}}
                effective = apply_manual_corrections(value, payload)
                self.assertEqual([f.value for f in effective.facts], ["NEW"])
                self.assertEqual(effective.images[0].field_candidates, [])
                self.assertNotIn("OLD", visual_sources(effective, [{"attachment_id": "one"}])["image:one"]["body"])

    def test_correction_authority_versions_idempotency_and_later_inference_cannot_replace_manual(self):
        cid, rows = self.image_mail()
        aid = UUID(rows[0]["attachment_id"])
        service = EvidenceService(self.engine, self.store)
        conv = self.conversation(cid)
        command = Correction(expected_version=conv["row_version"], expected_input_revision=conv["input_revision"],
            evidence_revision=0, kind="observation", value="It is a reflection.", reason="原图人工核对")
        self.assert_error("manual_takeover_required", lambda: service.mutate(aid, command, uuid4().hex))
        self.execute(VisionModel(image_output, handoff()))
        conv = self.conversation(cid)
        command = command.model_copy(update={"expected_version": conv["row_version"]})
        key = uuid4().hex
        first = service.mutate(aid, command, key)
        self.assertEqual(first, service.mutate(aid, command, key))
        self.assertIsNone(self.leases.claim("no_automatic_resume"))
        conv = self.conversation(cid)
        self.assert_error("stale_evidence_revision", lambda: service.mutate(aid,
            command.model_copy(update={"expected_version": conv["row_version"], "expected_input_revision": conv["input_revision"]}), uuid4().hex))
        self.service.human_reply(cid, HumanReply(expected_version=conv["row_version"], expected_input_revision=conv["input_revision"],
            body="Please send another angle."), uuid4().hex)
        self.assertIsNone(self.leases.claim("wait_customer_barrier"))
        self.append_mail(cid, "New customer input after human reply")
        model = VisionModel(image_output, handoff())
        result, job = self.execute(model)
        self.assertNotIn("error_code", result, result)
        payload = json.loads(model.requests[1]["messages"][1]["content"])
        self.assertTrue(any(f["value"] == "It is a reflection." and f["kind"] == "human_decision"
            for f in payload["understanding"]["facts"]))
        response = self.client.get(f"/api/v1/conversations/{cid}/visual-evidence", params={"attachment_id": str(aid)})
        self.assertEqual(response.status_code, 200, response.text)
        observations = [r for r in response.json()["data"]["items"] if r["kind"] == "observation"]
        self.assertEqual([(r["manual"], r["value"]) for r in observations], [(True, "It is a reflection.")])

    def test_revoke_redacts_handoff_reason_and_human_reply_derived_from_image(self):
        cid, rows = self.image_mail()
        proposal = handoff()
        proposal["calls"][0]["arguments"] = json.dumps({"reason": "cannot_decide", "summary": "PRIVATE_IMAGE_98122",
            "gaps": ["人工核对"], "draft": ""})
        result, job = self.execute(VisionModel(image_output, proposal))
        self.assertNotIn("error_code", result, result)
        self.assertNotIn("PRIVATE_IMAGE_98122", self.service.detail(cid)["review"]["reason"])
        conv = self.conversation(cid)
        self.service.human_reply(cid, HumanReply(expected_version=conv["row_version"], expected_input_revision=conv["input_revision"],
            body="PRIVATE_HUMAN_IMAGE_98122", note="PRIVATE_NOTE_IMAGE_98122"), uuid4().hex)
        conv = self.conversation(cid)
        EvidenceService(self.engine, self.store).mutate(UUID(rows[0]["attachment_id"]), EvidenceCommand(
            expected_version=conv["row_version"], expected_input_revision=conv["input_revision"], evidence_revision=0), uuid4().hex, revoke=True)
        response = self.client.get(f"/api/v1/conversations/{cid}")
        self.assertEqual(response.status_code, 200, response.text)
        self.assertNotIn("PRIVATE_IMAGE_98122", response.text)
        self.assertNotIn("PRIVATE_HUMAN_IMAGE_98122", response.text)
        self.assertNotIn("PRIVATE_NOTE_IMAGE_98122", response.text)
        record = self.client.get(f"/api/v1/runs/{job['run_id']}")
        self.assertEqual(record.status_code, 410, record.text)

    def test_storage_failure_is_per_image_technical_reason_not_unreadable_quality(self):
        cid, rows = self.image_mail()
        with self.engine.connect() as conn:
            row = conn.execute(sa.select(message_attachments)).mappings().one()
        self.store._path(row["source_object_id"]).write_bytes(b"corrupt")
        model = VisionModel(image_output)
        result, job = self.execute(model)
        self.assertEqual(result["error_code"], "attachment_integrity_error")
        self.assertEqual(len(model.requests), 0)
        image = self.images.listing(cid)["items"][0]
        self.assertEqual(image["status"], "failed")
        self.assertEqual(image["failure_reason"], "attachment_integrity_error")
