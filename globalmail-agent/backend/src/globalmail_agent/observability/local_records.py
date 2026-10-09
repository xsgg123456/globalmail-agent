"""Persist source material in controlled objects and associate it before model exposure."""
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.body_store import BodyWriter
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.agent.guard import guarded
from globalmail_agent.knowledge.base import canonical
from globalmail_agent.application.event_store import append_ui_event


def save_understanding(engine, store, workspace, job, value):
    with BodyWriter(store) as writer, guarded(engine, workspace, job, check_knowledge=False) as (conn, conv, run, cycle):
        store_understanding(conn, writer, conv, run, value)


def store_understanding(conn, writer, conv, run, value):
    """Danger uses the terminal transaction, so an active risk cannot exist without its review."""
    from globalmail_agent.attachments.evidence import store_visual_analysis
    store_visual_analysis(conn, writer, conv, run, value)
    source = conn.execute(sa.select(a.agent_run_contexts.c.context_object_id).where(
        a.agent_run_contexts.c.run_id == run["id"])).scalar_one()
    body = writer.put(conn, conv, canonical(value).decode(), "understanding_result", (source,))
    old = conn.execute(sa.select(a.understanding_results).where(a.understanding_results.c.run_id == run["id"])).mappings().first()
    if old:
        conn.execute(a.understanding_results.update().where(a.understanding_results.c.id == old["id"]).values(body_object_id=body))
    else:
        conn.execute(sa.insert(a.understanding_results).values(id=uuid4(), **{k: conv[k] for k in SCOPE_KEYS},
            conversation_id=conv["id"], run_id=run["id"], body_object_id=body))
    append_ui_event(conn, conv["id"], "agent.understood", {"run_id": str(run["id"]), "risk": bool(value["risk_flags"])})
    return body
