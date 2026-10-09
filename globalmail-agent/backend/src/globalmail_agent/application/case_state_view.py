"""Read actual scoped issue/wait/event state without exposing object storage paths."""
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import case_issues, domain_events
from globalmail_agent.application.business_read_model import scope_where


def case_state(conn, conv):
    fields = {"issues": (case_issues, ("id", "issue_key", "order_line_id", "order_number", "business_type", "status",
            "plan_status", "current_operation_id", "source_message_id", "version")),
        "waits": (a.wait_conditions, ("id", "issue_id", "operation_id", "condition_type", "condition_key",
            "last_seen_business_version", "owner", "status", "run_id")),
        "wakes": (a.wake_pending, ("id", "issue_id", "operation_id", "condition_key", "business_version", "status", "observed_run_id")),
        "business_events": (domain_events, ("id", "source", "source_event_id", "issue_id", "operation_id",
            "condition_type", "business_version", "status", "observed_run_id"))}
    result = {}
    for key, (table, names) in fields.items():
        rows = conn.execute(sa.select(*[table.c[n] for n in names]).where(
            table.c.conversation_id == conv["id"], *scope_where(table, conv)).order_by(table.c.created_at)).mappings()
        result[key] = [{n: str(v) if n.endswith("_id") or n == "id" else v for n, v in r.items()}
            for r in rows]
        for row in result[key]:
            for name in names:
                if row[name] == "None":
                    row[name] = None
    return result
