"""Local script/API fact injection; no customer-workbench controls or business executor."""
from uuid import UUID
from fastapi import APIRouter, Header, Request
from globalmail_agent.api.conversations import safe_call
from globalmail_agent.application.branch_facts import BranchFactsService
from globalmail_agent.domain.business_events import BranchFact


def testing_router(database, store):
    router = APIRouter(prefix="/api/v1/testing")
    facts = BranchFactsService(database, store)

    @router.post("/branches/{branch_id}/facts")
    def fact(request: Request, branch_id: UUID, command: BranchFact, idempotency_key: str = Header(default="")):
        return safe_call(request, lambda: facts.event(branch_id, command, idempotency_key))

    return router
