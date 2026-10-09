from uuid import UUID
from fastapi import APIRouter, Header, Request
from globalmail_agent.api.conversations import safe_call
from globalmail_agent.application.conversation_lock import lock_conversation, ServiceError
from globalmail_agent.attachments.evidence import evidence_listing
from globalmail_agent.attachments.corrections import EvidenceService, Correction, EvidenceCommand


def visual_evidence_router(engine, store):
    router = APIRouter(prefix="/api/v1")
    service = EvidenceService(engine, store)

    @router.get("/conversations/{conversation_id}/visual-evidence")
    def evidence(request: Request, conversation_id: UUID, attachment_id: UUID):
        def action():
            if engine is None:
                raise ServiceError("database_unavailable", 503)
            with engine.begin() as conn:
                conv = lock_conversation(conn, conversation_id)
                return evidence_listing(conn, store, conv, attachment_id)
        return safe_call(request, action)

    @router.post("/attachments/{attachment_id}/corrections")
    def correct(request: Request, attachment_id: UUID, command: Correction, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: service.mutate(attachment_id, command, idempotency_key))

    @router.post("/attachments/{attachment_id}/revoke")
    def revoke(request: Request, attachment_id: UUID, command: EvidenceCommand, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: service.mutate(attachment_id, command, idempotency_key, revoke=True))
    return router
