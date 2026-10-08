"""Read-only business APIs; scene creation accepts no caller-selected scope."""
from uuid import UUID
from fastapi import APIRouter, Header, Query, Request
from globalmail_agent.api.conversations import safe_call
from globalmail_agent.application.business_queries import BusinessQueries
from globalmail_agent.application.fixture_conversations import FixtureConversations
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.application.eligibility import EligibilityService
from globalmail_agent.domain.conversation import Command
from globalmail_agent.domain.policy import EligibilityRequest


def business_router(database, store):
    router = APIRouter(prefix="/api/v1")
    queries = BusinessQueries(database)
    eligibility = EligibilityService(database)

    def fixtures():
        try:
            return FixtureConversations(database, store)
        except (OSError, ValueError, KeyError, TypeError):
            raise ServiceError("fixture_unavailable", 503) from None

    def strict_query(request, names):
        if set(request.query_params) - set(names):
            raise ServiceError("invalid_query_fields", 422)

    def read_call(request, action):
        def checked():
            value = action()
            if value["status"] == "error":
                raise ServiceError(value["reason_code"], 503)
            return value
        return safe_call(request, checked)

    @router.get("/business/scenarios")
    def scenarios(request: Request):
        return safe_call(request, lambda: fixtures().list())

    @router.post("/business/scenarios/{scenario_id}/conversations")
    def create(request: Request, scenario_id: str, command: Command,
               idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: fixtures().create(scenario_id, command, idempotency_key), 202)

    @router.get("/conversations/{conversation_id}/business")
    def detail(request: Request, conversation_id: UUID,
               order_number: str | None = Query(default=None, max_length=100),
               order_line_id: str | None = Query(default=None, max_length=160)):
        def action():
            strict_query(request, ("order_number", "order_line_id"))
            return queries.detail(conversation_id, order_number, order_line_id)
        return read_call(request, action)

    @router.get("/conversations/{conversation_id}/availability")
    def availability(request: Request, conversation_id: UUID,
                     order_line_id: str | None = Query(default=None, max_length=160),
                     item_id: str | None = Query(default=None, max_length=160)):
        def action():
            strict_query(request, ("order_line_id", "item_id"))
            return queries.availability(conversation_id, order_line_id, item_id)
        return read_call(request, action)

    @router.post("/conversations/{conversation_id}/eligibility")
    def preview(request: Request, conversation_id: UUID, command: EligibilityRequest):
        return read_call(request, lambda: eligibility.preview(conversation_id, command))

    return router
