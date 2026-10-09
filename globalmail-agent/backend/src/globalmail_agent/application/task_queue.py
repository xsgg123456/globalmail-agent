"""Only effective inputs create cycles. Retrying is owned by the worker service."""
from uuid import UUID, uuid4
from sqlalchemy import insert, select, update, func
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.adapters.conversation_schema import (
    conversations, processing_cycles, agent_runs, jobs, domain_events, agent_slots)


def invalidate(conn, conversation_id):
    for before, after in (("queued", "cancelled"), ("running", "superseded")):
        ids = list(conn.execute(select(agent_runs.c.id).where(
            agent_runs.c.conversation_id == conversation_id, agent_runs.c.status == before)).scalars())
        if not ids:
            continue
        conn.execute(update(agent_runs).where(agent_runs.c.id.in_(ids)).values(status=after,
            checkpoint_writable=False, finished_at=func.now(), updated_at=func.now()))
        conn.execute(update(jobs).where(jobs.c.run_id.in_(ids)).values(status=after, updated_at=func.now()))
        from globalmail_agent.attachments.lifecycle import interrupt_images
        interrupt_images(conn, ids)
        affected_jobs = select(jobs.c.id).where(jobs.c.run_id.in_(ids))
        conn.execute(update(agent_slots).where(agent_slots.c.job_id.in_(affected_jobs))
            .values(lease_owner=None, lease_expires_at=None, job_id=None,
                    fence=agent_slots.c.fence + 1, updated_at=func.now()))
        cycle_ids = select(agent_runs.c.processing_cycle_id).where(agent_runs.c.id.in_(ids))
        conn.execute(update(processing_cycles).where(processing_cycles.c.id.in_(cycle_ids))
                     .values(state="superseded", updated_at=func.now()))


def enqueue(conn, conversation, event):
    existing = conn.execute(select(processing_cycles).where(
        processing_cycles.c.conversation_id == conversation["id"],
        processing_cycles.c.trigger_id == event["id"])).mappings().first()
    if existing:
        run = conn.execute(select(agent_runs).where(agent_runs.c.processing_cycle_id == existing["id"])
                           .order_by(agent_runs.c.attempt_no.desc())).mappings().first()
        job = conn.execute(select(jobs).where(jobs.c.run_id == run["id"])).mappings().one()
        return {"processing_cycle_id": str(existing["id"]), "run_id": str(run["id"]), "job_id": str(job["id"])}
    scope = {k: conversation[k] for k in SCOPE_KEYS}
    cycle, run, job = uuid4(), uuid4(), uuid4()
    revisions = {k: conversation[k] for k in ("input_revision", "authority_epoch", "branch_generation")}
    conn.execute(insert(processing_cycles).values(id=cycle, **scope, **revisions,
        conversation_id=conversation["id"], trigger_id=event["id"],
        trigger_message_id=UUID(str(event["payload"]["message_id"])), state="queued"))
    conn.execute(insert(agent_runs).values(id=run, **scope, **revisions, conversation_id=conversation["id"],
        processing_cycle_id=cycle, attempt_no=1, status="queued", trigger_id=event["id"]))
    conn.execute(insert(jobs).values(id=job, **scope, conversation_id=conversation["id"],
        run_id=run, cycle_id=cycle, kind="agent", status="queued", attempt_no=1))
    conn.execute(update(conversations).where(conversations.c.id == conversation["id"])
                 .values(scheduling_state="queued", updated_at=func.now()))
    return {"processing_cycle_id": str(cycle), "run_id": str(run), "job_id": str(job)}
