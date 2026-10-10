"""Source-backed commercial intents change authority, never create a business operation."""
import sqlalchemy as sa
from globalmail_agent.adapters.conversation_schema import conversations, agent_runs, processing_cycles, human_reviews
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.agent.guard import guarded
from globalmail_agent.application.event_store import append_ui_event
from uuid import uuid4

COMMERCIAL = {"refund", "return", "replacement", "parts"}


def commercial_intent(understanding):
    return any(intent["business_type"] in COMMERCIAL for intent in understanding.get("intents", []))


def ensure_review(conn, conv, *, reason="售后由客服持续处理", as_of=None):
    review = conn.execute(sa.select(human_reviews).where(human_reviews.c.conversation_id == conv["id"],
        human_reviews.c.status == "open")).mappings().first()
    if review:
        return dict(review)
    row = {"id": uuid4(), **{k: conv[k] for k in SCOPE_KEYS}, "conversation_id": conv["id"],
        "status": "open", "input_revision": conv["input_revision"], "reason": reason,
        "visible_message_seq": conv["visible_message_seq"], "as_of": as_of, "version": 1}
    conn.execute(sa.insert(human_reviews).values(**row))
    return row


def retain_human(engine, store, context, job, understanding):
    if not commercial_intent(understanding):
        return
    with guarded(engine, context.workspace_id, job, check_knowledge=False) as (conn, conv, run, cycle):
        if conv["persistent_human"]:
            context.payload["execution_mode"] = "human_assist"
            return
        epoch = conv["authority_epoch"] + 1
        conn.execute(conversations.update().where(conversations.c.id == conv["id"]).values(
            persistent_human=True, processing_owner="human_review", auto_run_gate="disabled",
            human_claimed=False, authority_epoch=epoch, row_version=conv["row_version"] + 1))
        conn.execute(agent_runs.update().where(agent_runs.c.id == run["id"]).values(
            execution_mode="human_assist", authority_epoch=epoch))
        conn.execute(processing_cycles.update().where(processing_cycles.c.id == cycle["id"]).values(authority_epoch=epoch))
        conv.update(persistent_human=True, processing_owner="human_review", authority_epoch=epoch)
        ensure_review(conn, conv, as_of=context.as_of)
        context.payload.update(execution_mode="human_assist", persistent_human=True, authority_epoch=epoch)
        append_ui_event(conn, conv["id"], "human.required", {"run_id": str(run["id"])})


def advice_value(command, understanding):
    return {"summary": command.summary, "gaps": command.gaps, "recommendations": command.recommendations,
        "draft": command.draft, "intents": understanding.get("intents", []), "facts": understanding.get("facts", [])}
