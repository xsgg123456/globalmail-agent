"""A guarded transaction commits one complete outcome per cycle, never stream fragments."""
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.body_store import BodyWriter
from globalmail_agent.adapters.conversation_schema import conversations, agent_runs, jobs, processing_cycles, human_reviews, domain_events
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.agent.guard import guarded
from globalmail_agent.agent.memory import persist_facts
from globalmail_agent.agent.tool_schemas import Draft, Handoff
from globalmail_agent.application.conversation_base import ServiceBase
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.application.event_store import append_ui_event
from globalmail_agent.application.draft_validation import check_draft_sources
from globalmail_agent.application.waits import register_wait, consume_wakes
from globalmail_agent.worker.leases import db_now, slot_for_update, release_slot


def existing_outcome(engine, workspace, job):
    """Unknown commit/replay first reads its original scoped credential without acquiring a new lease."""
    with engine.connect() as conn:
        stored_job = conn.execute(sa.select(jobs).where(jobs.c.id == job["id"],
            jobs.c.workspace_id == workspace, jobs.c.run_id == job["run_id"],
            jobs.c.cycle_id == job["cycle_id"], jobs.c.conversation_id == job["conversation_id"])).mappings().first()
        if stored_job is None:
            raise ServiceError("job_not_found", 404)
        conv = conn.execute(sa.select(conversations).where(conversations.c.id == job["conversation_id"],
            conversations.c.workspace_id == workspace)).mappings().one()
        if conv["lifecycle"] in {"deleting", "deleted"}:
            raise ServiceError("run_not_found", 404)
        prior = conn.execute(sa.select(a.reply_artifacts).where(a.reply_artifacts.c.cycle_id == job["cycle_id"],
            *[a.reply_artifacts.c[k] == conv[k] for k in SCOPE_KEYS])).mappings().first()
        return {"artifact_id": str(prior["id"]), "outcome": prior["outcome"]} if prior else None


def validate_draft(conn, store, context, understanding, draft):
    from globalmail_agent.agent.outcome_validation import check_coverage, draft_hash
    check_coverage(draft)
    validated = conn.execute(sa.select(a.agent_run_contexts.c.validated_draft_hash).where(
        a.agent_run_contexts.c.run_id == context.run_id)).scalar_one()
    if validated != draft_hash(draft.model_dump(mode="json")):
        raise ServiceError("reply_not_validated", 422)
    return check_draft_sources(conn, store, context, understanding, draft)


