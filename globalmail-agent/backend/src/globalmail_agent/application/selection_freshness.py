"""A later customer message requires current source-backed interpretation before old execution."""
from uuid import UUID
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import messages, agent_runs
from globalmail_agent.application.business_read_model import scope_where
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.application.understanding_revisions import current_understanding
from globalmail_agent.application.selection_parameters import intent_applies_to_plan


def execution_selection(conn, store, conv, run_id, source, data, command):
    later = {str(r) for r in conn.execute(sa.select(messages.c.id).where(
        messages.c.conversation_id == conv["id"], *scope_where(messages, conv),
        messages.c.seq > source["seq"], messages.c.seq <= conv["visible_message_seq"],
        messages.c.sender == "customer")).scalars()}
    if not later:
        return current_understanding(conn, store, conv, run_id) or {}, run_id, None
    latest = conn.execute(sa.select(a.agent_run_contexts.c.run_id).join(agent_runs,
        agent_runs.c.id == a.agent_run_contexts.c.run_id).join(a.understanding_results,
        a.understanding_results.c.run_id == agent_runs.c.id).where(
        a.agent_run_contexts.c.conversation_id == conv["id"], *scope_where(a.agent_run_contexts, conv),
        a.agent_run_contexts.c.visible_message_seq == conv["visible_message_seq"],
        agent_runs.c.input_revision == conv["input_revision"]).order_by(agent_runs.c.created_at.desc()).limit(1)).scalar_one_or_none()
    if latest is None:
        raise ServiceError("selection_revalidation_required", 422)
    known = current_understanding(conn, store, conv, latest) or {}
    relevant = [i for i in known.get("intents", []) if i["consent"] in {"explicit", "declined", "conditional"}
        and any(ref["message_id"] in later for ref in i["sources"])
        and intent_applies_to_plan(i, data, command)]
    if not relevant:
        return current_understanding(conn, store, conv, run_id) or {}, latest, None
    category = {"spare_part": "parts", "logistics": "shipment"}.get(command.action, command.action)
    if len(relevant) != 1 or relevant[0]["consent"] != "explicit" or relevant[0].get("condition") or relevant[0]["business_type"] != category:
        raise ServiceError("selection_superseded", 422)
    refs = [ref for ref in relevant[0]["sources"] if ref["message_id"] in later]
    newest = conn.execute(sa.select(messages.c.id).where(messages.c.conversation_id == conv["id"],
        messages.c.id.in_([UUID(ref["message_id"]) for ref in refs]), *scope_where(messages, conv))
        .order_by(messages.c.seq.desc()).limit(1)).scalar_one()
    quotes = [ref for ref in refs if ref["message_id"] == str(newest)]
    if len(quotes) != 1:
        raise ServiceError("selection_reconfirmation_ambiguous", 422)
    return known, latest, quotes[0]
