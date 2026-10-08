"""Exact identity, integer money and explicit result semantics."""
from datetime import datetime, timezone

MOCK_SOURCES = {"synthetic", "synthetic_scenario", "authored_business_journey",
                "synthetic_replay_test_not_real_history", "synthetic_project_policy",
                "synthetic_project_compatibility", "synthetic_project_part"}


def operation_status(value):
    return {"requested": "accepted", "completed": "succeeded", "fulfilled": "succeeded"}.get(value, value)


def timestamp(value):
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(parsed, datetime) or parsed.tzinfo is None:
        raise ValueError("timezone_required")
    return parsed


def integer(value, *, minimum=0, optional=False):
    if value is None and optional:
        return None
    if type(value) is not int or value < minimum:
        raise ValueError("invalid_integer")
    return value


def result(status="ok", reason_code="business_snapshot", data=None, *, simulation=False,
           source_kind="unknown", observed_at=None, resource_versions=None, evidence_refs=None,
           retryable=False):
    return {"status": status, "reason_code": reason_code, "data": data,
            "evidence_refs": evidence_refs or [],
            "observed_at": observed_at or datetime.now(timezone.utc).isoformat(),
            "resource_versions": resource_versions or {}, "source_kind": source_kind,
            "simulation": simulation, "retryable": retryable}


def unknown_fields(record, names):
    return [name for name in names if record.get(name) is None]


def verified(record, evidence_ref):
    original_kind = record.get("source_kind", "synthetic")
    return {**record, "original_source_kind": original_kind,
            "source_kind": "verified_fixture" if original_kind in MOCK_SOURCES else original_kind,
            "evidence_ref": evidence_ref}
