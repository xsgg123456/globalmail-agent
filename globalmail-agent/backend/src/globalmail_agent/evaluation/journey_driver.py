"""External controller delivers only the current fact after real service gates."""
import json
from dataclasses import asdict, dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Protocol

from globalmail_agent.domain.orders import timestamp
from globalmail_agent.evaluation.journey_gates import evaluate_gate, has_forbidden
from globalmail_agent.evaluation.reporting import save_json, scenario_report, step_key, step_record


@dataclass(frozen=True)
class CommitResult:
    committed: bool
    evidence_refs: tuple[str, ...] = ()
    resources: dict = field(default_factory=dict)
    run_ids: tuple[str, ...] = ()
    reason: str | None = None


class DriverCallbacks(Protocol):
    def create(self, scenario_id, initial, command_id) -> CommitResult: ...
    def observe(self, scenario_id, resources) -> dict: ...
    def apply(self, delivery, resources, command_id, authorization) -> CommitResult: ...
    def verify_gate(self, name, event, observation, resources): ...


def valid_receipt(receipt):
    return (isinstance(receipt, CommitResult) and receipt.committed is True
            and isinstance(receipt.evidence_refs, (list, tuple)) and bool(receipt.evidence_refs)
            and all(isinstance(ref, str) and ref for ref in receipt.evidence_refs)
            and isinstance(receipt.resources, dict)
            and all(isinstance(k, str) and isinstance(v, str) and v for k, v in receipt.resources.items())
            and isinstance(receipt.run_ids, (list, tuple))
            and all(isinstance(identifier, str) and identifier for identifier in receipt.run_ids))


def load_controller(root, scenarios, *, journeys=True):
    """Constant path: no evaluation/reference file can be opened by this loader."""
    relative = "scenarios/journeys/controller-events.jsonl" if journeys else "scenarios/controller-events.jsonl"
    raw = (Path(root) / relative).read_bytes()
    rows = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
    grouped, seen = {sid: [] for sid in scenarios}, {}
    for row in rows:
        if has_forbidden(row) or row.get("agent_can_create") is not False:
            raise ValueError("controller_visibility_invalid")
        if row["scenario_id"] not in scenarios:
            raise ValueError("controller_scenario_unknown")
        if type(row["sequence"]) is not int or row["sequence"] < 1:
            raise ValueError("controller_sequence_invalid")
        timestamp(row["not_before"])
        identifier = row["event_id"]
        if identifier in seen:
            original = {k: v for k, v in row.items() if k != "replay_same_event"}
            if original != seen[identifier]:
                raise ValueError("controller_duplicate_conflict")
            if row.get("replay_same_event") is not True:
                continue
            row["controller_step_id"] = identifier + ":replay"
            if any(step_key(e) == row["controller_step_id"] for e in grouped[row["scenario_id"]]):
                continue
            grouped[row["scenario_id"]].append(row)
            continue
        if row.get("replay_same_event"):
            raise ValueError("controller_replay_original_missing")
        seen[identifier] = row
        grouped[row["scenario_id"]].append(row)
    for events in grouped.values():
        events.sort(key=lambda row: row["sequence"])
        if [row["sequence"] for row in events if not row.get("replay_same_event")] != list(range(1, len({r['sequence'] for r in events}) + 1)):
            raise ValueError("controller_sequence_gap_or_duplicate")
        positions = {e["event_id"]: e["sequence"] for e in events}
        for event in events:
            dependency = event.get("requires_event_id")
            if dependency is not None and positions.get(dependency, len(events) + 1) >= event["sequence"]:
                raise ValueError("controller_dependency_invalid")
    return grouped, sha256(raw).hexdigest()


