"""Build one consistent, scope-filtered read model without registering jobs."""
from hashlib import sha256
from sqlalchemy import select, func, or_
from globalmail_agent.adapters import business_schema as bs
from globalmail_agent.adapters.conversation_schema import conversations, messages, replay_cursors
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.domain.orders import MOCK_SOURCES, timestamp, unknown_fields, verified, operation_status
from globalmail_agent.application.business_projection import project, ORDER_FIELDS, LINE_FIELDS, LEDGER_FIELDS


def scope_where(table, scope):
    return [table.c[k] == scope[k] for k in SCOPE_KEYS]


def read_model(conn, conversation_id, workspace=DEFAULT_WORKSPACE_ID):
    conversation = conn.execute(select(conversations).where(conversations.c.id == conversation_id,
        conversations.c.workspace_id == workspace)).mappings().first()
    if not conversation or conversation["lifecycle"] in {"deleting", "deleted"}:
        raise ServiceError("conversation_not_found", 404)
    scope = {k: conversation[k] for k in SCOPE_KEYS}
    branch = conn.execute(select(bs.simulation_branches).where(*scope_where(bs.simulation_branches, scope),
        bs.simulation_branches.c.conversation_id == conversation_id)).mappings().first()
    visible = conn.execute(select(messages.c.source_message_id, messages.c.seq).where(*scope_where(messages, scope),
        messages.c.conversation_id == conversation_id, messages.c.seq <= conversation["visible_message_seq"])
        .order_by(messages.c.seq)).mappings().all()
    seen = {row["source_message_id"]: row["seq"] for row in visible}
    historical = conversation["mode"] == "historical_replay"
    if historical:
        as_of = conn.execute(select(replay_cursors.c.as_of).where(*scope_where(replay_cursors, scope),
            replay_cursors.c.conversation_id == conversation_id)).scalar()
    else:
        as_of = branch["clock"] if branch else None
    model = {"conversation": conversation, "scope": scope, "branch": branch, "as_of": as_of,
        "observed_at": conn.execute(select(func.now())).scalar_one().isoformat(),
        "orders": [], "lines": [], "shipments": [], "operations": [], "executions": [], "returns": [],
        "policy": None, "policy_metadata": None, "inventory": [], "compatibility": [], "products": {},
        "parts": [], "state": {}, "seen": list(seen), "unavailable": False, "future": False}
    if not branch:
        model["unavailable"] = historical
        return model
    if not as_of:
        model["unavailable"] = True
        return model
    orders = conn.execute(select(bs.branch_orders).where(*scope_where(bs.branch_orders, scope))).mappings().all()
    usable = [r for r in orders if r["snapshot_at"] <= as_of and
              (not historical or r["source_kind"] not in MOCK_SOURCES)]
    model["future"] = any(r["snapshot_at"] > as_of and r["source_kind"] not in MOCK_SOURCES for r in orders)
    model["unavailable"] = historical and not usable
    ids = [r["id"] for r in usable]
    lines = conn.execute(select(bs.branch_order_lines).where(*scope_where(bs.branch_order_lines, scope),
        bs.branch_order_lines.c.order_id.in_(ids))).mappings().all() if ids else []
    for row in conn.execute(select(bs.products).where(bs.products.c.workspace_id == workspace,
        bs.products.c.version == "v1")).mappings():
        record = row["source_snapshot"]
        if historical and (row["source_kind"] in MOCK_SOURCES or row["kind"] != "product" or
                not record.get("identity_observed_at") or timestamp(record["identity_observed_at"]) > as_of):
            continue
        if row["kind"] == "product":
            model["products"][row["sku"]] = record
        else:
            model["parts"].append(record)
    for row in usable:
        record = project(row["source_snapshot"], ORDER_FIELDS)
        record.update(customer_id=str(scope["customer_id"]), order_id=row["external_id"],
            source_kind=row["source_kind"], snapshot_at=row["snapshot_at"].isoformat(), is_realtime=False,
            unknown_fields=unknown_fields(record, ("currency", "paid_minor", "purchase_at", "delivered_at")),
            lines=[])
        model["orders"].append(record)
    for row in lines:
        if historical and row["source_kind"] in MOCK_SOURCES:
            continue
        record = project(row["source_snapshot"], LINE_FIELDS)
        product = model["products"].get(row["sku"], {})
        names = product.get("registered_names", [])
        record.update(line_id=row["external_id"], sku=row["sku"], quantity=row["quantity"],
            paid_minor=row["paid_minor"], hardware_revision=row["hardware_revision"],
            product_name=names[0] if names else None, source_kind=row["source_kind"],
            unknown_fields=unknown_fields({**record, "product_name": names[0] if names else None},
                ("paid_minor", "hardware_revision", "product_name")))
        order = next(o for o, original in zip(model["orders"], usable) if original["id"] == row["order_id"])
        order["lines"].append(record)
        model["lines"].append((row, record, order))
    line_ids = [r[0]["id"] for r in model["lines"]]
    operation_ids, execution_ids = {}, {}
    for key, table in (("operations", bs.operations), ("executions", bs.executions),
                       ("shipments", bs.shipments), ("returns", bs.return_receipts)):
        time_filter = table.c.snapshot_at <= as_of if historical else or_(table.c.snapshot_at <= as_of, table.c.snapshot_at.is_(None))
        rows = conn.execute(select(table).where(*scope_where(table, scope), table.c.order_id.in_(ids),
            table.c.order_line_id.in_(line_ids), time_filter)).mappings().all() if ids else []
        for row in rows:
            if historical and row["source_kind"] in MOCK_SOURCES:
                continue
            if "operation_id" in row and row["operation_id"] and row["operation_id"] not in operation_ids:
                continue
            if "execution_id" in row and row["execution_id"] and row["execution_id"] not in execution_ids:
                continue
            record = project(row["source_snapshot"], LEDGER_FIELDS)
            if key == "operations":
                operation_ids[row["id"]] = record["operation_id"] = row["external_id"]
                record["execution_ids"] = []
            if key == "executions":
                execution_ids[row["id"]] = record["execution_id"] = row["external_id"]
                operation = next(o for o in model["operations"] if o["operation_id"] == operation_ids[row["operation_id"]])
                operation["execution_ids"].append(row["external_id"])
            if row.get("operation_id"):
                record["operation_id"] = operation_ids[row["operation_id"]]
            if row.get("execution_id"):
                record["execution_id"] = execution_ids[row["execution_id"]]
            record.update(source_kind=row["source_kind"], snapshot_at=row["snapshot_at"].isoformat() if row["snapshot_at"] else None, is_realtime=False)
            if "status" in row:
                record["status"] = row["status"]
                if key == "operations":
                    record["source_status"] = row["source_snapshot"].get("status")
                    record["status"] = operation_status(row["status"])
            for field in ("quantity", "amount_minor", "currency", "received", "inspection"):
                if field in row:
                    record[field] = row[field]
            order = next(o for o, original in zip(model["orders"], usable) if original["id"] == row["order_id"])
            line = next(l for original, l, _ in model["lines"] if original["id"] == row["order_line_id"])
            record.update(order_id=order["order_id"], order_line_id=line["line_id"])
            record["unknown_fields"] = unknown_fields(record, ("status", "updated_at", "snapshot_at"))
            model[key].append(record)
    if historical:
        return model  # No Mock facts, compatibility, inventory or policy can cross this boundary.
    policy = conn.execute(select(bs.policy_profiles).where(bs.policy_profiles.c.id == branch["policy_profile_id"],
        bs.policy_profiles.c.workspace_id == workspace, bs.policy_profiles.c.available_at <= as_of)).mappings().first()
    if policy:
        model["policy"] = policy["source_snapshot"]
        model["policy_metadata"] = {k: policy[k] for k in
            ("policy_id", "version", "publication_status", "description", "source_kind", "source_hash")}
        model["policy_metadata"]["available_at"] = policy["available_at"].isoformat()
        model["policy_metadata"]["readable_sha256"] = sha256(policy["description"].encode("utf-8")).hexdigest()
    model["compatibility"] = [r["source_snapshot"] for r in conn.execute(select(bs.compatibility).where(
        bs.compatibility.c.workspace_id == workspace, bs.compatibility.c.version == "v1",
        bs.compatibility.c.sku.in_([l[1]["sku"] for l in model["lines"]]))).mappings()]
    for row in conn.execute(select(bs.inventory).where(*scope_where(bs.inventory, scope),
            or_(bs.inventory.c.snapshot_at <= as_of, bs.inventory.c.snapshot_at.is_(None)))).mappings():
        model["inventory"].append({"item_id": row["item_id"], "region_spec": row["region_spec"],
            "hardware_revision": row["hardware_revision"], "on_hand": row["on_hand"], "reserved": row["reserved"],
            "snapshot_at": row["snapshot_at"].isoformat() if row["snapshot_at"] else None, "source_kind": row["source_kind"],
            "evidence_ref": "inventory:" + str(row["id"]), "source_hash": row["source_hash"]})
    state = dict(branch["state"])
    state["customer_choices"] = [verified({**choice, "source_message_seq": seen[choice["source_message_id"]]}, "message:" + choice["source_message_id"])
        for choice in state.get("customer_choices", []) if choice.get("source_message_id") in seen]
    state["customer_choices"].sort(key=lambda choice: choice["source_message_seq"])
    state["attempted_steps"] = [step for step in state.get("attempted_steps", [])
        if step.get("source_message_id") in seen]
    address = state.get("address_confirmation")
    if (address and address.get("customer_id") == state["source_customer_id"]
            and (not address.get("source_message_id") or address["source_message_id"] in seen)):
        state["address_confirmation"] = verified({**address, "customer_id": str(scope["customer_id"])},
            "branch:" + str(branch["id"]) + ":address:" + str(address.get("version")))
    else:
        state.pop("address_confirmation", None)
    state.pop("source_customer_id", None); state.pop("allowed_order_ids", None)
    state["visible_source_message_ids"] = list(seen)
    state["mode"] = conversation["mode"]
    model["state"] = state
    return model
