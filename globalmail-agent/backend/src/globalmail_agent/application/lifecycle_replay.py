"""Replay ordinary withdrawal/revocation without appending another journal record."""
from uuid import UUID
import sqlalchemy as sa
from globalmail_agent.adapters import knowledge_schema as k, conversation_schema as c, attachment_schema as image
from globalmail_agent.application.lifecycle_revoke import lock_writers
from globalmail_agent.application.task_queue import invalidate
from globalmail_agent.application.conversation_lock import ServiceError


def replay_revocation(service, record):
    identity = UUID(record["target_id"])
    kind, action = record["target_type"], record["action"]
    if (kind, action) not in {("document", "withdraw"), ("attachment", "revoke")}:
        raise ServiceError("invalid_journal_action", 422)
    with service.engine.begin() as conn:
        lock_writers(conn, service.workspace)
        from globalmail_agent.adapters.lifecycle_schema import journal_receipts
        receipt = conn.execute(sa.select(journal_receipts.c.seq).where(
            journal_receipts.c.request_id == UUID(record['request_id']),
            journal_receipts.c.workspace_id == service.workspace)).scalar_one_or_none()
        if receipt is not None:
            if receipt != int(record['seq']):
                raise ServiceError('journal_receipt_mismatch', 503)
            return {'status': 'completed', 'already_applied': True}
        row = service._target_locked(conn, kind, identity)
        if kind == "document" and not row["withdrawn"]:
            from globalmail_agent.knowledge.queue import invalidate_document_jobs
            from globalmail_agent.knowledge.releases import ReleaseService
            from globalmail_agent.knowledge.release_queries import head
            invalidate_document_jobs(conn, service.workspace, row)
            conn.execute(k.documents.update().where(k.documents.c.id == identity).values(withdrawn=True,
                document_fence=k.documents.c.document_fence + 1, revocation_epoch=k.documents.c.revocation_epoch + 1,
                row_version=k.documents.c.row_version + 1))
            releases = ReleaseService(service.engine, service.store, service.workspace)
            current = head(conn, service.workspace)
            if current.get("id"):
                remaining = {key: value for key, value in releases._current(conn, current).items() if key != str(identity)}
                entries, profile = releases._entries(conn, list(remaining.values()), verify_source=False)
                releases._write(conn, current, entries, profile, "withdraw")
        elif kind == "attachment":
            cid = row["conversation_id"]
            invalidate(conn, cid)
            conn.execute(c.agent_runs.update().where(c.agent_runs.c.conversation_id == cid)
                .values(checkpoint_writable=False, stop_requested=True))
            if row["status"] != "revoked":
                conn.execute(image.message_attachments.update().where(image.message_attachments.c.id == identity)
                    .values(status="revoked", evidence_epoch=image.message_attachments.c.evidence_epoch + 1,
                        processing_run_id=None))
                conn.execute(c.conversations.update().where(c.conversations.c.id == cid).values(
                    input_revision=c.conversations.c.input_revision + 1, row_version=c.conversations.c.row_version + 1,
                    auto_run_gate="disabled", scheduling_state="idle"))
        service._receipt(conn, record, record["seq"])
    return {"status": "completed", "action": action, "target_type": kind, "target_id": str(identity)}