class JourneyDriver:
    def __init__(self, scenario, events, controller_hash, callbacks, *, state_path=None):
        self.scenario, self.events, self.callbacks = scenario, events, callbacks
        self.path = Path(state_path) if state_path else None
        self.state = {"scenario_id": scenario["scenario_id"], "controller_hash": controller_hash,
                      "scope": {"branch_id": scenario["branch_id"],
                                "customer_id": scenario["access_scope"]["customer_id"]},
                      "position": 0, "committed": {}, "resources": {}, "reports": {}}
        if self.path and self.path.exists():
            stored = json.loads(self.path.read_text(encoding="utf-8"))
            if any(stored.get(k) != self.state[k] for k in ("scenario_id", "controller_hash", "scope")):
                raise ValueError("controller_cursor_source_mismatch")
            position = stored.get("position")
            if type(position) is not int or not 0 <= position <= len(events):
                raise ValueError("controller_cursor_invalid")
            expected = {e["event_id"] for e in events[:position]}
            if set(stored.get("committed", {})) - {"initial_message"} != expected:
                raise ValueError("controller_cursor_commit_mismatch")
            self.state = stored

    def _save(self):
        if self.path:
            save_json(self.path, self.state)

    def _command_id(self, event_id):
        return "controller:" + self.scenario["branch_id"] + ":" + event_id

    def start(self):
        if "initial_message" in self.state["committed"]:
            return self.report()
        # Initial messages/facts came from FixturePackage's allowlist, not raw inputs.
        if has_forbidden(self.scenario):
            raise ValueError("initial_visibility_invalid")
        try:
            receipt = self.callbacks.create(self.scenario["scenario_id"], self.scenario,
                                            self._command_id("initial_message"))
        except Exception as exc:
            self.state["initial"] = {"status": "failed", "reason": "service_error:" + type(exc).__name__}
            self._save()
            return self.report()
        valid = valid_receipt(receipt)
        if valid and receipt.resources.get("conversation_id"):
            result = asdict(receipt)
            self.state["committed"]["initial_message"] = result
            self.state["resources"].update(receipt.resources)
            self.state["initial"] = {"status": "in_progress", **result}
        else:
            self.state["initial"] = {"status": "blocked", "reason": "initial_commit_evidence_missing"}
        self._save()
        return self.report()

    def advance(self, now, *, checkpoint=None, staff_id=None, resolution_reason=None):
        if "initial_message" not in self.state["committed"]:
            return self.report()
        try:
            observation = self.callbacks.observe(self.scenario["scenario_id"], dict(self.state["resources"]))
        except Exception as exc:
            self.state["initial"] = {**self.state["initial"], "status": "failed",
                                     "reason": "observation_error:" + type(exc).__name__}
            self._save()
            return self.report()
        if self.state["position"] == len(self.events):
            self._finish(observation)
            return self.report()
        event = self.events[self.state["position"]]
        authorization = {"staff_id": staff_id or "", "resolution_reason": resolution_reason or ""}
        names = ["event_dependencies", "not_before", *event.get("gate", {}).get("required_business_checks", [])]
        names = list(dict.fromkeys(["previous_step_committed", "event_not_already_applied",
                                    "record_scope_matches_branch", "no_reference_reply_injection", *names]))
        mandatory = {"checkpoint": ["actual_agent_run_completed", "checkpoint_conditions_verified_by_controller"],
                     "human_close": ["staff_identity_required", "resolution_reason_recorded"]}
        names.extend(name for name in mandatory.get(event["kind"], ()) if name not in names)
        # Legacy trigger conditions are checked individually and cannot be dropped.
        names.extend(name for name in event.get("trigger_condition", {}) if name not in names)
        gates = []
        for name in names:
            try:
                gates.append(evaluate_gate(name, event, self.state, observation, now, authorization,
                                           checkpoint, self.callbacks.verify_gate))
            except Exception as exc:
                from globalmail_agent.evaluation.journey_gates import GateResult
                gates.append(GateResult(name, reason="gate_error:" + type(exc).__name__))
        unmet = [gate for gate in gates if gate.status != "passed"]
        if unmet:
            status = "failed" if any(g.status == "failed" for g in unmet) else "blocked"
            if all(g.status == "awaiting_checkpoint" for g in unmet):
                status = "awaiting_checkpoint"
            return self._record(event, status, gates, observation, reason=";".join(g.name + ":" + g.reason for g in unmet))
        if event.get("replay_same_event") is True:
            self.state["position"] += 1
            receipt = CommitResult(**self.state["committed"][event["event_id"]])
            return self._record(event, "duplicate_suppressed", gates, observation, receipt,
                                reason="original_committed_event_not_redelivered")
        if event["kind"] == "checkpoint":
            receipt = CommitResult(True, checkpoint.evidence_refs, run_ids=(checkpoint.run_id,))
        else:
            delivery = {k: event[k] for k in ("event_id", "scenario_id", "kind", "actor", "not_before", "source_kind", "payload")}
            current_resources = dict(self.state["resources"])
            for gate in gates:
                if gate.resource_ids.get("operation_id"):
                    current_resources["operation_id"] = gate.resource_ids["operation_id"]
            try:
                receipt = self.callbacks.apply(delivery, current_resources,
                                               self._command_id(event["event_id"]), authorization)
            except Exception as exc:
                return self._record(event, "failed", gates, observation, reason="service_error:" + type(exc).__name__)
        if not valid_receipt(receipt):
            reason = receipt.reason if isinstance(receipt, CommitResult) else "invalid_service_receipt"
            return self._record(event, "blocked", gates, observation, reason=reason or "commit_evidence_missing")
        self.state["committed"][event["event_id"]] = asdict(receipt)
        self.state["resources"].update(receipt.resources)
        self.state["position"] += 1
        return self._record(event, "applied", gates, observation, receipt)

    def _finish(self, observation):
        from globalmail_agent.evaluation.journey_gates import run_completed
        # Eventless scenarios also need an actual run/outcome, not just input creation.
        completed = run_completed(observation, "initial_message") if not self.events else True
        self.state["initial"].update(status="completed" if completed else "in_progress", run=observation.get("run"))
        self._save()

    def _record(self, event, status, gates, observation, receipt=None, reason=None):
        self.state["reports"][step_key(event)] = step_record(event, status, gates, observation,
                                                             asdict(receipt) if receipt else None, reason)
        self._save()
        return self.report()

    def report(self):
        return scenario_report(self.scenario["scenario_id"], self.state, self.events)
