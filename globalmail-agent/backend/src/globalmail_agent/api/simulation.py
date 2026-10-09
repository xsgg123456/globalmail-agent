"""Explicit local manual console; no endpoint is registered as an Agent tool."""
from uuid import UUID
from fastapi import APIRouter, Header, Request
from globalmail_agent.api.conversations import safe_call
from globalmail_agent.application.simulation_control import SimulationControlService
from globalmail_agent.domain.executions import SimulationEvent, ExecutionLink
from globalmail_agent.domain.business_events import BranchFact
from globalmail_agent.application.branch_facts import BranchFactsService


def simulation_router(database, store):
    router = APIRouter(prefix="/api/v1/simulation")
    service = SimulationControlService(database, store)
    facts = BranchFactsService(database, store)

    @router.post("/branches/{branch_id}/branch-facts")
    def fact(request: Request, branch_id: UUID, command: BranchFact, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: facts.event(branch_id, command, idempotency_key))

    @router.post("/branches/{branch_id}/events")
    def event(request: Request, branch_id: UUID, command: SimulationEvent, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: service.event(branch_id, command, idempotency_key))

    @router.post("/branches/{branch_id}/execution-links")
    def link(request: Request, branch_id: UUID, command: ExecutionLink, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: service.link(branch_id, command, idempotency_key))

    return router
