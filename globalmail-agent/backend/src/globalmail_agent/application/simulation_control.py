"""Independent console writes ordered events under the same conversation and business locks."""
from uuid import uuid4
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert as pg_insert
from globalmail_agent.adapters import business_schema as b, after_sales_schema as a
from globalmail_agent.adapters.knowledge_index_schema import knowledge_release_heads
from globalmail_agent.knowledge.base import scope
from globalmail_agent.knowledge.release_queries import head
from globalmail_agent.application.after_sales import AfterSalesService
from globalmail_agent.application.after_sales_ledger import operation_row, operations_view, refresh_balances
from globalmail_agent.application.business_read_model import read_model, scope_where
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError, lock_conversation
from globalmail_agent.application.idempotency import prior, remember
from globalmail_agent.application.event_store import append_ui_event
from globalmail_agent.application.simulation_execution import create_execution, execution_event, recheck
from globalmail_agent.application.simulation_fulfillment import create_label, return_event, shipment_event
from globalmail_agent.application.simulation_inventory import change
from globalmail_agent.application.reconciliation import link_existing
from globalmail_agent.application.waits import _record_wake_locked
from globalmail_agent.domain.executions import SimulationEvent, ExecutionLink, allowed_events


class SimulationControlService:
    def __init__(self, engine, store, workspace_id=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.workspace_id = engine, store, workspace_id

    def _available(self):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)

    def _locked(self, conn, branch_id, command):
        conv = lock_conversation(conn, command.conversation_id, self.workspace_id, command.expected_version)
        if conv["mode"] != "simulation" or conv["branch_id"] != branch_id:
            raise ServiceError("simulation_branch_out_of_scope", 422)
        branch = conn.execute(sa.select(b.simulation_branches).where(b.simulation_branches.c.id == branch_id,
            b.simulation_branches.c.conversation_id == conv["id"], *scope_where(b.simulation_branches, conv))).mappings().one_or_none()
        if not branch:
            raise ServiceError("simulation_branch_out_of_scope", 422)
        conn.execute(pg_insert(knowledge_release_heads).values(id=uuid4(), **scope(self.workspace_id)).on_conflict_do_nothing())
        head(conn, self.workspace_id, True)
        conn.execute(sa.select(b.branch_order_lines.c.id).where(*scope_where(b.branch_order_lines, conv))
            .order_by(b.branch_order_lines.c.id).with_for_update()).all()
        operation = operation_row(conn, conv, command.operation_id, lock=True)
        if not operation or not operation["decision_id"]:
            raise ServiceError("managed_operation_required", 422)
        if operation["version"] != command.expected_operation_version:
            raise ServiceError("stale_operation_version")
        return conv, branch, operation

    def _execution(self, conn, conv, operation, external_id):
        rows = conn.execute(sa.select(b.executions).where(b.executions.c.operation_id == operation["id"],
            *scope_where(b.executions, conv)).order_by(b.executions.c.attempt_no).with_for_update()).mappings().all()
        if external_id:
            row = next((e for e in rows if e["external_id"] == external_id), None)
            if not row:
                raise ServiceError("execution_out_of_scope", 422)
            return row
        active = [e for e in rows if not e["confirmed_not_executed"]]
        return active[-1] if active else None

    def event(self, branch_id, command, key):
        self._available()
        if not isinstance(command, SimulationEvent):
            command = SimulationEvent.model_validate(command)
        operation_key = "simulation-event:" + str(branch_id)
        payload = command.model_dump(mode="json")
        with self.engine.begin() as conn:
            old, digest = prior(conn, self.workspace_id, key, operation_key, payload)
            if old is not None:
                return old
            conv, branch, operation = self._locked(conn, branch_id, command)
            model = read_model(conn, conv["id"], self.workspace_id)
            view = operations_view(model, operation["external_id"])["data"]
            permitted = view["operations"][0]["allowed_events"]
            if command.event not in permitted:
                raise ServiceError("simulation_event_not_allowed")
            if command.quantity is not None and command.quantity != operation["quantity"]:
                raise ServiceError("execution_quantity_mismatch", 422)
            execution = self._execution(conn, conv, operation, command.execution_id)
            status, confirmed = operation["status"], operation["confirmed_not_executed"]
            if command.event == "create_execution":
                execution, status = create_execution(conn, self.store, conv, branch, operation)
                conn.execute(a.compensation_reservations.update().where(a.compensation_reservations.c.operation_id == operation["id"],
                    *scope_where(a.compensation_reservations, conv)).values(active=True))
                confirmed = False
            elif command.event in {"processing", "succeeded", "failed", "unknown", "reconciled_not_executed"}:
                status, confirmed = execution_event(conn, self.store, conv, branch, operation, execution, command)
            elif command.event == "inventory_changed":
                change(conn, conv, operation, command.on_hand, branch["clock"])
            elif command.event == "label_created":
                decision = conn.execute(sa.select(b.policy_decisions.c.decision_data).where(b.policy_decisions.c.id == operation["decision_id"])).scalar_one()
                from types import SimpleNamespace
                from globalmail_agent.application.after_sales_policy import published_policy
                selected = next(l for l in model["lines"] if l[0]["id"] == operation["order_line_id"])
                context = SimpleNamespace(release_id=operation["policy_release_id"], release_epoch=decision["release_epoch"],
                    mode=conv["mode"], as_of=branch["clock"])
                policy = published_policy(conn, self.store, self.workspace_id, context, model, selected)["rules"]
                if execution and operation["kind"] in {"replacement", "spare_part"}:
                    self._dispatch_recheck(conn, conv, branch, operation, execution)
                create_label(conn, conv, branch, operation, execution, command, policy)
            elif command.event in {"shipped", "delivered"}:
                if command.event == "shipped":
                    self._dispatch_recheck(conn, conv, branch, operation, execution)
                shipment_event(conn, conv, branch, operation, execution, command)
            else:
                return_event(conn, conv, branch, operation, command)
            version = operation["version"] + 1
            snapshot = {**operation["source_snapshot"], "status": status, "version": version,
                "confirmed_not_executed": confirmed, "updated_at": branch["clock"].isoformat()}
            conn.execute(b.operations.update().where(b.operations.c.id == operation["id"])
                .values(status=status, version=version, confirmed_not_executed=confirmed, details=snapshot))
            refresh_balances(conn, conv)
            sequence = conn.execute(sa.select(sa.func.max(a.simulation_events.c.sequence)).where(
                a.simulation_events.c.operation_id == operation["id"])).scalar_one() or 0
            event_id = uuid4()
            conn.execute(sa.insert(a.simulation_events).values(id=event_id, **{k: conv[k] for k in a.SCOPE_KEYS},
                conversation_id=conv["id"], operation_id=operation["id"], execution_id=execution["id"] if execution else None,
                event=command.event, sequence=sequence + 1, payload=payload))
            condition = "inventory" if command.event == "inventory_changed" else "warehouse_receipt" if command.event in {
                "received", "inspected", "return_in_transit"} else "shipment_changed" if command.event in {
                "label_created", "shipped", "delivered"} else "refund_receipt" if operation["kind"] == "refund" else "manual_execution"
            wake = _record_wake_locked(conn, conv, condition + ":" + operation["external_id"], version)
            append_ui_event(conn, conv["id"], "simulation.event", {"event_id": str(event_id),
                "operation_id": operation["external_id"], "event": command.event, "operation_version": version})
            data = operations_view(read_model(conn, conv["id"], self.workspace_id), operation["external_id"])["data"]
            response = {"conversation_id": str(conv["id"]), "operation_id": operation["external_id"],
                "operation_version": version, "event_id": str(event_id), "event": command.event,
                "wake_status": wake["status"], **data}
            remember(conn, self.workspace_id, key, operation_key, digest, response)
            return response

    def _dispatch_recheck(self, conn, conv, branch, operation, execution):
        if not execution or execution["status"] not in {"accepted", "processing", "unknown"}:
            raise ServiceError("dispatch_execution_invalid")
        # Own reserved stock remains available to this exact execution only.
        hold = conn.execute(sa.select(a.inventory_reservations).where(a.inventory_reservations.c.execution_id == execution["id"],
            *scope_where(a.inventory_reservations, conv))).mappings().first()
        if not hold or hold["state"] != "reserved":
            raise ServiceError("dispatch_stock_reservation_required")
        stock = conn.execute(sa.select(b.inventory).where(b.inventory.c.id == hold["inventory_id"]).with_for_update()).mappings().one()
        conn.execute(b.inventory.update().where(b.inventory.c.id == stock["id"]).values(reserved=stock["reserved"] - hold["quantity"]))
        recheck(conn, self.store, conv, branch, operation)
        conn.execute(b.inventory.update().where(b.inventory.c.id == stock["id"]).values(reserved=stock["reserved"]))

    def link(self, branch_id, command, key):
        self._available()
        if not isinstance(command, ExecutionLink):
            command = ExecutionLink.model_validate(command)
        operation_key = "execution-link:" + str(branch_id)
        with self.engine.begin() as conn:
            old, digest = prior(conn, self.workspace_id, key, operation_key, command.model_dump(mode="json"))
            if old is not None:
                return old
            conv, branch, operation = self._locked(conn, branch_id, command)
            execution = link_existing(conn, conv, operation, command.execution_id)
            response = {"conversation_id": str(conv["id"]), "operation_id": operation["external_id"],
                "execution_id": execution["external_id"], "linked": True, "status": execution["status"],
                "operation_version": operation["version"], "conversation_version": conv["row_version"]}
            append_ui_event(conn, conv["id"], "simulation.execution_linked", {
                "conversation_id": str(conv["id"]), "operation_id": operation["external_id"],
                "execution_id": execution["external_id"], "operation_version": operation["version"], "status": execution["status"]})
            remember(conn, self.workspace_id, key, operation_key, digest, response)
            return response
