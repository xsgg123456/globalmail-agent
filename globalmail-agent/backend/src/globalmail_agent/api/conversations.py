from uuid import UUID
from fastapi import APIRouter, Header, Query, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import SQLAlchemyError
from globalmail_agent.api.envelope import response
from globalmail_agent.application.conversations import ConversationService
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.domain.conversation import (
    CreateConversation, AppendMessage, ImportCase, Command, Takeover, ReviewDraft, HumanReply, Close)

EXAMPLE = {"expected_version": 0, "source_ref": "synthetic-demo", "source_conversation_id": "lamp-example-01",
    "split": "dev", "identity_verified": False, "messages": [
        {"source_message_id": "mail-01", "sender": "customer", "sent_at": "2026-10-01T08:00:00Z",
         "subject": "Lamp remote control", "body": "The lamp turns on, but the remote does not respond. What should I check?"},
        {"source_message_id": "mail-02", "sender": "historical_staff", "sent_at": "2026-10-01T09:00:00Z",
         "subject": "Re: Lamp remote control", "body": "Please share your order number and confirm whether you replaced the remote batteries."},
        {"source_message_id": "mail-03", "sender": "customer", "sent_at": "2026-10-02T08:00:00Z",
         "subject": "Re: Lamp remote control", "body": "My demo order number is DEMO-1001. I replaced the batteries, and the remote still does not respond."}]}


def safe_call(request, action, status=200):
    try:
        return response(request.state.request_id, jsonable_encoder(action()), status=status)
    except ServiceError as error:
        return response(request.state.request_id, status=error.status, msg=error.code)
    except SQLAlchemyError:
        return response(request.state.request_id, status=503, msg="database_unavailable")


def conversation_router(database, store):
    router = APIRouter(prefix="/api/v1")
    service = ConversationService(database, store)
    from globalmail_agent.application.conversation_advice import ConversationAdvice
    advice = ConversationAdvice(database, store)

    @router.get("/imports/example")
    def example(request: Request):
        return response(request.state.request_id, EXAMPLE)

    @router.get("/conversations")
    def listing(request: Request, mode: str | None = None, limit: int = Query(50, ge=1, le=100),
                cursor: UUID | None = None, state: str | None = None):
        if mode not in {None, "interactive_simulation", "historical_replay"}:
            return response(request.state.request_id, status=422, msg="invalid_mode")
        return safe_call(request, lambda: service.list(mode, limit, cursor, state))

    @router.post("/conversations")
    def create(request: Request, command: CreateConversation, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: service.create(command, idempotency_key), 202)

    @router.post("/imports")
    def importing(request: Request, command: ImportCase, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: service.import_case(command, idempotency_key), 202)

    @router.get("/conversations/{conversation_id}")
    def detail(request: Request, conversation_id: UUID):
        return safe_call(request, lambda: service.detail(conversation_id))

    @router.get("/conversations/{conversation_id}/advice")
    def internal_advice(request: Request, conversation_id: UUID):
        return safe_call(request, lambda: advice.get(conversation_id))

    @router.post("/conversations/{conversation_id}/messages")
    def append(request: Request, conversation_id: UUID, command: AppendMessage,
               idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: service.append(conversation_id, command, idempotency_key), 202)

    @router.post("/conversations/{conversation_id}/replay/next")
    def advance(request: Request, conversation_id: UUID, command: Command,
                idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: service.next(conversation_id, command, idempotency_key), 202)

    @router.post("/conversations/{conversation_id}/takeover")
    def takeover(request: Request, conversation_id: UUID, command: Takeover,
                 idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: service.takeover(conversation_id, command, idempotency_key), 202)

    @router.patch("/human-reviews/{review_id}")
    def draft(request: Request, review_id: UUID, command: ReviewDraft, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: service.save_review(review_id, command, idempotency_key))

    @router.post("/conversations/{conversation_id}/human-replies")
    def reply(request: Request, conversation_id: UUID, command: HumanReply,
              idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: service.human_reply(conversation_id, command, idempotency_key), 202)

    @router.post("/conversations/{conversation_id}/close")
    def close(request: Request, conversation_id: UUID, command: Close, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: service.close(conversation_id, command, idempotency_key), 202)

    return router
