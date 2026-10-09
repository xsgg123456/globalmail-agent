"""Usage is provider-reported and deduplicated; unknown cost stays unknown."""
import sqlalchemy as sa
from globalmail_agent.adapters.agent_schema import cycle_budgets
from globalmail_agent.agent.budget import LIMITS


def usage_view(conn, cycle_id):
    row = conn.execute(sa.select(cycle_budgets).where(cycle_budgets.c.cycle_id == cycle_id)).mappings().first()
    keys = ("model_requests", "tool_calls", "input_tokens", "output_tokens", "unknown_requests", "reserved_tokens", "active_ms")
    return {**{key: row[key] if row else 0 for key in keys}, "limits": LIMITS, "cost": None}
