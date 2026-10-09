"""Named controller gates inspect current real ledger; missing premises remain blocked."""
from globalmail_agent.evaluation.journey_gates import GateResult


def selected_operation(event, observation):
    selector = event.get("gate", {}).get("operation_required") or event.get("trigger_condition", {}).get(
        "after_matching_internal_request") or event.get("payload", {}).get("operation_selector")
    if not selector:
        record = event.get("payload", {}).get("record", event.get("payload", {}))
        selector = {k: record[k] for k in ("kind", "order_id", "order_line_id") if record.get(k)}
    selector = dict(selector or {})
    if selector.get("kind") == "investigation":
        selector["kind"] = "logistics"
    rows = observation["ledger"]["operations"]
    if not selector:
        return None
    matches = [r for r in rows if all(r.get(k) == v for k, v in selector.items() if k in {"kind", "order_id", "order_line_id"})]
    return matches[0] if len(matches) == 1 else None


def verify_business_gate(adapter, name, event, observation, resources):
    operation = selected_operation(event, observation)
    if not operation:
        return GateResult(name, reason="matching_actual_operation_missing_or_ambiguous")
    op_id = operation["operation_id"]
    records = observation["ledger"]
    attempts = [r for r in records["executions"] if r.get("operation_id") == op_id]
    parcels = [r for r in records["shipments"] if r.get("operation_id") == op_id]
    returns = [r for r in records["returns"] if r.get("order_line_id") == operation["order_line_id"]]
    record = event.get("payload", {}).get("record", event.get("payload", {}))
    plan = operation.get("plan", {})
    passed = False
    reason = "current_business_premise_missing"
    proof = ["operation:" + op_id, "version:" + str(operation["version"])]
    if name in {"actual_internal_request_exists", "after_matching_internal_request"}:
        passed = operation.get("managed") is True and operation["status"] != "cancelled"
    elif name == "after_internal_return_request":
        matched = [r for r in records["operations"] if r.get("managed") and r["kind"] == "return" and r["status"] != "cancelled"
            and r.get("order_id") == operation.get("order_id") and r.get("order_line_id") == operation.get("order_line_id")
            ]
        passed = bool(matched)
        proof.extend("return_operation:" + r["operation_id"] + ":version:" + str(r["version"]) for r in matched)
    elif name == "result_matches_original_request":
        passed = all(record.get(k, operation.get(k)) == operation.get(k) for k in ("order_id", "order_line_id", "quantity"))
    elif name == "authorized_refund_amount_and_currency_match":
        passed = operation["kind"] == "refund" and all(record.get(k) == operation.get(k) for k in ("amount_minor", "currency"))
    elif name == "no_duplicate_refund_result":
        passed = sum(r.get("status") == "succeeded" for r in attempts) <= 1
    elif name == "legal_execution_status_transition":
        status = record.get("status")
        allowed = {"accepted": "create_execution", "processing": "processing", "succeeded": "succeeded", "failed": "failed", "unknown": "unknown"}
        transition = allowed.get(status)
        if record.get("correction_of_execution_id"):
            transition = "create_corrective_execution"
        elif record.get("confirmed_not_executed"):
            transition = "cancellation_acknowledged" if status == "cancelled" else "reconciled_not_executed"
        elif event["kind"] == "shipment_update":
            transition = {"in_transit": "shipped", "label_created": "label_created", "shipped": "shipped", "delivered": "delivered"}.get(status)
        elif event["kind"] == "return_update":
            transition = "inspected" if record.get("inspection") in {"passed", "failed", "disputed"} else {
                "authorized": "label_created", "in_transit": "return_in_transit", "received": "received"}.get(status)
            if transition == "inspected" and record.get("received") and "received" in operation.get("allowed_events", ()):
                transition = "received"
        passed = transition is not None and transition in operation.get("allowed_events", ())
    elif name == "confirmed_current_address_version":
        address = observation["business"].get("address_confirmations", {}).get(operation["order_line_id"],
            observation["business"].get("address_confirmation")) or {}
        passed = address.get("confirmed") is True and address.get("version") == plan.get("address_version")
    elif name == "cancellation_requested":
        passed = operation.get("cancellation_requested") is True
    elif name == "no_dispatch_confirmed":
        passed = not any(p.get("status") in {"shipped", "delivered"} for p in parcels) and bool(record.get("confirmed_not_executed"))
    elif name == "release_original_reservations":
        # Prospective gate permits the explicit acknowledgment, never a guessed cancellation.
        passed = "cancellation_acknowledged" in operation.get("allowed_events", ()) and bool(record.get("confirmed_not_executed"))
    elif name in {"return_inspection_or_recorded_exception_before_dispatch", "return_inspection_or_recorded_exception_for_full_refund"}:
        line = next((l for o in observation["business"]["orders"] for l in o["lines"] if l["line_id"] == operation["order_line_id"]), {})
        is_full = operation.get("amount_minor") == line.get("paid_minor")
        passed = name.endswith("full_refund") and not is_full or any(
            r.get("received") and r.get("inspection") == "passed" and r.get("quantity") == operation["quantity"] for r in returns)
    elif name in {"customer_choice_valid", "explicit_amount_acceptance_for_partial_refund", "refund_balance_available", "stock_available_before_dispatch", "exact_item_compatible"}:
        # Recheck uses the current published policy, real selection/address and same ledger.
        try:
            from globalmail_agent.application.conversation_lock import lock_conversation
            from globalmail_agent.application.after_sales_ledger import operation_row
            from globalmail_agent.application.simulation_execution import recheck
            from globalmail_agent.adapters.business_schema import simulation_branches
            import sqlalchemy as sa
            from uuid import UUID
            with adapter.engine.begin() as conn:
                conv = lock_conversation(conn, UUID(resources["conversation_id"]))
                branch = conn.execute(sa.select(simulation_branches).where(simulation_branches.c.id == conv["branch_id"])).mappings().one()
                original = operation_row(conn, conv, op_id, lock=True)
                recheck(conn, adapter.store, conv, branch, original)
                passed = True
        except Exception as error:
            reason = "recheck:" + getattr(error, "code", type(error).__name__)
    return GateResult(name, "passed" if passed else "blocked", "ledger_verified" if passed else reason,
        tuple(proof), {"operation_id": op_id})
