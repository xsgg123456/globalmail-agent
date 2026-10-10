"""Internal suggestions remain separate from staff drafts and customer mail."""
import sqlalchemy as sa
from datetime import datetime, timezone
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import conversations
from globalmail_agent.application.human_assistance import ensure_review, advice_value
from globalmail_agent.knowledge.base import canonical


def save_advice(conn, writer, conv, run, context, command, understanding, context_object):
    receipts = list(conn.execute(sa.select(a.tool_commands.c.result_object_id).where(
        a.tool_commands.c.run_id == run["id"], a.tool_commands.c.result_object_id.is_not(None))).scalars())
    dependencies = (context_object, *receipts)
    draft = writer.put(conn, conv, command.draft, "agent_unsent_draft", dependencies) if command.draft else None
    advice = advice_value(command, understanding)
    advice.update(run_id=str(run["id"]), input_revision=conv["input_revision"],
        queried_at=datetime.now(timezone.utc).isoformat(), as_of=context.as_of.isoformat())
    advice_object = writer.put(conn, conv, canonical(advice).decode(), "agent_advice", dependencies)
    ensure_review(conn, conv, reason="Agent转人工：" + command.reason, as_of=context.as_of)
    claimed = conv["human_claimed"] if conv["persistent_human"] else False
    conn.execute(conversations.update().where(conversations.c.id == conv["id"]).values(
        processing_owner="human_review", auto_run_gate="disabled", human_claimed=claimed,
        authority_epoch=conv["authority_epoch"] + 1, scheduling_state="idle"))
    outcome = "human_advice" if conv["persistent_human"] and claimed else "handoff"
    return draft, advice_object, outcome, "completed" if outcome == "human_advice" else "handed_off"
