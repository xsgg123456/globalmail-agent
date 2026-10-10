"""Safe log metadata. Never copy provider exceptions, model reasoning or raw bodies."""
from globalmail_agent.observability.media_filter import safe_fields


def safe_summary(values):
    try:
        return safe_fields(values)
    except Exception:
        return {}  # Logging must also fail closed; export records separately mark degraded.
