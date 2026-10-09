"""Changing a plan requires resolving the original compensating request first."""
import sqlalchemy as sa
from globalmail_agent.adapters.business_schema import operations
from globalmail_agent.application.business_read_model import scope_where
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.domain.operations import COMPENSATING


def check_plan_change(conn, conv, line_id, action, exclude=None):
    rows = conn.execute(sa.select(operations).where(*scope_where(operations, conv),
        operations.c.order_line_id == line_id, operations.c.kind.in_(COMPENSATING),
        operations.c.kind != action, operations.c.confirmed_not_executed.is_(False),
        operations.c.status.in_(["accepted", "waiting_condition", "awaiting_execution", "processing", "failed", "unknown"]))) .mappings()
    if action == "return" and any(r["external_id"] != exclude for r in rows):
        raise ServiceError("original_plan_requires_cancellation_or_reconciliation", 422)
