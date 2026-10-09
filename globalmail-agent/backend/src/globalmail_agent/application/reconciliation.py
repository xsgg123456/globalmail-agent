"""Backup linking cannot invent, migrate or duplicate existing execution effects."""
import sqlalchemy as sa
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.application.business_read_model import scope_where
from globalmail_agent.application.conversation_lock import ServiceError


def link_existing(conn, conv, operation, execution_id):
    execution = conn.execute(sa.select(b.executions).where(b.executions.c.external_id == execution_id,
        *scope_where(b.executions, conv)).with_for_update()).mappings().first()
    if not execution:
        raise ServiceError("execution_out_of_scope", 422)
    snapshot = execution["source_snapshot"]
    proposal = operation["source_snapshot"].get("plan", {})
    if (execution["operation_id"] != operation["id"] or execution["order_id"] != operation["order_id"]
            or execution["order_line_id"] != operation["order_line_id"] or execution["amount_minor"] != operation["amount_minor"]
            or execution["currency"] != operation["currency"] or snapshot.get("kind") != operation["kind"]
            or snapshot.get("quantity") != operation["quantity"]
            or snapshot.get("item_id") != proposal.get("item_id")
            or snapshot.get("address_version") != proposal.get("address_version")
            or set(snapshot.get("affected_unit_ids", [])) != set(proposal.get("affected_unit_ids", []))):
        raise ServiceError("execution_link_mismatch", 422)
    return execution
