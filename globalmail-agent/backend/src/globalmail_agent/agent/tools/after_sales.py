"""Business effects and their result credential share one guarded transaction."""
import json
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.body_store import BodyWriter, read_bytes
from globalmail_agent.agent.guard import guarded
from globalmail_agent.application.business_digest import business_digest
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.agent.tools.after_sales_result import compact_result

NAMES = {"check_after_sales_eligibility", "create_after_sales_operation", "cancel_after_sales_operation"}


def call_after_sales(gateway, name, args, identity):
    if gateway.context.mode != "simulation":
        raise ServiceError("historical_write_denied", 422)
    from globalmail_agent.application.after_sales import AfterSalesService
    service = AfterSalesService(gateway.engine, gateway.store, gateway.context.workspace_id)
    with BodyWriter(gateway.store) as writer, guarded(gateway.engine, gateway.context.workspace_id,
            gateway.job, lock_business=True) as (conn, conv, run, cycle):
        if name == "check_after_sales_eligibility":
            output = service.check(conn, conv, gateway.context, args)
        elif name == "create_after_sales_operation":
            output = service.create(conn, conv, gateway.context, args, identity)
        else:
            output = service.cancel(conn, conv, gateway.context, args, identity)
        compact_result(output)
        digest = business_digest(conn, conv)
        output["resource_versions"] = {**output.get("resource_versions", {}), "business_digest": digest}
        stale = []
        rows = conn.execute(sa.select(a.tool_commands).where(a.tool_commands.c.run_id == run["id"],
            a.tool_commands.c.id != identity, a.tool_commands.c.status.in_(["ok", "needs_input"]),
            a.tool_commands.c.result_object_id.is_not(None))).mappings().all()
        for row in rows:
            old = json.loads(read_bytes(conn, gateway.store, conv, row["result_object_id"]))
            previous = old.get("resource_versions", {}).get("business_digest")
            if previous and previous != digest:
                conn.execute(a.tool_commands.update().where(a.tool_commands.c.id == row["id"]).values(status="stale"))
                stale.append("command:" + str(row["id"]))
        if stale:
            output["superseded_source_ids"] = stale
        gateway.save_result(conn, writer, conv, run, name, identity, output)
        return output
