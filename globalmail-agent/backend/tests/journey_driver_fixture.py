"""In-memory callback contract tests; this is not an Agent/business acceptance run."""
from copy import deepcopy

from globalmail_agent.evaluation.journey_driver import CommitResult, JourneyDriver
from globalmail_agent.evaluation.journey_gates import CheckpointVerification, GateResult


NOW = "2026-10-10T00:00:00+08:00"
SCENARIO = {"scenario_id": "JRN-UNIT", "branch_id": "source-branch",
            "access_scope": {"customer_id": "source-customer"}, "initial_messages": [{"body": "hello"}]}


def event(sequence=1, kind="checkpoint", *, checks=(), trigger=None):
    dependency = "JRN-UNIT-s%02d" % (sequence - 1) if sequence > 1 else None
    return {"event_id": "JRN-UNIT-s%02d" % sequence, "scenario_id": "JRN-UNIT",
            "sequence": sequence, "kind": kind, "source_kind": "synthetic", "actor": "staff",
            "not_before": "2026-10-09T12:00:00+08:00", "requires_event_id": dependency,
            "gate": {"after_step": dependency.rsplit("-", 1)[-1] if dependency else "initial_message",
                     "scope": {"branch_id": "source-branch", "customer_id": "source-customer"},
                     "required_business_checks": list(checks)}, "payload": {"text": "Inspect actual result.", "record": {}},
            "trigger_condition": trigger or {}, "agent_can_create": False}


class CallbackHarness:
    def __init__(self):
        self.deliveries, self.commands, self.checked = [], [], []
        self.gate_results = {}
        self.receipt = CommitResult(True, ("domain_event:committed",), {"operation:source": "operation:actual"})
        self.observation = {"branch_id": "source-branch", "customer_id": "source-customer",
                            "conversation_id": "conversation:actual", "revision": 7,
                            "evidence_refs": ["snapshot:7"], "ledger_resource_ids": {"operation_id": "operation:actual"},
                            "run": {"id": "run:actual", "status": "completed", "outcome": "reply_and_wait",
                                    "observed_steps": ["initial_message"]}}

    def create(self, scenario_id, initial, command_id):
        self.commands.append(command_id)
        return CommitResult(True, ("message:actual",), {"conversation_id": "conversation:actual"}, ("run:actual",))

    def observe(self, scenario_id, resources):
        return deepcopy(self.observation)

    def apply(self, delivery, resources, command_id, authorization):
        self.deliveries.append(deepcopy(delivery))
        self.commands.append(command_id)
        self.observation["run"]["observed_steps"].append(delivery["event_id"])
        return self.receipt

    def verify_gate(self, name, event, observation, resources):
        self.checked.append(name)
        return self.gate_results.get(name, GateResult(name))


def verification(**changes):
    values = {"event_id": "JRN-UNIT-s01", "staff_id": "tester", "run_id": "run:actual",
              "revision": 7, "evidence_refs": ("reply:actual",), "passed": True,
              "reason": "Manually inspected the actual committed reply and tool evidence."}
    return CheckpointVerification(**(values | changes))


def driver(events=None, callbacks=None, state_path=None):
    callbacks = callbacks or CallbackHarness()
    result = JourneyDriver(deepcopy(SCENARIO), events if events is not None else [event()],
                           "fixture-hash", callbacks, state_path=state_path)
    result.start()
    return result, callbacks
