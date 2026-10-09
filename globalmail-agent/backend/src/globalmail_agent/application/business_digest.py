"""A scoped snapshot receipt is compared again under the final branch/conversation locks."""
import sqlalchemy as sa
import json
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.knowledge.base import sha


TABLES = (b.simulation_branches, b.branch_orders, b.branch_order_lines, b.operations, b.executions,
    b.shipments, b.return_receipts, b.inventory)


def business_digest(conn, conv, *, lock=False):
    snapshot = {}
    for table in TABLES:
        query = sa.select(table).where(*[table.c[k] == conv[k] for k in SCOPE_KEYS]).order_by(table.c.id)
        if lock:
            query = query.with_for_update()
        snapshot[table.name] = [dict(row) for row in conn.execute(query).mappings()]
    return sha(json.dumps(snapshot, default=str, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode())