def commit_outcome(engine, store, context, job, understanding, proposal, *, safety=False):
    prior = existing_outcome(engine, context.workspace_id, job)
    if prior:
        return prior
    handoff = proposal["kind"] == "handoff"
    command = Handoff.model_validate(proposal["data"]) if handoff else Draft.model_validate(proposal["data"])
    with BodyWriter(store) as writer, guarded(engine, context.workspace_id, job,
            check_knowledge=not safety) as (conn, conv, run, cycle):
        previous = conn.execute(sa.select(a.reply_artifacts).where(a.reply_artifacts.c.cycle_id == cycle["id"])).mappings().first()
        if previous:
            return dict(previous)
        if cycle["state"] != "running" or cycle["final_message_id"]:
            raise ServiceError("cycle_already_completed")
        now, scope = db_now(conn), {k: conv[k] for k in SCOPE_KEYS}
        context_object = conn.execute(sa.select(a.agent_run_contexts.c.context_object_id).where(
            a.agent_run_contexts.c.run_id == run["id"])).scalar_one()
        language = understanding["language"]
        if handoff:
            if understanding.get("risk_flags"):
                from globalmail_agent.observability.local_records import store_understanding
                from globalmail_agent.application.risk_records import store_risks
                understanding_object = store_understanding(conn, writer, conv, run, understanding)
                store_risks(conn, writer, conv, run, understanding, understanding_object)
            body = command.draft
            summary = command.summary + "\n待核查：" + "；".join(command.gaps)
            draft_object = writer.put(conn, conv, body, "agent_unsent_draft", (context_object,)) if body else None
            note = writer.put(conn, conv, summary, "agent_handoff_summary", (context_object,))
            conn.execute(sa.insert(human_reviews).values(id=uuid4(), **scope, conversation_id=conv["id"],
                status="open", input_revision=conv["input_revision"], reason=summary[:500],
                visible_message_seq=conv["visible_message_seq"], as_of=context.as_of,
                draft_object_id=draft_object, note_object_id=note))
            conn.execute(conversations.update().where(conversations.c.id == conv["id"]).values(processing_owner="human_review",
                auto_run_gate="disabled", authority_epoch=conv["authority_epoch"] + 1, scheduling_state="idle"))
            outcome, status, citations, claims = "handoff", "handed_off", [], []
        else:
            validate_draft(conn, store, context, understanding, command)
            business_wait = command.waiting_for not in {"customer_information", "customer_feedback"}
            if business_wait and (not command.waiting_operation_id or context.mode != "simulation"):
                raise ServiceError("business_wait_invalid", 422)
            if context.mode == "simulation" and not register_wait(conn, conv, run["id"], command.waiting_for,
                    command.waiting_operation_id, command.observed_business_version):
                return {"outcome": "superseded", "reason_code": "stale_business_context"}
            body, citations = command.body, command.citation_ids
            claims = [c.model_dump(mode="json") for c in command.claims]
            draft_object = writer.put(conn, conv, body, "agent_reply", (context_object,))
            if context.mode == "simulation" and body:
                message = ServiceBase(engine, store).add_message(conn, writer, conv, body, conv["subject"],
                    "simulated_agent", "agent_cycle", str(cycle["id"]), now)
                from globalmail_agent.application.content_dependencies import register_dependencies
                register_dependencies(conn, scope, message["body_object_id"], (draft_object,))
                conn.execute(conversations.update().where(conversations.c.id == conv["id"]).values(
                    visible_message_seq=message["seq"], received_seq=message["received_seq"],
                    scheduling_state="waiting_business" if business_wait else "waiting_customer"))
                conn.execute(processing_cycles.update().where(processing_cycles.c.id == cycle["id"]).values(final_message_id=message["id"]))
                persist_facts(conn, writer, conv, context.payload, understanding["facts"], "agent_final_candidates")
                outcome = "reply_and_wait"
            elif context.mode == "simulation" and business_wait:
                outcome = "wait_business"
                conn.execute(conversations.update().where(conversations.c.id == conv["id"]).values(scheduling_state="waiting_business"))
            else:
                outcome = "historical_comparison"
                conn.execute(conversations.update().where(conversations.c.id == conv["id"]).values(scheduling_state="waiting_customer"))
            status = "completed"
        artifact_id = uuid4()
        conn.execute(sa.insert(a.reply_artifacts).values(id=artifact_id, **scope, conversation_id=conv["id"], run_id=run["id"],
            cycle_id=cycle["id"], outcome=outcome, language=language, body_object_id=draft_object,
            citation_ids=citations, claims=claims))
        conn.execute(agent_runs.update().where(agent_runs.c.id == run["id"]).values(status=status,
            outcome=outcome, finished_at=now, checkpoint_writable=False))
        conn.execute(jobs.update().where(jobs.c.id == job["id"]).values(status="completed", lease_expires_at=None))
        conn.execute(processing_cycles.update().where(processing_cycles.c.id == cycle["id"]).values(state="completed", completed_at=now))
        conn.execute(conversations.update().where(conversations.c.id == conv["id"]).values(row_version=conv["row_version"] + 1))
        conn.execute(domain_events.update().where(domain_events.c.conversation_id == conv["id"], domain_events.c.status == "pending")
            .values(status="processed"))
        consume_wakes(conn, conv, run["id"])
        append_ui_event(conn, conv["id"], "agent.handed_off" if handoff else "run.completed",
            {"run_id": str(run["id"]), "artifact_id": str(artifact_id), "outcome": outcome})
        release_slot(conn, slot_for_update(conn, context.workspace_id))
        return {"artifact_id": str(artifact_id), "outcome": outcome}
