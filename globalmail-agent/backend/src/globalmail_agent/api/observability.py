"""Private loopback trace entry; GET only reads local scoped receipts."""
from uuid import UUID
from fastapi import APIRouter, Request
from sqlalchemy.exc import SQLAlchemyError
from globalmail_agent.api.envelope import response
from globalmail_agent.application.conversation_lock import ServiceError


def observability_router(records):
    router = APIRouter(prefix="/api/v1/observability")

    @router.get("/runs/{run_id}")
    def get(run_id: UUID, request: Request):
        try:
            return response(request.state.request_id, records.get(run_id))
        except ServiceError as error:
            return response(request.state.request_id, status=error.status, msg=error.code)
        except SQLAlchemyError:
            return response(request.state.request_id, status=503, msg="database_unavailable")

    return router
