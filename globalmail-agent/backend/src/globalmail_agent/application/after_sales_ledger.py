"""Mutations share the original operations/executions ledger and scoped reservations."""
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters import business_schema as b, after_sales_schema as a
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.application.business_read_model import scope_where, read_model
from globalmail_agent.application.business_queries import BusinessQueries
from globalmail_agent.domain.compensation import refundable_balance
from globalmail_agent.domain.executions import allowed_events
from globalmail_agent.domain.policy_ledger import units_for
from globalmail_agent.knowledge.base import canonical, sha


def provenance(conv, payload, ref):
    return {**{k: conv[k] for k in SCOPE_KEYS}, "source_kind": "synthetic_scenario",
        "source_ref": ref, "source_hash": sha(canonical(payload)), "source_snapshot": payload}


def operation_row(conn, conv, external_id, *, lock=False):
    query = sa.select(b.operations).where(b.operations.c.external_id == external_id, *scope_where(b.operations, conv))
    return conn.execute(query.with_for_update() if lock else query).mappings().first()


def release_compensation(conn, operation):
    conn.execute(a.compensation_reservations.update().where(a.compensation_reservations.c.operation_id == operation["id"],
        *scope_where(a.compensation_reservations, operation)).values(active=False))


def refresh_balances(conn, conv):
    # Balances are a projection of this same ledger; imported source bytes never mutate.
    return None


def operations_view(model, external_id=None):
    operations = [o for o in model["operations"] if external_id is None or o["operation_id"] == external_id]
    keys = {o["operation_id"] for o in operations}
    executions = [e for e in model["executions"] if e.get("operation_id") in keys]
    shipments = [s for s in model["shipments"] if s.get("operation_id") in keys]
    returns = [r for r in model["returns"] if r.get("operation_id") in keys]
    for operation in operations:
        related = [e for e in executions if e["operation_id"] == operation["operation_id"]]
        operation["cancelable"] = operation["status"] in {"accepted", "waiting_condition", "awaiting_execution", "failed"} and (
            not related or all(e.get("confirmed_not_executed") for e in related))
        operation["allowed_events"] = allowed_events(operation, related,
            [s for s in shipments if s["operation_id"] == operation["operation_id"]],
            [r for r in returns if r["operation_id"] == operation["operation_id"]])
        if operation["status"] == "waiting_condition" and not waiting_ready(model, operation):
            operation["allowed_events"] = [e for e in operation["allowed_events"] if e != "create_execution"]
    data = {"branch_id": str(model["scope"]["branch_id"]),
        "branch_generation": model["branch"]["generation"] if model["branch"] else None,
        "conversation_version": model["conversation"]["row_version"], "operations": operations,
        "executions": executions, "shipments": shipments, "returns": returns}
    return BusinessQueries.response(model, "ok" if operations or external_id is None else "empty",
        "after_sales_ledger" if operations or external_id is None else "operation_not_found", data)


def waiting_ready(model, operation):
    selected = next((l for l in model["lines"] if l[1]["line_id"] == operation["order_line_id"]), None)
    if not selected:
        return False
    _, line, order = selected
    units = units_for(operation, line)
    for condition in operation.get("waiting_conditions", []):
        if condition == "inventory":
            stocks = [s for s in model["inventory"] if s["item_id"] == operation.get("item_id")
                and s["region_spec"] == order["market"] and s["hardware_revision"] == line["hardware_revision"]]
            if len(stocks) != 1 or stocks[0]["on_hand"] - stocks[0]["reserved"] < operation["quantity"]:
                return False
        elif condition in {"warehouse_receipt", "warehouse_inspection"}:
            covered = set()
            for row in model["returns"]:
                if row["order_line_id"] != line["line_id"] or not row.get("received"):
                    continue
                if condition == "warehouse_inspection" and row.get("inspection") != "passed":
                    continue
                record = row
                if condition == "warehouse_inspection":
                    record = {**row, "quantity": row.get("inspected_quantity", row["quantity"])}
                    if "inspected_unit_ids" in row:
                        record["affected_unit_ids"] = row["inspected_unit_ids"]
                covered |= units_for(record, line) or set()
            if not units or not units <= covered:
                return False
    return True
