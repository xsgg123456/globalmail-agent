"""Explicit human revisions invalidate in-flight work and never resume automation."""
import json
from typing import Literal
from uuid import UUID, uuid4
import sqlalchemy as sa
from pydantic import Field, model_validator
from globalmail_agent.domain.conversation import Command
from globalmail_agent.adapters.attachment_schema import message_attachments, visual_evidence
from globalmail_agent.adapters.body_store import read_bytes
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.application.conversation_base import ServiceBase
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.application.task_queue import invalidate
from globalmail_agent.application.event_store import append_ui_event
from globalmail_agent.attachments.queries import authorize_attachment
from globalmail_agent.attachments.evidence import scoped
from globalmail_agent.knowledge.base import canonical


class EvidenceCommand(Command):
    expected_input_revision: int = Field(ge=0)
    evidence_revision: int = Field(ge=0)


class Correction(EvidenceCommand):
    kind: Literal["field_candidate", "observation", "hypothesis"]
    field_key: Literal["order_number", "sku", "model", "error_code", "other"] = "other"
    value: str = Field(min_length=1, max_length=2000)
    reason: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def field_limit(self):
        if self.kind == "field_candidate" and len(self.value) > (100 if self.field_key == "order_number" else 500):
            raise ValueError("field_candidate_too_long")
        return self


class EvidenceService(ServiceBase):
    def mutate(self, attachment_id, command, key, revoke=False):
        def action(conn, writer):
            owner = conn.execute(sa.select(message_attachments.c.conversation_id).where(
                message_attachments.c.id == attachment_id, message_attachments.c.workspace_id == self.workspace_id)).scalar_one_or_none()
            if owner is None:
                raise ServiceError("attachment_not_found", 404)
            conv = self.lock(conn, owner, command.expected_version)
            attachment = authorize_attachment(conn, conv, attachment_id, lock=True)
            if conv["mode"] != "simulation":
                raise ServiceError("historical_evidence_read_only")
            if conv["input_revision"] != command.expected_input_revision:
                raise ServiceError("stale_input_revision")
            if attachment["evidence_epoch"] != command.evidence_revision:
                raise ServiceError("stale_evidence_revision")
            if not revoke and conv["processing_owner"] not in {"human_review", "human_wait_customer"}:
                raise ServiceError("manual_takeover_required")
            if not revoke and attachment["source_object_id"] is None:
                raise ServiceError("attachment_bytes_unavailable", 422)
            if not revoke and (not command.value.strip() or not command.reason.strip()):
                raise ServiceError("correction_content_required", 422)
            epoch = attachment["evidence_epoch"] + 1
            if not revoke:
                previous = list(conn.execute(sa.select(visual_evidence).where(*scoped(visual_evidence, conv),
                    visual_evidence.c.attachment_id == attachment_id,
                    visual_evidence.c.evidence_epoch == attachment["evidence_epoch"])
                    .order_by(visual_evidence.c.created_at)).mappings())
                # Carry forward human corrections in other columns; inference never overwrites them.
                supersedes = None
                for row in previous:
                    content = json.loads(read_bytes(conn, self.store, conv, row["body_object_id"]))
                    same = row["kind"] == command.kind and (command.kind != "field_candidate"
                        or content.get("key", "other") == command.field_key)
                    if same:
                        supersedes = row["id"]
                    elif row["manual"]:
                        self._revision(conn, writer, conv, attachment, epoch, row["kind"], content, row["id"])
                self._revision(conn, writer, conv, attachment, epoch, command.kind,
                    {"key": command.field_key, "value": command.value, "reason": command.reason,
                     "coverage": "人工核对原图", "quality": "人工修订"}, supersedes)
            invalidate(conn, conv["id"])
            conn.execute(message_attachments.update().where(message_attachments.c.id == attachment_id).values(
                evidence_epoch=epoch, status="revoked" if revoke else "ready", processing_run_id=None))
            self.update(conn, conv, input_revision=conv["input_revision"] + 1, scheduling_state="idle",
                auto_run_gate="disabled" if conv["processing_owner"] != "agent" else "manual_retry_required")
            append_ui_event(conn, conv["id"], "attachment.revoked" if revoke else "attachment.corrected",
                {"attachment_id": str(attachment_id), "evidence_epoch": epoch, "input_revision": conv["input_revision"]})
            return {"conversation_id": str(conv["id"]), "version": conv["row_version"],
                "input_revision": conv["input_revision"], "evidence_epoch": epoch}
        return self.write(key, ("attachment.revoke:" if revoke else "attachment.correct:") + str(attachment_id), command, action)

    @staticmethod
    def _revision(conn, writer, conv, attachment, epoch, kind, value, supersedes):
        source = attachment["source_object_id"]
        body = writer.put(conn, conv, canonical(value).decode(), "manual_image_revision", (source,))
        conn.execute(sa.insert(visual_evidence).values(id=uuid4(), **{k: conv[k] for k in SCOPE_KEYS},
            conversation_id=conv["id"], attachment_id=attachment["id"], message_id=attachment["message_id"],
            revision=epoch, evidence_epoch=epoch, kind=kind, body_object_id=body, manual=True,
            source_sha256=attachment["source_sha256"], location={"type": "full_image"}, supersedes_id=supersedes))
