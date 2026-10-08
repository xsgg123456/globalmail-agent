"""Rebuild history using only actual visible messages; stable issue IDs survive cutpoints."""
from uuid import uuid4
from sqlalchemy import insert, select, update, delete
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.adapters.conversation_schema import case_issues, case_facts, case_revisions, conversations
from globalmail_agent.adapters.body_store import read_body


def rebuild(conn, writer, store, conversation, visible_messages, as_of):
    issue = conn.execute(select(case_issues).where(case_issues.c.conversation_id == conversation["id"],
        case_issues.c.issue_key == "correspondence")).mappings().first()
    scope = {k: conversation[k] for k in SCOPE_KEYS}
    if issue is None:
        issue_id = uuid4()
        conn.execute(insert(case_issues).values(id=issue_id, **scope, conversation_id=conversation["id"],
                                              issue_key="correspondence", status="open", version=1))
    else:
        issue_id = issue["id"]
        conn.execute(update(case_issues).where(case_issues.c.id == issue_id)
                     .values(status="open", version=issue["version"] + 1))
    revision = conversation["case_revision"] + 1
    # Replace the current projection, never copy candidate memory from a prior AI/human comparison.
    conn.execute(delete(case_facts).where(case_facts.c.conversation_id == conversation["id"]))
    for message in visible_messages:
        value = writer.put(conn, conversation, read_body(conn, store, conversation, message["body_object_id"]),
                           "case_fact", derived_from=(message["body_object_id"],))
        conn.execute(insert(case_facts).values(id=uuid4(), **scope, conversation_id=conversation["id"],
            issue_id=issue_id, source_message_id=message["id"],
            kind="customer_report" if message["sender"] == "customer" else "historical_claim",
            value_object_id=value, revision=revision, visible_seq=message["seq"]))
    conn.execute(insert(case_revisions).values(id=uuid4(), **scope, conversation_id=conversation["id"],
        revision=revision, as_of=as_of, visible_message_seq=conversation["visible_message_seq"],
        source="real_visible_prefix"))
    conn.execute(update(conversations).where(conversations.c.id == conversation["id"])
                 .values(case_revision=revision))
