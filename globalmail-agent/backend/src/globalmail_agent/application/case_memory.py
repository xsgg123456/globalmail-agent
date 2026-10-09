"""Rebuild history using only actual visible messages; stable issue IDs survive cutpoints."""
from uuid import uuid4
from sqlalchemy import insert, select, update, delete
from globalmail_agent.adapters.schema import SCOPE_KEYS, objects
from globalmail_agent.adapters.conversation_schema import case_issues, case_facts, case_revisions, conversations
from globalmail_agent.adapters.body_store import read_body


def rebuild(conn, writer, store, conversation, visible_messages, as_of):
    issue = conn.execute(select(case_issues.c.id, case_issues.c.version).where(case_issues.c.conversation_id == conversation["id"],
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
    # Historical cutpoints rebuild from actual mail; simulation keeps validated source-backed candidates.
    kept = set()
    if conversation["mode"] == "simulation":
        visible_ids = [message["id"] for message in visible_messages]
        kept = {(r["source_message_id"], r["kind"]) for r in conn.execute(select(case_facts)
            .join(objects, objects.c.id == case_facts.c.value_object_id).where(
                case_facts.c.conversation_id == conversation["id"], case_facts.c.source_message_id.in_(visible_ids),
                objects.c.source_kind == "candidate_case_facts")).mappings()}
        retained = select(objects.c.id).where(objects.c.source_kind == "candidate_case_facts")
        conn.execute(delete(case_facts).where(case_facts.c.conversation_id == conversation["id"],
            ~case_facts.c.value_object_id.in_(retained)))
    else:
        conn.execute(delete(case_facts).where(case_facts.c.conversation_id == conversation["id"]))
    for message in visible_messages:
        kind = "customer_report" if message["sender"] == "customer" else "historical_claim"
        if (message["id"], kind) in kept:
            continue
        value = writer.put(conn, conversation, read_body(conn, store, conversation, message["body_object_id"]),
                           "case_fact", derived_from=(message["body_object_id"],))
        conn.execute(insert(case_facts).values(id=uuid4(), **scope, conversation_id=conversation["id"],
            issue_id=issue_id, source_message_id=message["id"],
            kind=kind,
            value_object_id=value, revision=revision, visible_seq=message["seq"]))
    conn.execute(insert(case_revisions).values(id=uuid4(), **scope, conversation_id=conversation["id"],
        revision=revision, as_of=as_of, visible_message_seq=conversation["visible_message_seq"],
        source="real_visible_prefix"))
    conn.execute(update(conversations).where(conversations.c.id == conversation["id"])
                 .values(case_revision=revision))
