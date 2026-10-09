"""Same-ledger read APIs expose current state and legal console actions."""
from uuid import UUID
from fastapi import APIRouter, Query, Request
from globalmail_agent.api.conversations import safe_call
from globalmail_agent.application.after_sales import AfterSalesService
from globalmail_agent.application.conversation_lock import ServiceError


def after_sales_router(database, store):
    router = APIRouter(prefix="/api/v1")
    service = AfterSalesService(database, store)

    def read(request, conversation_id, operation_id=None):
        allowed = {"conversation_id"} if operation_id else set()
        if set(request.query_params) - allowed:
            raise ServiceError("invalid_query_fields", 422)
        value = service.listing(conversation_id, operation_id)
        if value["status"] == "error":
            raise ServiceError(value["reason_code"], 503)
        return value

    @router.get("/conversations/{conversation_id}/operations")
    def listing(request: Request, conversation_id: UUID):
        return safe_call(request, lambda: read(request, conversation_id))

    @router.get("/operations/{operation_id}")
    def detail(request: Request, operation_id: str, conversation_id: UUID = Query()):
        return safe_call(request, lambda: read(request, conversation_id, operation_id))

    return router
