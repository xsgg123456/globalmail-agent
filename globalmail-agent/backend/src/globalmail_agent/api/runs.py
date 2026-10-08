"""Run read/control API; test barriers remain internal service methods."""
from uuid import UUID

from fastapi import APIRouter, Header, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.exc import SQLAlchemyError

from globalmail_agent.api.envelope import response
from globalmail_agent.domain.conversation import Command
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.worker.jobs import JobService


def runs_router(database):
    router = APIRouter(prefix="/api/v1/runs")
    service = JobService(database)

    def handle(request, function, *, status=200):
        try:
            return response(request.state.request_id, jsonable_encoder(function()), status=status)
        except ServiceError as error:
            return response(request.state.request_id, status=error.status, msg=error.code)
        except SQLAlchemyError:
            return response(request.state.request_id, status=503, msg="database_unavailable")

    @router.get("/{run_id}")
    def get(run_id: UUID, request: Request):
        return handle(request, lambda: service.get(run_id))

    @router.post("/{run_id}/stop")
    def stop(run_id: UUID, command: Command, request: Request,
             idempotency_key: str | None = Header(default=None)):
        return handle(request, lambda: service.control(run_id, "stop", command, idempotency_key), status=202)

    @router.post("/{run_id}/retry")
    def retry(run_id: UUID, command: Command, request: Request,
              idempotency_key: str | None = Header(default=None)):
        return handle(request, lambda: service.control(run_id, "retry", command, idempotency_key), status=202)

    return router
