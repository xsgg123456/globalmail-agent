"""ERP stock is locked and reserved only when a simulated execution is created."""
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters import business_schema as b, after_sales_schema as a
from globalmail_agent.application.business_read_model import scope_where
from globalmail_agent.application.conversation_lock import ServiceError


def reserve(conn, conv, operation, execution):
    proposal = operation["source_snapshot"]["plan"]
    line = conn.execute(sa.select(b.branch_order_lines).where(b.branch_order_lines.c.id == operation["order_line_id"],
        *scope_where(b.branch_order_lines, conv))).mappings().one()
    order = conn.execute(sa.select(b.branch_orders).where(b.branch_orders.c.id == operation["order_id"],
        *scope_where(b.branch_orders, conv))).mappings().one()
    item = proposal["item_id"]
    stock = conn.execute(sa.select(b.inventory).where(*scope_where(b.inventory, conv), b.inventory.c.item_id == item,
        b.inventory.c.region_spec == order["source_snapshot"]["market"],
        b.inventory.c.hardware_revision == line["hardware_revision"]).with_for_update()).mappings().one_or_none()
    if not stock or stock["on_hand"] - stock["reserved"] < operation["quantity"]:
        raise ServiceError("execution_stock_unavailable")
    conn.execute(b.inventory.update().where(b.inventory.c.id == stock["id"])
        .values(reserved=stock["reserved"] + operation["quantity"]))
    conn.execute(sa.insert(a.inventory_reservations).values(id=uuid4(), **{k: conv[k] for k in a.SCOPE_KEYS},
        operation_id=operation["id"], execution_id=execution["id"], inventory_id=stock["id"],
        quantity=operation["quantity"], state="reserved"))


def settle(conn, conv, execution, *, consume):
    hold = conn.execute(sa.select(a.inventory_reservations).where(a.inventory_reservations.c.execution_id == execution["id"],
        *scope_where(a.inventory_reservations, conv)).with_for_update()).mappings().first()
    if not hold or hold["state"] != "reserved":
        return
    stock = conn.execute(sa.select(b.inventory).where(b.inventory.c.id == hold["inventory_id"],
        *scope_where(b.inventory, conv)).with_for_update()).mappings().one()
    quantity = hold["quantity"]
    if stock["reserved"] < quantity or stock["on_hand"] < quantity:
        raise ServiceError("inventory_reconciliation_required")
    conn.execute(b.inventory.update().where(b.inventory.c.id == stock["id"]).values(
        reserved=stock["reserved"] - quantity, on_hand=stock["on_hand"] - quantity if consume else stock["on_hand"]))
    conn.execute(a.inventory_reservations.update().where(a.inventory_reservations.c.id == hold["id"])
        .values(state="consumed" if consume else "released"))


def change(conn, conv, operation, on_hand, clock):
    if on_hand is None:
        raise ServiceError("inventory_quantity_required", 422)
    proposal = operation["source_snapshot"]["plan"]
    line = conn.execute(sa.select(b.branch_order_lines).where(b.branch_order_lines.c.id == operation["order_line_id"])).mappings().one()
    order = conn.execute(sa.select(b.branch_orders).where(b.branch_orders.c.id == operation["order_id"])).mappings().one()
    row = conn.execute(sa.select(b.inventory).where(*scope_where(b.inventory, conv),
        b.inventory.c.item_id == proposal["item_id"], b.inventory.c.region_spec == order["source_snapshot"]["market"],
        b.inventory.c.hardware_revision == line["hardware_revision"]).with_for_update()).mappings().one_or_none()
    if not row or on_hand < row["reserved"]:
        raise ServiceError("inventory_change_conflict")
    conn.execute(b.inventory.update().where(b.inventory.c.id == row["id"]).values(on_hand=on_hand, snapshot_at=clock))
