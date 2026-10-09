"""Deliver one gated external event through the actual application services."""
from uuid import UUID
import sqlalchemy as sa
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.adapters.conversation_schema import domain_events, messages
from globalmail_agent.application.conversation_lock import lock_conversation, ServiceError
from globalmail_agent.application.business_read_model import scope_where
from globalmail_agent.application.simulation_control import SimulationControlService
from globalmail_agent.application.branch_facts import BranchFactsService
from globalmail_agent.domain.conversation import AppendMessage, Takeover, HumanReply, Close
from globalmail_agent.domain.executions import SimulationEvent
from globalmail_agent.domain.business_events import BranchFact
from globalmail_agent.domain.orders import timestamp
from globalmail_agent.evaluation.service_gates import selected_operation
from globalmail_agent.evaluation.journey_driver import CommitResult


def deliver(adapter, delivery, resources, command_id, authorization):
    cid = UUID(resources["conversation_id"])
    with adapter.engine.begin() as conn:
        conv = lock_conversation(conn, cid)
        branch = conn.execute(sa.select(b.simulation_branches).where(b.simulation_branches.c.id == conv["branch_id"])).mappings().one()
        when = timestamp(delivery["not_before"])
        if when > branch["clock"]:
            conn.execute(b.simulation_branches.update().where(b.simulation_branches.c.id == branch["id"]).values(clock=when))
    observation = adapter.observe(delivery["scenario_id"], resources)
    conv = observation["conversation"]
    payload, kind = delivery["payload"], delivery["kind"]
    record = payload.get("record", payload)
    mapping, refs = {}, []
    if kind == "customer_message":
        result = adapter.conversations.append(cid, AppendMessage(expected_version=conv["row_version"],
            body=payload.get("body", payload.get("text", "")), source_message_id=payload.get("message_id", delivery["event_id"])), command_id)
        with adapter.engine.connect() as conn:
            message = conn.execute(sa.select(messages).where(messages.c.conversation_id == cid,
                messages.c.source_message_id == payload.get("message_id", delivery["event_id"]))).mappings().one()
        mapping["message:" + delivery["event_id"]] = str(message["id"])
        refs.append("message:" + str(message["id"]))
    elif kind in {"human_reply", "human_close"}:
        staff = authorization.get("staff_id")
        if not staff:
            return CommitResult(False, reason="staff_identity_required")
        if kind == "human_close":
            reason = authorization.get("resolution_reason")
            if not reason:
                return CommitResult(False, reason="resolution_reason_required")
            result = adapter.conversations.close(cid, Close(expected_version=conv["row_version"],
                note=staff + ": " + reason), command_id)
        else:
            if conv["processing_owner"] != "human_review":
                adapter.conversations.takeover(cid, Takeover(expected_version=conv["row_version"], reason="控制器人工回复"), command_id + ":takeover")
                conv = adapter.conversations.detail(cid)["conversation"]
            result = adapter.conversations.human_reply(cid, HumanReply(expected_version=conv["row_version"],
                expected_input_revision=conv["input_revision"], body=payload.get("body", payload.get("text", "")),
                note="控制器人工：" + staff), command_id)
        refs.append("human_action:" + result["review_id"] if result.get("review_id") else "conversation:" + str(cid))
    else:
        operation = selected_operation({**delivery, "gate": {}}, observation)
        if not operation and resources.get("operation_id"):
            operation = next((r for r in observation["ledger"]["operations"] if r["operation_id"] == resources["operation_id"]
                and record.get("order_line_id", r["order_line_id"]) == r["order_line_id"]), None)
        original = next((r for r in observation["business"]["shipments"] if not r.get("operation_id") and
            r.get("parcel_id") == record.get("parcel_id")), None) if kind == "shipment_update" else None
        returned = next((r for r in observation["ledger"]["returns"] if r.get("return_id") == resources.get(
            "resource:" + record.get("return_id", ""))), None) if kind == "return_update" else None
        if original or returned and (returned.get("inspection") in {"failed", "disputed"} or record.get("document_version", 1) > 1):
            event = "original_shipment" if original else "inspection_correction" if record.get("inspection") in {"passed", "failed", "disputed"} else "return_documents"
            row = original or returned
            result = _correction_delivery(adapter, cid, row, record, event, delivery, authorization, command_id)
        elif kind in {"execution_record", "execution_created", "refund_succeeded", "execution_failed", "execution_unknown", "shipment_update", "return_update"}:
            if not operation:
                return CommitResult(False, reason="actual_operation_missing_or_ambiguous")
            result, mapping = _operation_delivery(adapter, cid, operation, record, kind, delivery, resources, command_id, authorization)
        elif kind in {"inventory_update", "address_update", "service_note"}:
            result = _fact_delivery(adapter, cid, record, kind, delivery, authorization, command_id)
        else:
            return CommitResult(False, reason="unsupported_current_controller_event:" + kind)
        refs.append("business_event:" + result["event_id"])
        with adapter.engine.connect() as conn:
            event = conn.execute(sa.select(domain_events.c.id).where(domain_events.c.conversation_id == cid,
                sa.or_(domain_events.c.id == UUID(result["event_id"]),
                    domain_events.c.source_event_id.startswith(result["event_id"] + ":")))) .scalar()
        if event:
            mapping["event:" + delivery["event_id"]] = str(event)
    return CommitResult(True, tuple(refs), mapping, (result["run_id"],) if result.get("run_id") else ())


