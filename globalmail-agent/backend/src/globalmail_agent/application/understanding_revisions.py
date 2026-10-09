"""Source-backed intent revisions remain candidates and never change business authority."""
import json
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.body_store import BodyWriter, read_body
from globalmail_agent.adapters.conversation_schema import conversations, case_revisions
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.agent.guard import guarded
from globalmail_agent.agent.understanding import Understanding, validate_sources
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.application.event_store import append_ui_event
from globalmail_agent.domain.orders import result
from globalmail_agent.knowledge.base import canonical

BUSINESS_TOOLS = {"get_order_snapshot", "get_shipment_status", "get_after_sales_context",
    "get_item_availability", "get_operation_status"}


def scoped_run(table, conv, run_id):
    return (table.c.run_id == run_id, table.c.conversation_id == conv["id"],
        *[table.c[k] == conv[k] for k in SCOPE_KEYS])


def initial_understanding(conn, store, conv, run_id):
    identity = conn.execute(sa.select(a.understanding_results.c.body_object_id).where(
        *scoped_run(a.understanding_results, conv, run_id))).scalar_one_or_none()
    return json.loads(read_body(conn, store, conv, identity)) if identity else None


def current_understanding(conn, store, conv, run_id):
    identity = conn.execute(sa.select(a.understanding_revisions.c.body_object_id).where(
        *scoped_run(a.understanding_revisions, conv, run_id)).order_by(
            a.understanding_revisions.c.revision.desc()).limit(1)).scalar_one_or_none()
    return (json.loads(read_body(conn, store, conv, identity))["understanding"] if identity
        else initial_understanding(conn, store, conv, run_id))


def tool_sources(conn, store, conv, run_id):
    """Only persisted successful business receipts in this run are candidate evidence."""
    rows = conn.execute(sa.select(a.tool_commands).where(*scoped_run(a.tool_commands, conv, run_id),
        a.tool_commands.c.name.in_(BUSINESS_TOOLS), a.tool_commands.c.status == "ok",
        a.tool_commands.c.result_object_id.is_not(None))).mappings()
    return {"command:" + str(row["id"]): {"sender": "business_tool", "object_id": row["result_object_id"],
        "body": canonical(json.loads(read_body(conn, store, conv, row["result_object_id"]))).decode()}
        for row in rows}


def revision_result(conn, store, conv, row):
    body = json.loads(read_body(conn, store, conv, row["body_object_id"]))
    return result(data={"understanding": body["understanding"], "revision": row["revision"],
        "case_revision": row["case_revision"], "source_ids": row["source_ids"],
        "sources": body["sources"], "change_reason": row["change_reason"], "candidate_only": True},
        simulation=conv["mode"] == "simulation", source_kind="source_backed_candidate_revision")


def revise_understanding(engine, store, context, job, args, command_id):
    with BodyWriter(store) as writer, guarded(engine, context.workspace_id, job) as (conn, conv, run, cycle):
        prior = conn.execute(sa.select(a.understanding_revisions).where(
            *scoped_run(a.understanding_revisions, conv, run["id"]),
            a.understanding_revisions.c.command_id == command_id)).mappings().first()
        if prior:
            return revision_result(conn, store, conv, prior)
        if args.expected_case_revision != conv["case_revision"]:
            return result("conflict", "stale_case_revision", {"case_revision": conv["case_revision"]},
                simulation=context.mode == "simulation")
        current = current_understanding(conn, store, conv, run["id"])
        if current is None:
            raise ServiceError("understanding_not_available", 422)
        sources = {row["message_id"]: row for row in
            [*context.payload["messages"], *context.payload["human_notes"]]}
        business = tool_sources(conn, store, conv, run["id"])
        sources.update(business)
        refs = [*args.sources, *[ref for intent in args.intents for ref in intent.sources]]
        for ref in refs:
            if ref.message_id not in sources or ref.quote not in sources[ref.message_id]["body"]:
                raise ServiceError("understanding_source_invalid", 422)
        for intent in args.intents:
            if intent.consent in {"explicit", "declined"} and not any(
                    sources[ref.message_id]["sender"] in {"customer", "simulated_human", "human_note"}
                    for ref in intent.sources):
                raise ServiceError("candidate_choice_requires_message", 422)
        value = Understanding.model_validate({**current, "intents": [i.model_dump(mode="json") for i in args.intents],
            "missing_information": args.missing_information})
        value = validate_sources(value, context.payload, tool_sources=business)
        value["risk_flags"] = current["risk_flags"]
        if value["intents"] == current["intents"] and value["missing_information"] == current["missing_information"]:
            return result("denied", "understanding_unchanged", simulation=context.mode == "simulation")
        scope = {k: conv[k] for k in SCOPE_KEYS}
        revision = conn.execute(sa.select(sa.func.max(a.understanding_revisions.c.revision)).where(
            *scoped_run(a.understanding_revisions, conv, run["id"]))).scalar_one() or 0
        source_ids = list(dict.fromkeys(ref.message_id for ref in refs))
        quoted = [ref.model_dump(mode="json") for ref in refs]
        context_object = conn.execute(sa.select(a.agent_run_contexts.c.context_object_id).where(
            *scoped_run(a.agent_run_contexts, conv, run["id"]))).scalar_one()
        dependencies = (context_object, *[business[identity]["object_id"] for identity in source_ids if identity in business])
        body = writer.put(conn, conv, canonical({"understanding": value, "sources": quoted}).decode(),
            "understanding_revision", dependencies)
        case_revision = conv["case_revision"] + 1
        row = {"id": uuid4(), **scope, "conversation_id": conv["id"], "run_id": run["id"],
            "command_id": command_id, "revision": revision + 1, "case_revision": case_revision,
            "body_object_id": body, "source_ids": source_ids, "change_reason": args.change_reason}
        conn.execute(sa.insert(a.understanding_revisions).values(**row))
        conn.execute(sa.insert(case_revisions).values(id=uuid4(), **scope, conversation_id=conv["id"],
            revision=case_revision, as_of=context.as_of, visible_message_seq=conv["visible_message_seq"],
            source="agent_understanding_revision"))
        conn.execute(conversations.update().where(conversations.c.id == conv["id"]).values(case_revision=case_revision))
        conn.execute(a.agent_run_contexts.update().where(a.agent_run_contexts.c.run_id == run["id"])
            .values(validated_draft_hash=None))
        append_ui_event(conn, conv["id"], "agent.understanding_revised", {"run_id": str(run["id"]),
            "revision": revision + 1, "case_revision": case_revision})
        output = revision_result(conn, store, conv, row)
        receipt = writer.put(conn, conv, canonical(output).decode(), "agent_tool_result", (body,))
        conn.execute(a.tool_commands.update().where(a.tool_commands.c.id == command_id)
            .values(status=output["status"], result_object_id=receipt))
        append_ui_event(conn, conv["id"], "agent.tool", {"run_id": str(run["id"]),
            "tool_name": "revise_understanding", "status": output["status"], "reason_code": output["reason_code"]})
        return output
