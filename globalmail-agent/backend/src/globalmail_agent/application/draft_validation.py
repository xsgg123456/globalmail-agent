"""Deterministic source gates run before model review and again inside commit."""
import json
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.body_store import read_body
from globalmail_agent.adapters.conversation_schema import conversations
from globalmail_agent.application.business_digest import business_digest
from globalmail_agent.application.conversation_lock import ServiceError


def check_draft_sources(conn, store, context, understanding, draft):
    if draft.language.lower().split("-")[0] != understanding["language"].lower().split("-")[0]:
        raise ServiceError("reply_language_invalid", 422)
    deps = {str(r["reference_id"]): r for r in conn.execute(sa.select(a.agent_run_dependencies).where(
        a.agent_run_dependencies.c.run_id == context.run_id, a.agent_run_dependencies.c.active.is_(True))).mappings()}
    if any(identity not in deps for identity in draft.citation_ids):
        raise ServiceError("reply_citation_invalid", 422)
    source_ids = {r["message_id"] for r in [*context.payload["messages"], *context.payload["human_notes"]]}
    command_ids, business_ids = set(), set()
    conv = conn.execute(sa.select(conversations).where(conversations.c.id == context.conversation_id)).mappings().one()
    current_business = business_digest(conn, conv, lock=True)
    records = conn.execute(sa.select(a.tool_commands).where(a.tool_commands.c.run_id == context.run_id,
        a.tool_commands.c.status.in_(["ok", "needs_input"]))).mappings()
    for record in records:
        if record["result_object_id"]:
            observation = json.loads(read_body(conn, store, conv, record["result_object_id"]))
            prior_business = observation.get("resource_versions", {}).get("business_digest")
            if prior_business and prior_business != current_business:
                raise ServiceError("stale_business_context")
        if record["name"] not in {"create_reply_draft", "request_human_review"}:
            command_ids.add("command:" + str(record["id"]))
        if record["name"] in {"get_order_snapshot", "get_shipment_status", "get_after_sales_context", "get_operation_status", "get_item_availability"}:
            business_ids.add("command:" + str(record["id"]))
    for claim in draft.claims:
        if claim.text not in draft.body or any(s not in source_ids | command_ids | deps.keys() for s in claim.source_ids):
            raise ServiceError("reply_source_invalid", 422)
        if claim.kind == "product_step" and not any(s in deps and s in draft.citation_ids for s in claim.source_ids):
            raise ServiceError("product_step_without_evidence", 422)
        if claim.kind == "order_fact" and not any(s in business_ids for s in claim.source_ids):
            raise ServiceError("order_fact_without_tool", 422)
        if claim.kind == "customer_fact" and not any(s in source_ids for s in claim.source_ids):
            raise ServiceError("customer_fact_without_message", 422)
    return list(deps)