def _operation_delivery(adapter, cid, operation, record, kind, delivery, resources, command_id, authorization):
    service = SimulationControlService(adapter.engine, adapter.store)
    bid = UUID(resources["branch_id"])
    fields, mapping = {}, {}
    status = record.get("status")
    event = {"accepted": "create_execution", "processing": "processing", "succeeded": "succeeded",
        "failed": "failed", "unknown": "unknown", "cancelled": "cancellation_acknowledged"}.get(status)
    if kind == "execution_created":
        event = "create_execution"
    elif kind == "refund_succeeded":
        event = "succeeded"
    elif kind.startswith("execution_") and kind in {"execution_failed", "execution_unknown"}:
        event = kind.removeprefix("execution_")
    elif kind == "shipment_update":
        event = {"in_transit": "shipped", "label_created": "label_created", "shipped": "shipped", "delivered": "delivered"}.get(status)
    elif kind == "return_update":
        event = "inspected" if record.get("inspection") in {"passed", "failed", "disputed"} else {
            "authorized": "label_created", "in_transit": "return_in_transit", "received": "received"}.get(status)
        if event == "label_created":
            address = record.get("address")
            fields.update(return_address=", ".join(str(v) for k, v in address.items() if k != "source_kind") if isinstance(address, dict) else address,
                packing_instructions=record.get("instructions"), postage_responsibility=record.get("postage_payer"),
                prepaid_label_ref=record.get("label_reference", record.get("prepaid_label_ref")))
    if event is None:
        return _blocked("controller_status_not_supported")
    if record.get("correction_of_execution_id"):
        event = "create_corrective_execution"
        origin = resources.get("resource:" + record["correction_of_execution_id"])
        if not origin:
            return _blocked("original_actual_execution_required")
        fields.update(correction_of_execution_id=origin, staff_id=authorization.get("staff_id"),
            reason=record.get("correction_reason", record.get("reason", delivery["payload"].get("text"))))
    fields.update({k: record[k] for k in ("quantity", "tracking_number", "carrier", "confirmed_not_executed") if k in record})
    fields["receipt_ref"] = record.get("receipt_ref", record.get("return_reference", record.get("payment_reference")))
    # Current external event ID is a simulation observation reference, not a guessed provider success.
    if not fields["receipt_ref"]:
        fields["receipt_ref"] = delivery["event_id"]
    if event in {"failed", "unknown", "cancellation_acknowledged"}:
        fields["reason"] = record.get("failure_code", delivery["payload"].get("text"))
    if event == "inspected":
        fields["reason"] = record["inspection"]
        # Compound warehouse observations are applied through both legal transitions.
        if record.get("received") and "received" in operation["allowed_events"]:
            _push(service, adapter, cid, bid, operation["operation_id"], "received", command_id + ":received",
                quantity=record.get("quantity"), receipt_ref=fields["receipt_ref"])
    if record.get("confirmed_not_executed") and status == "failed":
        event = "reconciled_not_executed"
    result = _push(service, adapter, cid, bid, operation["operation_id"], event, command_id, **fields)
    alias = record.get("execution_id") or record.get("return_id") or record.get("parcel_id")
    rows = result.get("executions", []) if record.get("execution_id") else result.get("returns", []) if record.get("return_id") else result.get("shipments", [])
    if alias and rows:
        field = "execution_id" if record.get("execution_id") else "return_id" if record.get("return_id") else "parcel_id"
        if rows[-1].get(field):
            mapping["resource:" + alias] = rows[-1][field]
    return result, mapping


