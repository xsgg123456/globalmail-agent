"""All effects and checkpoint writes hold the same locks until their transaction commits."""
from contextlib import contextmanager
from uuid import uuid4
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import agent_runs, conversations, jobs, processing_cycles
from globalmail_agent.adapters.business_schema import simulation_branches
from globalmail_agent.adapters.knowledge_index_schema import evidence_refs, index_parents, knowledge_release_heads
from globalmail_agent.adapters.knowledge_schema import documents
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.release_queries import head
from globalmail_agent.knowledge.base import scope, sha
from globalmail_agent.worker.leases import db_now, slot_for_update, valid_lease, qualified


def knowledge_guard(conn, workspace, run_id, current):
    context = conn.execute(sa.select(a.agent_run_contexts).where(
        a.agent_run_contexts.c.run_id == run_id)).mappings().first()
    if context is None:
        return
    if context["mode"] == "historical_replay":
        return  # No authorized historical manifest exists yet; simulation evidence is never loaded.
    if (context["release_id"] != current["release_id"] or context["release_epoch"] != current["epoch"]
            or context["profile_id"] != current["profile_id"]):
        raise ServiceError("stale_release")
    deps = conn.execute(sa.select(a.agent_run_dependencies).where(
        a.agent_run_dependencies.c.run_id == run_id, a.agent_run_dependencies.c.active.is_(True))).mappings()
    for dep in deps:
        ref = conn.execute(sa.select(evidence_refs).where(evidence_refs.c.id == dep["reference_id"],
            evidence_refs.c.workspace_id == workspace)).mappings().one()
        doc = conn.execute(sa.select(documents).where(documents.c.id == dep["document_id"],
            documents.c.workspace_id == workspace).with_for_update()).mappings().one()
        parent = conn.execute(sa.select(index_parents).where(
            index_parents.c.id == ref["reference"]["parent_id"])).mappings().one()
        if (doc["withdrawn"] or doc["lifecycle"] != "active" or doc["revocation_epoch"] != dep["revocation_epoch"]
                or ref["release_id"] != context["release_id"] or parent["content_sha256"] != dep["content_hash"]
                or sha(parent["text"].encode()) != dep["content_hash"]
                or not any(binding["sku"] == dep["sku"] for binding in parent["applicability"])):
            raise ServiceError("stale_release")


@contextmanager
def guarded(engine, workspace_id, job, *, checkpoint=False, check_knowledge=True):
    with engine.begin() as conn:
        slot = slot_for_update(conn, workspace_id)
        if not valid_lease(slot, job["id"], job["lease_owner"], job["slot_fence"], db_now(conn)):
            raise ServiceError("lease_expired")
        branch = conn.execute(sa.select(simulation_branches).where(
            simulation_branches.c.conversation_id == job["conversation_id"],
            simulation_branches.c.workspace_id == workspace_id).with_for_update()).mappings().first()
        conv = conn.execute(sa.select(conversations).where(conversations.c.id == job["conversation_id"],
            conversations.c.workspace_id == workspace_id).with_for_update()).mappings().one()
        # An empty scope still needs a lockable head to serialize its first publication.
        conn.execute(pg_insert(knowledge_release_heads).values(id=uuid4(), **scope(workspace_id)).on_conflict_do_nothing())
        current = head(conn, workspace_id, True)
        run = conn.execute(sa.select(agent_runs).where(agent_runs.c.id == job["run_id"],
            agent_runs.c.workspace_id == workspace_id).with_for_update()).mappings().one()
        task = conn.execute(sa.select(jobs).where(jobs.c.id == job["id"]).with_for_update()).mappings().one()
        cycle = conn.execute(sa.select(processing_cycles).where(
            processing_cycles.c.id == job["cycle_id"]).with_for_update()).mappings().one()
        if (not qualified(conv, run) or branch and branch["generation"] != run["branch_generation"]
                or run["status"] not in ({"running", "completed"} if checkpoint else {"running"})
                or task["status"] not in ({"running", "completed"} if checkpoint else {"running"})
                or checkpoint and not run["checkpoint_writable"]):
            raise ServiceError("run_superseded")
        if check_knowledge:
            knowledge_guard(conn, workspace_id, run["id"], current)
        yield conn, dict(conv), dict(run), dict(cycle)
