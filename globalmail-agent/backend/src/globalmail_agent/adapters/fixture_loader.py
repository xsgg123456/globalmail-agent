"""Only explicitly allowed source files and initial facts are read."""
import json
from hashlib import sha256
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from globalmail_agent.adapters.business_schema import products, compatibility, policy_profiles
from globalmail_agent.domain.orders import integer, timestamp

FIXTURE_ROOT = Path(__file__).resolve().parents[5] / "data" / "knowledge" / "v1"
STATE_FIELDS = {"customer_choices", "attempted_steps", "address_confirmation",
    "compatibility_override", "confirmed_missing_part_id", "defect_confirmed_in_simulation",
    "delivery_disputed", "refund_proposal", "requested_part_id", "return_request_details", "service_notes"}
LEDGER_FIELDS = {"orders", "operations", "execution_records", "shipments", "returns", "inventory"}


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def source_values(record, path, source_kind=None):
    return {"source_snapshot": record, "source_hash": digest(record), "source_ref": path,
            "source_kind": source_kind or record.get("source_kind", "synthetic")}


class FixturePackage:
    def __init__(self, root=FIXTURE_ROOT):
        self.root = Path(root)
        self.hashes = {}
        self.products = self.read("products.json")
        self.parts = self.read("parts.json")
        self.compatibility = self.read("compatibility.json")
        self.inventory = self.read("inventory.json")
        self.policy = self.read("policies/policy-profile.json")
        self.description = self.read("policies/policy-profile.md", text=True)
        canonical = self.read("authoring/policy-profile.json")
        rendered = self.read("sources/policy-render.json")
        if (canonical != self.policy or rendered["canonical_sha256"] != self.hashes["authoring/policy-profile.json"]
                or rendered["readable_sha256"] != self.hashes["policies/policy-profile.md"]
                or rendered["rule_version"] != self.policy["version"]):
            raise ValueError("policy_bundle_mismatch")
        self.by_sku = {p["sku"]: p for p in self.products}
        self.by_part = {p["part_id"]: p for p in self.parts}
        self.scenarios = {}
        for path in ("scenarios/inputs.jsonl", "scenarios/journeys/inputs.jsonl"):
            for row in self.read(path, lines=True):
                if row.get("usage_split") != "dev":
                    continue
                # Do not retain story, controller refs, provenance answers or future events.
                allowed = {k: row[k] for k in ("scenario_id", "mode", "clock", "branch_id",
                    "access_scope", "business_categories", "policy_profile_id", "source_kind", "product_id")}
                state = row["initial_state"]
                allowed["initial_state"] = {k: state[k] for k in STATE_FIELDS | LEDGER_FIELDS if k in state}
                allowed["tool_overrides"] = state.get("tool_overrides", [])
                allowed["conversation"] = state["conversation"]
                allowed["initial_messages"] = row["initial_messages"]
                allowed["source_ref"] = path + "#" + row["scenario_id"]
                self.validate(allowed)
                if row["scenario_id"] in self.scenarios:
                    raise ValueError("fixture_scenario_duplicate")
                self.scenarios[row["scenario_id"]] = allowed

    def read(self, path, *, lines=False, text=False):
        # Paths are constants at call sites, never supplied by requests.
        raw = (self.root / path).read_bytes()
        self.hashes[path] = sha256(raw).hexdigest()
        value = raw.decode("utf-8")
        return value if text else [json.loads(line) for line in value.splitlines() if line] if lines else json.loads(value)

    def validate(self, row):
        state, scope = row["initial_state"], row["access_scope"]
        if row["mode"] not in {"simulation", "historical_replay"}:
            raise ValueError("fixture_mode_invalid")
        timestamp(row["clock"])
        if row["conversation"]["customer_id"] != scope["customer_id"]:
            raise ValueError("fixture_customer_mismatch")
        orders, lines = {}, {}
        for order in state.get("orders", []):
            if order["customer_id"] != scope["customer_id"] or order["order_id"] not in scope["allowed_order_ids"]:
                raise ValueError("fixture_order_denied")
            if order["brand"] != row["conversation"]["brand"]:
                raise ValueError("fixture_brand_mismatch")
            if order["order_id"] in orders:
                raise ValueError("fixture_order_duplicate")
            timestamp(order["snapshot_at"])
            for key in ("paid_minor", "refunded_minor", "pending_refund_minor"):
                integer(order.get(key), optional=True)
            orders[order["order_id"]] = order
            for line in order["lines"]:
                product = self.by_sku.get(line["sku"])
                if not product or product["brand"] != order["brand"]:
                    raise ValueError("fixture_product_not_registered")
                integer(line["quantity"], minimum=1)
                integer(line.get("paid_minor"), optional=True)
                if line["line_id"] in lines:
                    raise ValueError("fixture_line_duplicate")
                lines[line["line_id"]] = order["order_id"]
        operations = {}
        for value in state.get("operations", []):
            self.relation(value, lines, scope, row)
            integer(value["quantity"], minimum=1)
            integer(value.get("amount_minor"), optional=True)
            operations[value["operation_id"]] = (value["order_id"], value["order_line_id"])
        executions = {}
        for value in state.get("execution_records", []):
            if value["operation_id"] not in operations:
                raise ValueError("fixture_execution_unrelated")
            pair = operations[value["operation_id"]]
            if (value.get("order_id", pair[0]), value.get("order_line_id", pair[1])) != pair:
                raise ValueError("fixture_execution_line_mismatch")
            if value.get("customer_id", scope["customer_id"]) != scope["customer_id"] or value.get("branch_id", row["branch_id"]) != row["branch_id"]:
                raise ValueError("fixture_execution_scope_mismatch")
            integer(value.get("amount_minor"), optional=True)
            executions[value["execution_id"]] = value["operation_id"]
        for value in state.get("operations", []):
            if any(executions.get(eid) != value["operation_id"] for eid in value.get("execution_ids", [])):
                raise ValueError("fixture_operation_execution_mismatch")
        for value in state.get("shipments", []) + state.get("returns", []):
            self.relation(value, lines, scope, row)
            pair = (value["order_id"], value.get("order_line_id", value.get("line_id")))
            op, ex = value.get("operation_id"), value.get("execution_id")
            if op and operations.get(op) != pair or ex and executions.get(ex) != op:
                raise ValueError("fixture_ledger_unrelated")
            if "quantity" in value:
                integer(value["quantity"], minimum=1)
        for stock in state.get("inventory", []):
            if stock["item_id"] not in self.by_sku and stock["item_id"] not in self.by_part:
                raise ValueError("fixture_inventory_not_registered")
            integer(stock["on_hand"]); integer(stock["reserved"])
            if stock["reserved"] > stock["on_hand"]:
                raise ValueError("fixture_inventory_invalid")
        for message in row["initial_messages"]:
            timestamp(message["received_at"])
        for choice in state.get("customer_choices", []):
            integer(choice.get("amount_minor"), optional=True)
            if choice.get("quantity") is not None:
                integer(choice["quantity"], minimum=1)

    @staticmethod
    def relation(value, lines, scope, row):
        if lines.get(value.get("order_line_id", value.get("line_id"))) != value["order_id"]:
            raise ValueError("fixture_line_unrelated")
        if value.get("customer_id", scope["customer_id"]) != scope["customer_id"]:
            raise ValueError("fixture_ledger_customer_mismatch")
        if value.get("branch_id", row["branch_id"]) != row["branch_id"]:
            raise ValueError("fixture_ledger_branch_mismatch")

    def list(self):
        categories = {"BIZ-01": "产品咨询", "BIZ-02": "故障排查", "BIZ-03": "物流查询", "BIZ-04": "退款",
                      "BIZ-05": "退货", "BIZ-06": "换货", "BIZ-07": "补寄配件"}
        return {"items": [{"scenario_id": r["scenario_id"], "label": "、".join(categories.get(c, c)
            for c in r["business_categories"]) + " · " + r["scenario_id"], "mode":
            "interactive_simulation" if r["mode"] == "simulation" else "historical_replay",
            "brand": r["conversation"]["brand"], "business_categories": r["business_categories"]}
            for r in self.scenarios.values()]}

    def catalog(self, conn, workspace):
        from uuid import uuid4
        registered = {}
        for kind, records, path in (("product", self.products, "products.json"), ("part", self.parts, "parts.json")):
            for record in records:
                item = record["sku"] if kind == "product" else record["part_id"]
                values = dict(id=uuid4(), workspace_id=workspace, item_id=item, sku=item,
                    brand=record["brand"], kind=kind, version="v1", **source_values(record, path,
                    record.get("source_kind", record.get("identity_source", "unknown"))))
                self.ensure(conn, products, values, ["workspace_id", "item_id", "version"])
                registered[item] = conn.execute(select(products.c.id).where(products.c.workspace_id == workspace,
                    products.c.item_id == item, products.c.version == "v1")).scalar_one()
        for record in self.compatibility:
            values = dict(id=uuid4(), workspace_id=workspace, sku=record["sku"], item_id=record["part_id"],
                hardware_revision=record["hardware_revision"], version="v1", **source_values(record, "compatibility.json"))
            self.ensure(conn, compatibility, values, ["workspace_id", "sku", "item_id", "hardware_revision", "version"])
        record = self.policy
        values = dict(id=uuid4(), workspace_id=workspace, policy_id=record["policy_id"], version=record["version"],
            available_at=timestamp(record["available_at"]), publication_status="unpublished",
            description=self.description, **source_values(record, "policies/policy-profile.json"))
        self.ensure(conn, policy_profiles, values, ["workspace_id", "policy_id", "version"])
        policy_id = conn.execute(select(policy_profiles.c.id).where(policy_profiles.c.workspace_id == workspace,
            policy_profiles.c.policy_id == record["policy_id"], policy_profiles.c.version == record["version"])).scalar_one()
        return registered, policy_id

    @staticmethod
    def ensure(conn, table, values, keys):
        conn.execute(insert(table).values(**values).on_conflict_do_nothing(index_elements=[table.c[k] for k in keys]))
        stored = conn.execute(select(table.c.source_hash).where(*[table.c[k] == values[k] for k in keys])).scalar_one()
        if stored != values["source_hash"]:
            raise ValueError("immutable_fixture_changed")
        if table is policy_profiles:
            readable = conn.execute(select(table.c.description).where(*[table.c[k] == values[k] for k in keys])).scalar_one()
            if readable != values["description"]:
                raise ValueError("immutable_policy_description_changed")
