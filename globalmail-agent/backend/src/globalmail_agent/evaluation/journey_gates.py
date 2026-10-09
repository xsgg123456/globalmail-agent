"""Fail-closed gates over committed service observations, never authored answers."""
from dataclasses import asdict, dataclass, field

from globalmail_agent.domain.orders import timestamp


BUSINESS_GATES = {
    "actual_internal_request_exists", "result_matches_original_request",
    "legal_execution_status_transition", "exact_item_compatible",
    "authorized_refund_amount_and_currency_match", "no_duplicate_refund_result",
    "customer_choice_valid", "confirmed_current_address_version",
    "stock_available_before_dispatch", "refund_balance_available",
    "return_inspection_or_recorded_exception_for_full_refund",
    "explicit_amount_acceptance_for_partial_refund",
    "return_inspection_or_recorded_exception_before_dispatch",
    "cancellation_requested", "no_dispatch_confirmed", "release_original_reservations",
    "after_matching_internal_request", "after_internal_return_request",
}
STRUCTURAL_GATES = {
    "previous_step_committed", "event_not_already_applied", "record_scope_matches_branch",
    "actual_agent_run_completed", "checkpoint_conditions_verified_by_controller",
    "no_reference_reply_injection", "staff_identity_required", "resolution_reason_recorded",
    "after_initial_agent_turn", "event_dependencies", "not_before",
}
KNOWN_GATES = BUSINESS_GATES | STRUCTURAL_GATES
FORBIDDEN_FIELDS = {"reference_reply", "reference_replies", "expected_reply", "evaluation",
                    "future_events", "controller_events", "controller_events_ref"}


@dataclass(frozen=True)
class GateResult:
    name: str
    status: str = "blocked"
    reason: str = "evidence_missing"
    evidence_refs: tuple[str, ...] = ()
    resource_ids: dict = field(default_factory=dict)
    run_id: str | None = None

    def record(self):
        return asdict(self)


@dataclass(frozen=True)
class CheckpointVerification:
    event_id: str
    staff_id: str
    run_id: str
    revision: str | int
    evidence_refs: tuple[str, ...]
    passed: bool
    reason: str


def has_forbidden(value):
    if isinstance(value, dict):
        return bool(FORBIDDEN_FIELDS.intersection(value)) or any(has_forbidden(v) for v in value.values())
    return isinstance(value, (list, tuple)) and any(has_forbidden(v) for v in value)


def run_completed(observation, step, *, history=False):
    runs = [observation.get("run") or {}, *(observation.get("runs", ()) if history else ())]
    return any(run.get("id") and run.get("status") in {"completed", "handed_off"}
               and run.get("outcome") and step in run.get("observed_steps", ()) for run in runs)


def evaluate_gate(name, event, state, observation, now, authorization, checkpoint, verify):
    """Business checks are mandatory adapter calls to the existing service/ledger."""
    if name not in KNOWN_GATES:
        return GateResult(name, reason="unknown_gate")
    trigger = event.get("trigger_condition", {})
    if name in trigger and ((name == "after_matching_internal_request" and not isinstance(trigger[name], dict))
                           or (name != "after_matching_internal_request" and trigger[name] is not True)):
        return GateResult(name, reason="invalid_trigger_condition")
    if name in BUSINESS_GATES:
        result = verify(name, event, observation, state["resources"])
        if not isinstance(result, GateResult) or result.name != name:
            return GateResult(name, reason="invalid_gate_evidence")
        if result.status == "passed" and (not result.evidence_refs or not result.resource_ids):
            return GateResult(name, reason="ledger_evidence_missing")
        if result.status not in {"passed", "blocked", "failed"}:
            return GateResult(name, reason="invalid_gate_status")
        return result
    committed = state["committed"]
    previous = event.get("gate", {}).get("after_step")
    previous = "initial_message" if previous == "initial_message" else event.get("requires_event_id")
    if previous is None:
        previous = "initial_message"
    run = observation.get("run") or {}
    references = tuple(observation.get("evidence_refs", ()))
    passed, reason = False, "condition_not_met"
    if name == "previous_step_committed":
        passed = previous in committed and bool(committed[previous].get("evidence_refs"))
        references = tuple(committed.get(previous, {}).get("evidence_refs", ()))
    elif name == "event_dependencies":
        dependency = event.get("requires_event_id")
        passed = dependency is None or dependency in committed
        after = event.get("gate", {}).get("after_step")
        if after is not None:
            passed = passed and after == (dependency.rsplit("-", 1)[-1] if dependency else "initial_message")
        references = ("cursor:initial_message" if dependency is None else "cursor:" + dependency,)
    elif name == "event_not_already_applied":
        passed = event["event_id"] not in committed
        references = ("cursor:" + event["event_id"],)
        if event.get("replay_same_event") is True:
            references = tuple(committed.get(event["event_id"], {}).get("evidence_refs", ()))
            passed = bool(references)
    elif name == "not_before":
        passed = timestamp(now) >= timestamp(event["not_before"])
        references = ("simulation_clock:" + str(now),)
        reason = "not_before_unreached"
    elif name == "record_scope_matches_branch":
        expected = state["scope"]
        gate_scope = event.get("gate", {}).get("scope", expected)
        record = event.get("payload", {}).get("record", event.get("payload", {}))
        passed = all(observation.get(k) == v and gate_scope.get(k) == v
                     and record.get(k, v) == v for k, v in expected.items())
        passed = passed and observation.get("conversation_id") == state["resources"].get("conversation_id")
        reason = "scope_mismatch"
    elif name in {"actual_agent_run_completed", "after_initial_agent_turn"}:
        step = "initial_message" if name == "after_initial_agent_turn" else previous
        passed = run_completed(observation, step, history=name == "after_initial_agent_turn")
        reason = "matching_committed_run_missing"
    elif name == "no_reference_reply_injection":
        passed = not has_forbidden(event)
        references = ("controller_sha256:" + state["controller_hash"],)
    elif name == "staff_identity_required":
        passed = bool(authorization.get("staff_id", "").strip())
        references = ("staff:" + authorization["staff_id"],) if passed else ()
    elif name == "resolution_reason_recorded":
        passed = bool(authorization.get("resolution_reason", "").strip())
        references = ("resolution_reason:explicit_authorization",) if passed else ()
    elif name == "checkpoint_conditions_verified_by_controller":
        if checkpoint is None:
            return GateResult(name, "awaiting_checkpoint", "explicit_checkpoint_evidence_required")
        passed = (checkpoint.event_id == event["event_id"] and bool(checkpoint.staff_id.strip())
                  and checkpoint.run_id == run.get("id") and checkpoint.revision == observation.get("revision")
                  and bool(checkpoint.evidence_refs) and bool(checkpoint.reason.strip()))
        if not passed:
            return GateResult(name, reason="checkpoint_evidence_mismatch")
        return GateResult(name, "passed" if checkpoint.passed is True else "failed", checkpoint.reason,
                          checkpoint.evidence_refs, observation.get("ledger_resource_ids", {}), checkpoint.run_id)
    return GateResult(name, "passed" if passed else "blocked", "verified" if passed else reason,
                      references, observation.get("ledger_resource_ids", {}), run.get("id"))
