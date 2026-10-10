"""Explicit scenario staff facts update the same ledger and retain immutable event history."""
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.adapters.conversation_schema import conversations, domain_events, messages
from globalmail_agent.application.business_read_model import scope_where
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError, lock_conversation
from globalmail_agent.application.idempotency import prior, remember
from globalmail_agent.application.event_store import record_event, append_ui_event
from globalmail_agent.application.after_sales_selection import visible_quote
from globalmail_agent.domain.business_events import BranchFact
from globalmail_agent.knowledge.base import canonical, sha


class BranchFactsService:
    def __init__(self, engine, store, workspace_id=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.workspace_id = engine, store, workspace_id

    def event(self, branch_id, command, key):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)
        command = command if isinstance(command, BranchFact) else BranchFact.model_validate(command)
        payload = command.model_dump(mode="json")
        name = "branch-fact:" + str(branch_id)
        with self.engine.begin() as conn:
            old, digest = prior(conn, self.workspace_id, key, name, payload)
            if old is not None:
                return old
            conv = lock_conversation(conn, command.conversation_id, self.workspace_id)
            if conv["mode"] != "simulation" or conv["branch_id"] != branch_id:
                raise ServiceError("simulation_branch_out_of_scope", 422)
            existing = conn.execute(sa.select(domain_events).where(domain_events.c.conversation_id == conv["id"],
                domain_events.c.source == "branch_fact", domain_events.c.source_event_id == command.source_event_id)).mappings().first()
            if existing:
                if existing["payload"] != payload:
                    raise ServiceError("business_event_id_conflict")
                return {"conversation_id": str(conv["id"]), "event_id": str(existing["id"]), "status": existing["status"], "duplicate": True}
            if conv["row_version"] != command.expected_version:
                raise ServiceError("stale_version")
            branch = conn.execute(sa.select(b.simulation_branches).where(b.simulation_branches.c.id == branch_id,
                *scope_where(b.simulation_branches, conv))).mappings().one()
            lines = conn.execute(sa.select(b.branch_order_lines).where(*scope_where(b.branch_order_lines, conv))
                .order_by(b.branch_order_lines.c.id).with_for_update()).mappings().all()
            line = next((l for l in lines if command.order_line_id in {str(l["id"]), l["external_id"]}), None)
            if not line:
                raise ServiceError("order_line_out_of_scope", 422)
            order = conn.execute(sa.select(b.branch_orders).where(b.branch_orders.c.id == line["order_id"])).mappings().one()
            state = dict(branch["state"])
            resource = command.event + ":" + (command.resource_id or command.item_id or command.order_line_id)
            versions = dict(state.get("business_fact_versions", {}))
            current = versions.get(resource, 0)
            if command.expected_business_version != current or command.business_version != current + 1:
                raise ServiceError("stale_business_version")
            self._apply(conn, conv, branch, line, order, state, command)
            versions[resource] = command.business_version
            state["business_fact_versions"] = versions
            conn.execute(b.simulation_branches.update().where(b.simulation_branches.c.id == branch_id).values(state=state))
            event = record_event(conn, conv, "branch_fact", command.source_event_id, command.event, payload, suppressed=True)
            conn.execute(domain_events.update().where(domain_events.c.id == event["id"]).values(business_version=command.business_version))
            from globalmail_agent.application.task_queue import invalidate
            invalidate(conn, conv["id"])
            conn.execute(conversations.update().where(conversations.c.id == conv["id"]).values(
                input_revision=conv["input_revision"] + 1, row_version=conv["row_version"] + 1,
                scheduling_state="idle"))
            status = "facts_updated"
            conn.execute(domain_events.update().where(domain_events.c.id == event["id"]).values(status=status))
            append_ui_event(conn, conv["id"], "simulation.fact", {"event_id": str(event["id"]), "event": command.event,
                "version": command.business_version, "wake_status": status})
            response = {"conversation_id": str(conv["id"]), "event_id": str(event["id"]), "status": status, "business_version": command.business_version}
            remember(conn, self.workspace_id, key, name, digest, response)
            return response

    def _apply(self, conn, conv, branch, line, order, state, command):
        if command.event == "inventory_snapshot":
            if not all([command.item_id, command.region_spec, command.hardware_revision, command.snapshot_at]) or command.on_hand is None:
                raise ServiceError("inventory_specification_and_snapshot_required", 422)
            if command.region_spec != order["source_snapshot"]["market"] or command.hardware_revision != line["hardware_revision"]:
                raise ServiceError("inventory_specification_mismatch", 422)
            known = conn.execute(sa.select(b.products.c.id).where(b.products.c.workspace_id == self.workspace_id,
                b.products.c.item_id == command.item_id)).first()
            if not known or command.snapshot_at > branch["clock"]:
                raise ServiceError("inventory_source_invalid", 422)
            stock = conn.execute(sa.select(b.inventory).where(*scope_where(b.inventory, conv),
                b.inventory.c.item_id == command.item_id, b.inventory.c.region_spec == command.region_spec,
                b.inventory.c.hardware_revision == command.hardware_revision).with_for_update()).mappings().first()
            if stock and (command.on_hand < stock["reserved"] or stock["snapshot_at"] and command.snapshot_at < stock["snapshot_at"]):
                raise ServiceError("inventory_change_conflict")
            values = dict(on_hand=command.on_hand, snapshot_at=command.snapshot_at,
                source_kind="scenario_console_manual", source_ref=command.receipt_ref,
                source_hash=sha(canonical(command.model_dump(mode="json"))), source_snapshot=command.model_dump(mode="json"))
            if stock:
                conn.execute(b.inventory.update().where(b.inventory.c.id == stock["id"]).values(
                    on_hand=command.on_hand, snapshot_at=command.snapshot_at,
                    details={"source_kind": values["source_kind"], "source_ref": values["source_ref"],
                        "source_hash": values["source_hash"], "version": command.business_version}))
            else:
                conn.execute(sa.insert(b.inventory).values(id=uuid4(), **{k: conv[k] for k in b.SCOPE_KEYS},
                    item_id=command.item_id, region_spec=command.region_spec, hardware_revision=command.hardware_revision,
                    reserved=0, **values))
        elif command.event == "address_confirmation":
            if command.confirmed is None or not command.selection_ref:
                raise ServiceError("address_customer_source_required", 422)
            source = visible_quote(conn, self.store, conv, command.selection_ref)
            latest = conn.execute(sa.select(sa.func.max(messages.c.seq)).where(messages.c.conversation_id == conv["id"],
                messages.c.sender == "customer", messages.c.seq <= conv["visible_message_seq"], *scope_where(messages, conv))).scalar_one()
            if source["seq"] != latest:
                raise ServiceError("address_source_superseded", 422)
            address = {"customer_id": state["source_customer_id"], "confirmed": command.confirmed,
                "version": command.business_version, "market": order["source_snapshot"]["market"],
                "source_message_id": source["source_message_id"], "source_kind": "customer_statement",
                "evidence_ref": command.receipt_ref}
            state["address_confirmations"] = {**state.get("address_confirmations", {}), line["external_id"]: address}
            count = conn.execute(sa.select(sa.func.count()).select_from(b.branch_order_lines).where(
                *scope_where(b.branch_order_lines, conv))).scalar_one()
            if count == 1:
                state["address_confirmation"] = address
        elif command.event == "service_note":
            state["service_notes"] = [*state.get("service_notes", []), {"order_line_id": line["external_id"],
                "reason": command.reason, "evidence_ref": command.receipt_ref, "source_kind": "scenario_console_manual"}]
        else:
            from globalmail_agent.application.branch_fulfillment import correct_fulfillment
            correct_fulfillment(conn, conv, branch, line, command)
