"""Knowledge maintenance HTTP boundary; no publication/retrieval/model endpoint."""
from uuid import UUID
from typing import Literal
from fastapi import APIRouter, Request, Header, Query
from fastapi.responses import Response
from sqlalchemy.exc import SQLAlchemyError
from globalmail_agent.api.conversations import safe_call
from globalmail_agent.api.envelope import response
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.commands import Command, CreateDocument, VersionCommand, ParseCommand, ReviewCommand
from globalmail_agent.knowledge.documents import DocumentService
from globalmail_agent.knowledge.queries import KnowledgeQueries
from globalmail_agent.knowledge.queue import KnowledgeQueue
from globalmail_agent.knowledge.review import ReviewService
from globalmail_agent.knowledge.prepared import PreparedImport
from globalmail_agent.knowledge.validation import catalog, MAX_BYTES
from globalmail_agent.knowledge.parser_profiles import profiles


def knowledge_router(database, store):
    router = APIRouter(prefix="/api/v1")
    documents = DocumentService(database, store)
    queries = KnowledgeQueries(database, store)
    queue = KnowledgeQueue(database)
    reviews = ReviewService(database, store)

    @router.get("/knowledge/catalog")
    def catalogue(request: Request):
        return safe_call(request, lambda: {"products": catalog(), "parser_profiles": [
            {k: p[k] for k in ("id", "label", "available")} for p in profiles()]})

    @router.post("/knowledge/uploads")
    async def upload(request: Request, filename: str = Query(max_length=240), expected_version: int = Query(default=0, ge=0),
                     idempotency_key: str = Header(default="")):
        content = bytearray()
        async for chunk in request.stream():
            if len(content) + len(chunk) > MAX_BYTES:
                return response(request.state.request_id, status=422, msg="file_too_large")
            content.extend(chunk)
        return safe_call(request, lambda: documents.upload(filename, bytes(content), idempotency_key, expected_version), 202)

    @router.get("/knowledge/documents")
    def listing(request: Request, type: str | None = None, brand: str | None = None, sku: str | None = None,
                status: str | None = None, cursor: UUID | None = None, limit: int = Query(50, ge=1, le=100),
                publication: Literal["published", "unpublished", "withdrawn"] | None = None):
        return safe_call(request, lambda: queries.listing(type, brand, sku, status, cursor, limit, publication))

    @router.post("/knowledge/documents")
    def create(request: Request, command: CreateDocument, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: documents.create(command, idempotency_key), 202)

    @router.get("/knowledge/documents/{identity}")
    def detail(request: Request, identity: UUID):
        return safe_call(request, lambda: queries.detail(identity))

    @router.post("/knowledge/documents/{identity}/versions")
    def revise(request: Request, identity: UUID, command: VersionCommand, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: documents.revise(identity, command, idempotency_key), 202)

    @router.get("/knowledge/versions/{identity}")
    def version(request: Request, identity: UUID):
        return safe_call(request, lambda: queries.version_detail(identity))

    def file_response(content, media_type, filename=None):
        headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff", "Content-Security-Policy": "sandbox"}
        if filename:
            headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        return Response(content, media_type=media_type, headers=headers)

    @router.get("/knowledge/versions/{identity}/source")
    def source(request: Request, identity: UUID):
        def action():
            content, media_type, fmt = queries.source(identity)
            return file_response(content, media_type, "source." + fmt)
        try:
            return action()
        except ServiceError as error:
            return response(request.state.request_id, status=error.status, msg=error.code)
        except SQLAlchemyError:
            return response(request.state.request_id, status=503, msg="database_unavailable")

    @router.get("/knowledge/assets/{identity}")
    def asset(request: Request, identity: UUID):
        try:
            content, media_type = queries.asset(identity)
            return file_response(content, media_type)
        except ServiceError as error:
            return response(request.state.request_id, status=error.status, msg=error.code)
        except SQLAlchemyError:
            return response(request.state.request_id, status=503, msg="database_unavailable")

    @router.post("/knowledge/versions/{identity}/parse")
    def parse(request: Request, identity: UUID, command: ParseCommand, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: queue.enqueue(identity, command, idempotency_key), 202)

    @router.post("/knowledge/versions/{identity}/review")
    def review(request: Request, identity: UUID, command: ReviewCommand, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: reviews.review(identity, command, idempotency_key))

    @router.get("/jobs/{identity}")
    def job(request: Request, identity: UUID):
        return safe_call(request, lambda: queue.get(identity))

    @router.post("/jobs/{identity}/{action}")
    def control(request: Request, identity: UUID, action: str, command: Command, idempotency_key: str = Header(default="")):
        if action not in {"retry", "cancel"}:
            return response(request.state.request_id, status=404, msg="not_found")
        return safe_call(request, lambda: queue.control(identity, action, command, idempotency_key), 202)

    @router.post("/knowledge/prepared-import")
    def prepared(request: Request, command: Command, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: PreparedImport(database, store).importing(command, idempotency_key), 202)

    return router