def _push(service, adapter, cid, bid, op, event, key, **fields):
    ledger = adapter.sales.listing(cid, op)["data"]
    current = ledger["operations"][0]
    return service.event(bid, SimulationEvent(conversation_id=cid, expected_version=ledger["conversation_version"],
        operation_id=op, expected_operation_version=current["version"], event=event, **fields), key)


def _fact_delivery(adapter, cid, record, kind, delivery, authorization, key):
    if not authorization.get("staff_id"):
        return _blocked("staff_identity_required")
    conv = adapter.conversations.detail(cid)["conversation"]
    name = {"inventory_update": "inventory_snapshot", "address_update": "address_confirmation", "service_note": "service_note"}[kind]
    fields = {k: record[k] for k in BranchFact.model_fields if k in record}
    fields.update(conversation_id=cid, expected_version=conv["row_version"], source_event_id=delivery["event_id"],
        event=name, staff_id=authorization["staff_id"], receipt_ref=delivery["event_id"], reason=delivery["payload"].get("text"))
    if "order_line_id" not in fields:
        data = adapter.business.detail(cid)["data"]
        lines = [l for o in data["orders"] for l in o["lines"]]
        if len(lines) != 1:
            return _blocked("order_line_id_required")
        fields["order_line_id"] = lines[0]["line_id"]
    fields.setdefault("expected_business_version", 0)
    fields.setdefault("business_version", record.get("version", 1))
    return BranchFactsService(adapter.engine, adapter.store).event(UUID(str(conv["branch_id"])), BranchFact.model_validate(fields), key)


def _blocked(reason):
    raise ServiceError(reason, 422)


def _correction_delivery(adapter, cid, row, record, event, delivery, authorization, key):
    if not authorization.get("staff_id"):
        return _blocked("staff_identity_required")
    conv = adapter.conversations.detail(cid)["conversation"]
    identity = row.get("return_id") or row["parcel_id"]
    with adapter.engine.connect() as conn:
        branch = conn.execute(sa.select(b.simulation_branches).where(b.simulation_branches.c.id == conv["branch_id"])).mappings().one()
        version = branch["state"].get("business_fact_versions", {}).get(event + ":" + identity, 0)
    fields = {k: record[k] for k in ("quantity", "inspection", "carrier", "tracking_number") if k in record}
    if event == "original_shipment":
        fields["status"] = "shipped" if record.get("status") == "in_transit" else record.get("status")
    if event == "return_documents":
        address = record.get("address")
        fields.update(return_address=", ".join(str(v) for k, v in address.items() if k != "source_kind") if isinstance(address, dict) else address,
            packing_instructions=record.get("instructions"), postage_responsibility=record.get("postage_payer"),
            prepaid_label_ref=record.get("prepaid_label_ref", record.get("label_reference")))
    command = BranchFact(conversation_id=cid, expected_version=conv["row_version"], source_event_id=delivery["event_id"],
        order_line_id=row["order_line_id"], resource_id=identity, expected_resource_version=row["version"], event=event,
        expected_business_version=version, business_version=version + 1, staff_id=authorization["staff_id"],
        receipt_ref=delivery["event_id"], reason=delivery["payload"]["text"], **fields)
    return BranchFactsService(adapter.engine, adapter.store).event(UUID(str(conv["branch_id"])), command, key)
