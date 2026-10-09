"""Complete per-step engineering evidence; unexecuted samples stay unexecuted."""
import json
from pathlib import Path
from datetime import date, datetime
from uuid import UUID


def step_key(event):
    return event.get("controller_step_id", event["event_id"])


def step_record(event, status="not_run", gates=(), observation=None, receipt=None, reason=None):
    observation, receipt = observation or {}, receipt or {}
    return {"event_id": event["event_id"], "controller_step_id": step_key(event),
            "sequence": event["sequence"], "kind": event["kind"],
            "status": status, "gates": [g.record() for g in gates],
            "run": observation.get("run"), "run_ids": receipt.get("run_ids", []),
            "ledger_resource_ids": observation.get("ledger_resource_ids", {}),
            "commit_evidence_refs": receipt.get("evidence_refs", []), "reason": reason}


def scenario_report(scenario_id, state, events):
    steps = [state["reports"].get(step_key(e), step_record(e)) for e in events]
    initial = state.get("initial", {"status": "not_run", "reason": "service_not_called"})
    blocked = next((s for s in steps if s["status"] in {"blocked", "awaiting_checkpoint", "failed"}), None)
    status = blocked["status"] if blocked else "not_run" if initial["status"] == "not_run" else "in_progress"
    if initial["status"] in {"blocked", "failed"}:
        status = initial["status"]
    elif initial["status"] == "completed" and all(s["status"] in {"applied", "duplicate_suppressed"} for s in steps):
        status = "completed"
    return {"scenario_id": scenario_id, "status": status, "initial": initial,
            "controller_hash": state["controller_hash"], "cursor": state["position"],
            "resources": state["resources"], "steps": steps,
            "quality_status": "not_evaluated", "model_semantics": "deferred_to_phase13"}


def suite_report(reports):
    counts = {}
    for report in reports:
        counts[report["status"]] = counts.get(report["status"], 0) + 1
    return {"scenario_count": len(reports), "statuses": counts, "scenarios": reports,
            "quality_status": "not_evaluated", "production_accuracy": None}


def save_json(path, value):
    """Atomic local controller cursor/report persistence, not a business ledger."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=json_value), encoding="utf-8")
    temporary.replace(path)


def json_value(value):
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    raise TypeError("unsupported_controller_report_value:" + type(value).__name__)
