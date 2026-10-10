"""Fail closed before the SDK's media traversal; no arbitrary strings or bytes."""
import re

IDS = {"run_id", "conversation_id", "workspace_id", "branch_id", "customer_id", "cycle_id",
    "parent_run_id", "attachment_id", "release_id", "profile_id", "usage_id", "context_object_id",
    "observation_id", "parent_observation_id"}
COUNTS = {"attempt_no", "generation", "input_revision", "authority_epoch", "release_epoch",
    "case_revision", "position", "image_count", "view_count", "input_tokens", "output_tokens",
    "started_ns", "ended_ns", "duration_ms", "pending_count"}
HASHES = {"prompt_hash", "graph_hash", "policy_hash", "tool_hash", "model_hash", "request_hash"}
ENUMS = {
    "node": {"run", "context", "attachment_prepare", "understanding", "model", "retrieval",
        "tool", "policy", "response", "commit", "outcome"},
    "status": {"completed", "failed", "unknown", "known", "ok", "empty", "needs_input", "denied",
        "pending", "reserved", "unavailable", "error", "revoked", "interrupted", "stopped",
        "budget_exhausted", "running", "queued", "handoff", "handed_off", "cancelled", "superseded"},
    "stage": {"understanding", "decision", "validation"},
    "mode": {"simulation", "historical_replay"},
    "execution_mode": {"autonomous", "human_assist"},
    "outcome": {"reply_and_wait", "historical_comparison", "handoff", "human_advice",
        "wait_business", "no_material_update"},
    "reason_code": {"business_failure", "dependency_error", "model_timeout", "model_rate_limited",
        "model_unavailable", "model_not_configured", "budget_exhausted", "input_budget_exceeded",
        "provider_usage_exceeded", "image_view_budget_exceeded", "run_superseded", "lease_expired",
        "worker_interrupted", "image_content_revoked", "stale_release", "sanitization_failed"},
    "tool_name": {"get_case_context", "get_order_snapshot", "get_shipment_status", "get_after_sales_context",
        "get_operation_status", "get_item_availability", "search_reference", "update_case_state",
        "revise_understanding", "create_reply_draft", "request_human_review"},
    "model": {"qwen3.7-plus"},
    "usage_status": {"reserved", "known", "unknown"},
}


def safe_fields(values):
    if not isinstance(values, dict):
        raise ValueError("sanitization_failed")
    result = {}
    for key, value in values.items():
        if value is None:
            continue
        if key in IDS and isinstance(value, str) and re.fullmatch(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", value):
            result[key] = value
        elif key in COUNTS and type(value) is int and 0 <= value <= 2 ** 63 - 1:
            result[key] = value
        elif key in HASHES and isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value):
            result[key] = value
        elif key in ENUMS and isinstance(value, str) and value in ENUMS[key]:
            result[key] = value
        elif key == "attachment_ids" and isinstance(value, list) and len(value) <= 6 and all(
                isinstance(item, str) and re.fullmatch(
                    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", item) for item in value):
            result[key] = list(value)
        else:
            raise ValueError("sanitization_failed")
    return result


def safe_payload(value):
    if not isinstance(value, dict) or set(value) != {"metadata", "observations"}:
        raise ValueError("sanitization_failed")
    rows = value["observations"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 128:
        raise ValueError("sanitization_failed")
    return {"metadata": safe_fields(value["metadata"]), "observations": [safe_fields(r) for r in rows]}
