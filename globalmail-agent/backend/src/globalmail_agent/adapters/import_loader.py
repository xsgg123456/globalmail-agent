import hashlib
import json
from globalmail_agent.domain.conversation import ImportCase
from globalmail_agent.application.conversation_lock import ServiceError


def payload_hash(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                    ensure_ascii=False, default=str).encode()).hexdigest()


def validate_case(case: ImportCase):
    ids = [m.source_message_id for m in case.messages]
    if len(ids) != len(set(ids)):
        raise ServiceError("duplicate_source_message", 422)
    if case.messages[0].sender != "customer":
        raise ServiceError("missing_starting_customer_message", 422)
    if any(a.sent_at > b.sent_at for a, b in zip(case.messages, case.messages[1:])):
        raise ServiceError("messages_out_of_order", 422)
    if case.expected_version != 0:
        raise ServiceError("initial_version_required", 422)
    return case
