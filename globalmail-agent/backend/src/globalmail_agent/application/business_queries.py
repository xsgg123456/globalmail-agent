"""Pure scoped queries and internal eligibility context, read in one PG snapshot."""
from sqlalchemy.exc import SQLAlchemyError
from globalmail_agent.application.business_read_model import read_model
from globalmail_agent.application.business_customer_view import customer_view
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
from globalmail_agent.domain.orders import result, verified
from globalmail_agent.domain.inventory import compatible


class BusinessQueries:
    def __init__(self, engine, workspace_id=DEFAULT_WORKSPACE_ID):
        self.engine, self.workspace_id = engine, workspace_id

    def read(self, conversation_id, callback):
        if self.engine is None:
            return result("error", "database_unavailable", retryable=True)
        try:
            with self.engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
                with conn.begin():
                    return callback(read_model(conn, conversation_id, self.workspace_id))
        except SQLAlchemyError:
            return result("error", "database_unavailable", retryable=True)
        except (ValueError, KeyError, TypeError):
            return result("error", "business_data_invalid", retryable=False)

    @staticmethod
    def response(model, status="ok", code="business_snapshot", data=None):
        branch = model["branch"]
        versions = {"conversation": model["conversation"]["row_version"]}
        if branch:
            versions.update(branch_generation=branch["generation"], source_hash=branch["source_hash"])
        if model["policy_metadata"]:
            versions["policy"] = model["policy_metadata"]["version"]
        refs = [] if not branch else [{"evidence_id": "branch:" + str(branch["id"]),
            "source_kind": branch["source_kind"], "source_hash": branch["source_hash"],
            "source_ref": branch["source_ref"]}]
        return result(status, code, data, simulation=model["conversation"]["mode"] == "simulation",
            source_kind=branch["source_kind"] if branch else "unknown", observed_at=model["observed_at"],
            resource_versions=versions, evidence_refs=refs, retryable=status == "error")

    @staticmethod
    def selected(model, line_id=None, order_number=None):
        candidates = model["lines"]
        if order_number:
            candidates = [item for item in candidates if item[2]["display_order_number"] == order_number]
        if line_id:
            candidates = [item for item in candidates if item[1]["line_id"] == line_id]
        return candidates[0] if len(candidates) == 1 else None

    @staticmethod
    def failure(model, data):
        if model["unavailable"]:
            return ("unavailable", "historical_snapshot_unavailable" if model["future"] else "historical_source_unavailable")
        if not model["orders"]:
            return ("empty", "scoped_order_not_found")
        return None

    @staticmethod
    def override(model, tool):
        if not model["branch"] or model["conversation"]["mode"] != "simulation":
            return None
        injected = next((o for o in model["branch"]["tool_overrides"] if o.get("tool") == tool), None)
        if not injected:
            return None
        if injected.get("fault") in {"query_failed", "timeout", "technical_error"}:
            return ("error", "simulated_query_failure")
        if injected.get("fault") in {"not_found", "empty"}:
            return ("empty", "simulated_record_not_found")
        return None

    def detail(self, conversation_id, order_number=None, order_line_id=None):
        def query(model):
            data = {"scenario_id": model["branch"]["scenario_id"] if model["branch"] else None,
                "as_of": model["as_of"].isoformat() if model["as_of"] else None,
                "orders": model["orders"], "selected_line_id": None,
                **{k: model[k] for k in ("shipments", "operations", "executions", "returns")},
                "missing_fields": [], "policy": model["policy_metadata"], **customer_view(model)}
            failure = self.failure(model, data) or self.override(model, "get_order_snapshot")
            if failure:
                data.update(orders=[], shipments=[], operations=[], executions=[], returns=[], policy=None,
                    customer_choices=[], address_confirmation=None, missing_fields=["order_snapshot"])
                return self.response(model, *failure, data)
            if order_number and not any(o["display_order_number"] == order_number for o in model["orders"]):
                return self.response(model, "denied", "order_out_of_scope", None)
            if order_line_id and not any(l[1]["line_id"] == order_line_id for l in model["lines"]):
                return self.response(model, "denied", "order_line_out_of_scope", None)
            selected = self.selected(model, order_line_id, order_number)
            if order_line_id and order_number and selected is None:
                return self.response(model, "conflict", "order_line_order_mismatch", None)
            if selected is None:
                data["missing_fields"].append("order_line_id")
                return self.response(model, "needs_input", "target_order_line_required", data)
            if order_number:
                data["orders"] = [o for o in data["orders"] if o["display_order_number"] == order_number]
            data["selected_line_id"] = selected[1]["line_id"]
            data["missing_fields"] = selected[1]["unknown_fields"]
            return self.response(model, data=data)
        return self.read(conversation_id, query)

    def availability(self, conversation_id, order_line_id=None, item_id=None):
        def query(model):
            failure = self.failure(model, None) or self.override(model, "get_item_availability")
            if failure:
                return self.response(model, *failure, None)
            selected = self.selected(model, order_line_id)
            if not selected:
                code = "order_line_out_of_scope" if order_line_id else "target_order_line_required"
                return self.response(model, "denied" if order_line_id else "needs_input", code,
                    {"missing_fields": ["order_line_id"]})
            _, line, order = selected
            if not item_id:
                return self.response(model, "needs_input", "target_item_required", {"missing_fields": ["item_id"]})
            if model["conversation"]["mode"] != "simulation":
                return self.response(model, "unavailable", "historical_inventory_unavailable", None)
            if item_id not in model["products"] and not any(p["part_id"] == item_id for p in model["parts"]):
                return self.response(model, "denied", "item_not_registered", None)
            matches = [c for c in model["compatibility"] if c["part_id"] == item_id and c["sku"] == line["sku"]
                and c["hardware_revision"] == line.get("hardware_revision")]
            exact = compatible(line, item_id, matches)
            stock = [s for s in model["inventory"] if s["item_id"] == item_id]
            data = {"item_id": item_id, "order_line_id": line["line_id"], "compatible": exact,
                "available_quantity": None, "on_hand": None, "reserved": None,
                "source_kind": "synthetic", "snapshot_at": None, "missing_fields": []}
            if len(stock) == 1:
                data.update(on_hand=stock[0]["on_hand"], reserved=stock[0]["reserved"], snapshot_at=stock[0]["snapshot_at"])
                if stock[0]["snapshot_at"] is None:
                    data["missing_fields"].append("inventory.snapshot_at")
            if model["state"].get("compatibility_override") == "unknown":
                exact = data["compatible"] = None
                data["missing_fields"].append("compatibility")
            if exact is False:
                return self.response(model, "denied", "item_incompatible", data)
            if exact is None:
                data["missing_fields"].append("hardware_revision")
            if item_id != line["sku"] and not any(c.get("region_spec", c.get("market")) == order.get("market") for c in matches):
                data["compatible"] = None
                data["missing_fields"].append("compatibility.region_spec")
            usable = [s for s in stock if s["region_spec"] == order.get("market")
                and s["hardware_revision"] == line.get("hardware_revision")]
            if not usable:
                data["missing_fields"].extend(["inventory.region_spec", "inventory.hardware_revision"] if stock else ["inventory"])
                return self.response(model, "unknown", "inventory_scope_unknown", data)
            if len(usable) != 1:
                return self.response(model, "unknown", "inventory_snapshot_ambiguous", data)
            current = usable[0]
            if current["snapshot_at"] is None:
                return self.response(model, "unknown", "inventory_snapshot_time_unknown", data)
            data.update(available_quantity=current["on_hand"] - current["reserved"],
                on_hand=current["on_hand"], reserved=current["reserved"], source_kind=current["source_kind"],
                snapshot_at=current["snapshot_at"])
            return self.response(model, "unknown" if data["missing_fields"] else "ok",
                "compatibility_unknown" if data["missing_fields"] else "branch_inventory_snapshot", data)
        return self.read(conversation_id, query)

    def eligibility_context(self, conversation_id, order_line_id=None):
        def query(model):
            failure = self.failure(model, None)
            if failure:
                return self.response(model, *failure, None)
            selected = self.selected(model, order_line_id)
            if not selected:
                return self.response(model, "denied" if order_line_id else "needs_input",
                    "order_line_out_of_scope" if order_line_id else "target_order_line_required", None)
            if model["conversation"]["mode"] != "simulation":
                return self.response(model, "unavailable", "historical_policy_unavailable", None)
            row, line, order = selected
            ref = "branch:" + str(model["branch"]["id"])
            facts = {k: [verified(x, ref + ":" + k + ":" + str(i)) for i, x in enumerate(model[key])]
                for k, key in (("operations", "operations"), ("execution_records", "executions"),
                    ("shipments", "shipments"), ("returns", "returns"), ("inventory", "inventory"))}
            single = len(model["lines"]) == 1
            state = {**model["state"], **facts, "verified_fixture": single, "evidence_ref": ref}
            if not single:
                state.pop("defect_confirmed_in_simulation", None); state.pop("confirmed_missing_part_id", None)
            if single and state.get("defect_confirmed_in_simulation") is True:
                state["problem_evidence"] = [{"order_line_id": line["line_id"], "reason": "defect",
                    "source_kind": "verified_fixture", "evidence_ref": ref + ":defect"}]
            requested = state.get("return_request_details")
            if single and requested and requested.get("reason") == "unwanted":
                state["problem_evidence"] = [{"order_line_id": line["line_id"], "reason": "unwanted",
                    "source_kind": "verified_fixture", "evidence_ref": ref + ":return_request"}]
                if requested.get("condition") == "unused_complete":
                    state["return_condition"] = {"unused": True, "complete": True,
                        "source_kind": "verified_fixture", "evidence_ref": ref + ":return_condition"}
            for choice in state["customer_choices"]:
                choice["action"] = choice.get("kind")
                if len(model["lines"]) == 1 and line["quantity"] == 1:
                    choice.setdefault("order_line_id", line["line_id"]); choice.setdefault("quantity", 1)
            exact = [c for c in model["compatibility"] if c["sku"] == line["sku"]
                     and c["hardware_revision"] == line.get("hardware_revision")]
            compatibility = [verified(c, ref + ":compatibility:" + str(i)) for i, c in enumerate(exact)]
            state["compatibility"] = compatibility
            data = {"order": verified(order, ref + ":order"), "line": verified(line, "line:" + str(row["id"])),
                "as_of": model["as_of"].isoformat(), "mode": model["conversation"]["mode"],
                "state": state, "policy": model["policy"], "policy_metadata": model["policy_metadata"],
                "product": verified(model["products"][line["sku"]], ref + ":product") if line["sku"] in model["products"] else None,
                "parts": [verified(p, ref + ":part:" + p["part_id"]) for p in model["parts"] if any(c["part_id"] == p["part_id"] for c in exact)],
                "compatibility": compatibility}
            data["order"]["line_count"] = len(order["lines"])
            return self.response(model, data=data)
        return self.read(conversation_id, query)
