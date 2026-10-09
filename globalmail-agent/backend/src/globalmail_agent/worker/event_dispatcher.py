"""Dispatch committed facts under the same conversation lock; no polling model loop."""
from globalmail_agent.application.business_events import publish_operation_event


def dispatch_locked(conn, conversation, operation, event, source_event_id):
    return publish_operation_event(conn, conversation, operation, event, source_event_id)
