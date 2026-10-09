"""Candidate updates keep message sources and cannot overwrite a business tool ledger."""
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.body_store import BodyWriter
from globalmail_agent.adapters.conversation_schema import case_facts, case_issues, case_revisions, conversations, messages
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.agent.guard import guarded
from globalmail_agent.agent.understanding import Understanding, validate_sources
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.domain.orders import result
from globalmail_agent.knowledge.base import canonical


def persist_facts(conn, writer, conv, payload, facts, source):
    scope = {k: conv[k] for k in SCOPE_KEYS}
    issue = conn.execute(sa.select(case_issues).where(case_issues.c.conversation_id == conv["id"],
        case_issues.c.issue_key == "correspondence")).mappings().one()
    revision = conv["case_revision"] + 1
    visible = {m["message_id"]: m for m in payload["messages"]}
    grouped = {}
    for fact in facts:
        for ref in fact["sources"]:
            if ref["message_id"] in visible:
                grouped.setdefault((ref["message_id"], fact["kind"]), []).append(fact)
    for (message_id, kind), values in grouped.items():
        source_object = conn.execute(sa.select(messages.c.body_object_id).where(messages.c.id == UUID(message_id),
            messages.c.conversation_id == conv["id"])).scalar_one()
        body = writer.put(conn, conv, canonical(values).decode(), "candidate_case_facts", (source_object,))
        old = conn.execute(sa.select(case_facts).where(case_facts.c.conversation_id == conv["id"],
            case_facts.c.source_message_id == UUID(message_id), case_facts.c.kind == kind)).mappings().first()
        if old:
            conn.execute(case_facts.update().where(case_facts.c.id == old["id"]).values(value_object_id=body, revision=revision))
        else:
            conn.execute(sa.insert(case_facts).values(id=uuid4(), **scope, conversation_id=conv["id"],
                issue_id=issue["id"], source_message_id=UUID(message_id), kind=kind, value_object_id=body,
                revision=revision, visible_seq=visible[message_id]["seq"]))
    conn.execute(sa.insert(case_revisions).values(id=uuid4(), **scope, conversation_id=conv["id"], revision=revision,
        as_of=payload["as_of"], visible_message_seq=conv["visible_message_seq"], source=source))
    conn.execute(conversations.update().where(conversations.c.id == conv["id"]).values(case_revision=revision))
    return revision


def update_candidates(engine, store, context, job, args):
    candidate = Understanding(language="und", intents=[], order_candidates=[], facts=args.facts,
        risk_flags=[], missing_information=[])
    validate_sources(candidate, context.payload)
    with BodyWriter(store) as writer, guarded(engine, context.workspace_id, job) as (conn, conv, run, cycle):
        if context.mode != "simulation":
            return result("denied", "historical_candidate_memory_isolated")
        if args.expected_case_revision != conv["case_revision"]:
            return result("conflict", "stale_case_revision", {"case_revision": conv["case_revision"]})
        revision = persist_facts(conn, writer, conv, context.payload,
            [f.model_dump(mode="json") for f in args.facts], "agent_source_backed_candidate")
        return result(data={"case_revision": revision, "facts": [f.model_dump(mode="json") for f in args.facts]},
            simulation=True, source_kind="model_inference")
