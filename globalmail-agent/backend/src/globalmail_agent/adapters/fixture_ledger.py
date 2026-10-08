"""Materialize one initial branch. No future controller is read or called."""
from uuid import uuid4
from sqlalchemy import insert
from globalmail_agent.adapters import business_schema as bs
from globalmail_agent.adapters.fixture_loader import source_values, STATE_FIELDS
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.domain.orders import timestamp, operation_status


def load_branch(conn, conversation, scenario, package):
    registered, policy = package.catalog(conn, conversation["workspace_id"])
    scope = {key: conversation[key] for key in SCOPE_KEYS}
    initial = scenario["initial_state"]
    source = source_values(scenario, scenario["source_ref"], scenario["source_kind"])
    state = {k: initial[k] for k in STATE_FIELDS if k in initial}
    state["source_customer_id"] = scenario["access_scope"]["customer_id"]
    state["allowed_order_ids"] = scenario["access_scope"]["allowed_order_ids"]
    conn.execute(insert(bs.simulation_branches).values(id=conversation["branch_id"], **scope, **source,
        conversation_id=conversation["id"], dataset_id=conversation["dataset_id"],
        scenario_id=scenario["scenario_id"], clock=timestamp(scenario["clock"]), state=state,
        policy_profile_id=policy if scenario["policy_profile_id"] else None,
        tool_overrides=scenario["tool_overrides"]))
    orders, lines = {}, {}
    for record in initial.get("orders", []):
        oid = orders[record["order_id"]] = uuid4()
        conn.execute(insert(bs.branch_orders).values(id=oid, **scope,
            **source_values(record, scenario["source_ref"]), conversation_id=conversation["id"],
            external_id=record["order_id"], display_order_number=record["display_order_number"],
            brand=record["brand"], currency=record.get("currency"), paid_minor=record.get("paid_minor"),
            snapshot_at=timestamp(record["snapshot_at"])))
        for line in record["lines"]:
            lid = lines[line["line_id"]] = uuid4()
            conn.execute(insert(bs.branch_order_lines).values(id=lid, **scope,
                **source_values(line, scenario["source_ref"]), order_id=oid, external_id=line["line_id"],
                brand=record["brand"], sku=line["sku"], product_id=registered[line["sku"]],
                hardware_revision=line.get("hardware_revision"), quantity=line["quantity"], paid_minor=line.get("paid_minor")))
    operation_map = {}
    for record in initial.get("operations", []):
        rid = operation_map[record["operation_id"]] = uuid4()
        values = ledger_values(scope, record, scenario, orders, lines)
        values["status"] = operation_status(record.get("status"))
        conn.execute(insert(bs.operations).values(id=rid, **values,
            external_id=record["operation_id"], kind=record["kind"], quantity=record["quantity"],
            amount_minor=record.get("amount_minor"), currency=record.get("currency"), issue_id=record.get("issue_id")))
    execution_map = {}
    operations = {v["operation_id"]: v for v in initial.get("operations", [])}
    for record in initial.get("execution_records", []):
        rid = execution_map[record["execution_id"]] = uuid4()
        operation = operations[record["operation_id"]]
        related = {**record, "order_id": operation["order_id"], "order_line_id": operation["order_line_id"]}
        values = ledger_values(scope, related, scenario, orders, lines)
        values.update(source_values(record, scenario["source_ref"]))
        conn.execute(insert(bs.executions).values(id=rid, **values, external_id=record["execution_id"],
            operation_id=operation_map[record["operation_id"]], amount_minor=record.get("amount_minor"), currency=record.get("currency")))
    for name, table, external in (("shipments", bs.shipments, "parcel_id"), ("returns", bs.return_receipts, "return_id")):
        for record in initial.get(name, []):
            extra = dict(operation_id=operation_map.get(record.get("operation_id")),
                         execution_id=execution_map.get(record.get("execution_id")))
            if name == "shipments":
                extra["parcel_purpose"] = record["purpose"]
            else:
                extra.update(quantity=record["quantity"], received=record.get("received"), inspection=record.get("inspection"))
            conn.execute(insert(table).values(id=uuid4(), **ledger_values(scope, record, scenario, orders, lines),
                external_id=record[external], **extra))
    # Inventory belongs only to this branch; absent region/specification stays unknown.
    for record in initial.get("inventory", []):
        at = record.get("snapshot_at")
        conn.execute(insert(bs.inventory).values(id=uuid4(), **scope,
            **source_values(record, scenario["source_ref"]), item_id=record["item_id"],
            region_spec=record.get("region_spec"), hardware_revision=record.get("hardware_revision"),
            on_hand=record["on_hand"], reserved=record["reserved"], snapshot_at=timestamp(at) if at else None))


def ledger_values(scope, record, scenario, orders, lines):
    return {**scope, **source_values(record, scenario["source_ref"]),
        "order_id": orders[record["order_id"]],
        "order_line_id": lines[record.get("order_line_id", record.get("line_id"))],
        "status": record.get("status"),
        "snapshot_at": timestamp(record["snapshot_at"]) if record.get("snapshot_at") else None}
