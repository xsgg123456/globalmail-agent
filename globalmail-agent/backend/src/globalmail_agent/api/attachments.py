"""Raw-byte uploads and authorized byte previews; metadata exposes no storage paths."""
from uuid import UUID
from fastapi import APIRouter, Request, Header, Query
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.exc import SQLAlchemyError
from globalmail_agent.api.conversations import safe_call
from globalmail_agent.api.envelope import response
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.attachments.intake import AttachmentService
from globalmail_agent.attachments.queries import AttachmentQueries
from globalmail_agent.attachments.validation import MAX_BYTES


class CancelUpload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expected_version: int = Field(ge=0)


def attachment_router(database, store):
    router = APIRouter(prefix="/api/v1")
    service, queries = AttachmentService(database, store), AttachmentQueries(database, store)

    @router.post("/attachments/uploads")
    async def upload(request: Request, filename: str = Query(min_length=1, max_length=240),
            conversation_id: UUID | None = None, sender_email: str | None = Query(default=None, max_length=320),
            idempotency_key: str = Header(default="")):
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > MAX_BYTES:
                return response(request.state.request_id, status=422, msg="image_too_large")
            content.extend(chunk)
        try:
            return safe_call(request, lambda: service.stage(filename, bytes(content), idempotency_key,
                conversation_id=conversation_id, sender_email=sender_email), 201)
        except (OSError, ValueError):
            return response(request.state.request_id, status=503, msg="attachment_storage_unavailable")

    @router.post("/attachments/{attachment_id}/cancel")
    def cancel(request: Request, attachment_id: UUID, command: CancelUpload):
        return safe_call(request, lambda: service.cancel(attachment_id, command.expected_version))

    @router.get("/attachments/{attachment_id}/preview")
    def preview(request: Request, attachment_id: UUID, conversation_id: UUID, thumbnail: bool = True):
        try:
            content, media_type = queries.preview(attachment_id, conversation_id, thumbnail)
            return Response(content, media_type=media_type, headers={"Cache-Control": "no-store",
                "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"})
        except ServiceError as error:
            return response(request.state.request_id, status=error.status, msg=error.code)
        except SQLAlchemyError:
            return response(request.state.request_id, status=503, msg="database_unavailable")

    @router.get("/conversations/{conversation_id}/attachments")
    def listing(request: Request, conversation_id: UUID):
        return safe_call(request, lambda: queries.listing(conversation_id))

    return router
