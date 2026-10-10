"""Persist actual text requests/responses locally, with the existing content revocation graph."""
import json
import sqlalchemy as sa
from globalmail_agent.adapters.agent_schema import agent_run_contexts, usage_records
from globalmail_agent.adapters.body_store import BodyWriter, read_bytes
from globalmail_agent.adapters.conversation_schema import conversations
from globalmail_agent.application.event_store import append_ui_event
from globalmail_agent.knowledge.base import canonical, sha


def request_record(conn, writer, conv, run, messages, stage, model, schema, tools, options, image_views):
    context = conn.execute(sa.select(agent_run_contexts.c.context_object_id).where(
        agent_run_contexts.c.run_id == run["id"])).scalar_one()
    # Full text is preserved. Transport image bytes are represented by authorized references.
    value = {"messages": messages, "response_schema": schema, "tools": tools or [],
        "provider_options": options, "model": model, "stage": stage,
        "image_views": image_views, "image_transport": "authorized_reference" if image_views else "none"}
    value["prompt_hash"] = sha(canonical(messages))
    return writer.put(conn, conv, canonical(value).decode(), "model_request", (context,))


def finish_record(engine, store, workspace, job, key, output, error_code=None):
    # Diagnostic late results are retained, but can never perform a business/customer effect.
    with BodyWriter(store) as writer, engine.begin() as conn:
        conv = conn.execute(sa.select(conversations).where(conversations.c.id == job["conversation_id"],
            conversations.c.workspace_id == workspace).with_for_update()).mappings().one()
        row = conn.execute(sa.select(usage_records).where(usage_records.c.run_id == job["run_id"],
            usage_records.c.request_key == key).with_for_update()).mappings().one()
        if row["request_state"] != "running" or conv["lifecycle"] in {"deleting", "deleted"}:
            return
        from globalmail_agent.attachments.revocation import check_content_access
        from globalmail_agent.application.conversation_lock import ServiceError
        try:
            check_content_access(conn, conv, row["request_object_id"])
        except ServiceError:
            conn.execute(usage_records.update().where(usage_records.c.id == row["id"]).values(
                request_state="revoked", error_code="image_content_revoked", finished_at=sa.func.now()))
            return
        response = writer.put(conn, conv, canonical(output).decode(), "model_response",
            (row["request_object_id"],)) if output is not None else None
        conn.execute(usage_records.update().where(usage_records.c.id == row["id"]).values(
            response_object_id=response, request_state="failed" if error_code else "completed",
            error_code=error_code, finished_at=sa.func.now()))
        append_ui_event(conn, conv["id"], "agent.model", {"run_id": str(job["run_id"]),
            "status": "failed" if error_code else "completed", "reason_code": error_code})


def read_records(conn, store, conv, run_id):
    records = []
    for row in conn.execute(sa.select(usage_records).where(usage_records.c.run_id == run_id)
            .order_by(usage_records.c.created_at, usage_records.c.id)).mappings():
        request = json.loads(read_bytes(conn, store, conv, row["request_object_id"])) if row["request_object_id"] else None
        output = json.loads(read_bytes(conn, store, conv, row["response_object_id"])) if row["response_object_id"] else None
        thinking = (request or {}).get("provider_options") or {}
        enabled = thinking.get("extra_body", {}).get("enable_thinking")
        state = "not_recorded" if request is None else "returned" if output and output.get("reasoning_content") else (
            "failed" if row["request_state"] == "failed" else "disabled" if enabled is False else "not_returned")
        records.append({"id": str(row["id"]), "request_key": row["request_key"], "stage": row["stage"],
            "model": row["model"], "status": row["request_state"], "request": request, "response": output,
            "reasoning_state": state, "created_at": row["created_at"], "finished_at": row["finished_at"],
            "error_code": row["error_code"], "input_tokens": row["input_tokens"], "output_tokens": row["output_tokens"]})
    return records
