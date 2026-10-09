"""Fail-closed sequential controller unit tests, with no database or paid model."""
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from journey_driver_fixture import CallbackHarness, NOW, SCENARIO, driver, event, verification
from globalmail_agent.evaluation.journey_driver import CommitResult, JourneyDriver, load_controller
from globalmail_agent.evaluation.journey_gates import GateResult


class JourneyDriverTests(unittest.TestCase):
    def test_text_checkpoint_never_defaults_to_pass(self):
        subject, callbacks = driver()
        result = subject.advance(NOW)
        self.assertEqual("awaiting_checkpoint", result["status"])
        self.assertIn("explicit_checkpoint_evidence_required", result["steps"][0]["reason"])
        self.assertEqual([], callbacks.deliveries)
        self.assertEqual(0, result["cursor"])

    def test_checkpoint_needs_bound_staff_run_revision_and_evidence(self):
        for changes in ({"staff_id": ""}, {"run_id": "unrelated"}, {"revision": 8},
                        {"evidence_refs": ()}, {"reason": ""}, {"event_id": "future"}):
            with self.subTest(changes=changes):
                subject, callbacks = driver()
                result = subject.advance(NOW, checkpoint=verification(**changes))
                self.assertEqual("blocked", result["status"])
                self.assertEqual([], callbacks.deliveries)

    def test_failed_checkpoint_keeps_future_steps_unrun(self):
        subject, _ = driver([event(), event(2, "customer_message")])
        result = subject.advance(NOW, checkpoint=verification(passed=False, reason="Incorrect SKU in reply"))
        self.assertEqual("failed", result["steps"][0]["status"])
        self.assertEqual("not_run", result["steps"][1]["status"])
        self.assertEqual(0, result["cursor"])

    def test_checkpoint_records_evidence_without_injecting_message(self):
        subject, callbacks = driver([event(), event(2, "customer_message")])
        subject.advance(NOW, checkpoint=verification())
        self.assertEqual([], callbacks.deliveries)
        result = subject.advance(NOW)
        self.assertEqual(2, result["cursor"])
        self.assertEqual(1, len(callbacks.deliveries))
        self.assertEqual("customer_message", callbacks.deliveries[0]["kind"])
        self.assertNotIn("gate", callbacks.deliveries[0])
        self.assertNotIn("trigger_condition", callbacks.deliveries[0])
        self.assertEqual("run:actual", result["steps"][0]["run"]["id"])

    def test_queued_failed_or_unrelated_run_cannot_verify_checkpoint(self):
        for key, value in (("status", "queued"), ("status", "failed"), ("outcome", None), ("observed_steps", ["future"])):
            subject, callbacks = driver()
            callbacks.observation["run"][key] = value
            self.assertEqual("blocked", subject.advance(NOW, checkpoint=verification())["status"])

    def test_old_completed_run_cannot_authorize_current_queued_checkpoint(self):
        subject, callbacks = driver()
        callbacks.observation["runs"] = [deepcopy(callbacks.observation["run"])]
        callbacks.observation["run"]["status"] = "queued"
        self.assertEqual("blocked", subject.advance(NOW, checkpoint=verification())["status"])

    def test_time_dependency_and_after_step_hold_current_event(self):
        for change in ({"requires_event_id": "missing"}, {"not_before": "2026-10-11T00:00:00+08:00"},
                       {"gate": {"after_step": "s99", "required_business_checks": []}}):
            current = event(kind="customer_message") | change
            subject, callbacks = driver([current])
            self.assertEqual("blocked", subject.advance(NOW)["status"])
            self.assertEqual([], callbacks.deliveries)

    def test_wrong_scope_or_injected_answer_never_reaches_service(self):
        for current in (event(kind="customer_message") | {"payload": {"record": {"customer_id": "other"}}},
                        event(kind="customer_message") | {"payload": {"reference_reply": "expected"}}):
            subject, callbacks = driver([current])
            self.assertEqual("blocked", subject.advance(NOW)["status"])
            self.assertEqual([], callbacks.deliveries)
        subject, callbacks = driver([event(kind="customer_message")])
        callbacks.observation["conversation_id"] = "other"
        self.assertEqual("blocked", subject.advance(NOW)["status"])

    def test_unknown_gate_is_not_silently_ignored_or_delegated(self):
        subject, callbacks = driver([event(kind="execution_record", checks=["undefined_check"])])
        result = subject.advance(NOW)
        self.assertEqual("blocked", result["status"])
        self.assertIn("undefined_check:unknown_gate", result["steps"][0]["reason"])
        self.assertNotIn("undefined_check", callbacks.checked)

    def test_business_gate_requires_real_resource_and_evidence_contract(self):
        gate = "actual_internal_request_exists"
        for proof in (GateResult(gate, "passed"), GateResult(gate, "passed", evidence_refs=("ref",)),
                      GateResult("wrong_name", "passed", evidence_refs=("ref",), resource_ids={"id": "op"})):
            subject, callbacks = driver([event(kind="execution_record", checks=[gate])])
            callbacks.gate_results[gate] = proof
            self.assertEqual("blocked", subject.advance(NOW)["status"])
        subject, callbacks = driver([event(kind="execution_record", checks=[gate])])
        callbacks.gate_results[gate] = GateResult(gate, "passed", "ledger query matched selector",
                                                ("operation:actual:version1",), {"operation_id": "operation:actual"})
        result = subject.advance(NOW)
        self.assertEqual("applied", result["steps"][0]["status"])
        self.assertEqual("operation:actual", result["steps"][0]["ledger_resource_ids"]["operation_id"])

    def test_human_close_requires_explicit_identity_and_reason(self):
        subject, callbacks = driver([event(kind="human_close")])
        for checks in ({}, {"staff_id": "staff"}, {"resolution_reason": "Customer confirmed"}):
            self.assertEqual("blocked", subject.advance(NOW, **checks)["status"])
        self.assertEqual([], callbacks.deliveries)
        result = subject.advance(NOW, staff_id="staff", resolution_reason="Customer confirmed")
        self.assertEqual("applied", result["steps"][0]["status"])

    def test_uncommitted_receipt_is_blocked_and_retry_keeps_same_command(self):
        subject, callbacks = driver([event(kind="customer_message")])
        callbacks.receipt = CommitResult(False, reason="version_conflict")
        self.assertEqual("blocked", subject.advance(NOW)["status"])
        callbacks.receipt = CommitResult(True, ("message:actual",))
        self.assertEqual(1, subject.advance(NOW)["cursor"])
        self.assertEqual(callbacks.commands[-2], callbacks.commands[-1])

    def test_receipt_cannot_create_shadow_ledger_in_resource_mapping(self):
        subject, callbacks = driver([event(kind="customer_message")])
        callbacks.receipt = CommitResult(True, ("message:actual",), {"orders": [{"status": "succeeded"}]})
        result = subject.advance(NOW)
        self.assertEqual("blocked", result["status"])
        self.assertNotIn("orders", result["resources"])

    def test_cursor_resume_keeps_real_mapping_and_does_not_replay(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "cursor.json"
            subject, callbacks = driver([event(kind="customer_message")], state_path=path)
            subject.advance(NOW)
            resumed = JourneyDriver(deepcopy(SCENARIO), [event(kind="customer_message")],
                                    "fixture-hash", callbacks, state_path=path)
            resumed.start()
            resumed.advance(NOW)
            self.assertEqual(1, len(callbacks.deliveries))
            self.assertEqual("operation:actual", resumed.state["resources"]["operation:source"])
            stored = json.loads(path.read_text(encoding="utf-8"))
            self.assertNotIn("orders", stored)
            with self.assertRaisesRegex(ValueError, "source_mismatch"):
                JourneyDriver(SCENARIO, [], "changed-hash", callbacks, state_path=path)

    def test_eventless_initial_input_needs_actual_run_before_completion(self):
        subject, callbacks = driver([])
        callbacks.observation["run"]["status"] = "queued"
        self.assertEqual("in_progress", subject.advance(NOW)["status"])
        callbacks.observation["run"]["status"] = "completed"
        self.assertEqual("completed", subject.advance(NOW)["status"])

    def test_legacy_triggers_are_individual_required_gates(self):
        for trigger in ({"after_matching_internal_request": {"kind": "refund"}},
                        {"after_internal_return_request": True}):
            subject, callbacks = driver([event(kind="execution_record", trigger=trigger)])
            self.assertEqual("blocked", subject.advance(NOW)["status"])
            self.assertIn(next(iter(trigger)), callbacks.checked)
        subject, _ = driver([event(kind="customer_message", trigger={"after_initial_agent_turn": True})])
        self.assertEqual("applied", subject.advance(NOW)["steps"][0]["status"])
        subject, _ = driver([event(kind="customer_message", trigger={"after_initial_agent_turn": False})])
        self.assertEqual("blocked", subject.advance(NOW)["status"])

    def test_initial_completed_turn_can_come_from_actual_run_history(self):
        subject, callbacks = driver([event(kind="customer_message", trigger={"after_initial_agent_turn": True})])
        callbacks.observation["runs"] = [deepcopy(callbacks.observation["run"])]
        callbacks.observation["run"] = {"id": "later", "status": "completed", "outcome": "wait_business",
                                         "observed_steps": ["later_event"]}
        self.assertEqual("applied", subject.advance(NOW)["steps"][0]["status"])

    def test_service_and_gate_failures_are_reported(self):
        subject, callbacks = driver([event(kind="execution_record", checks=["exact_item_compatible"])])
        def unavailable(*args):
            raise ConnectionError("private details")
        callbacks.verify_gate = unavailable
        result = subject.advance(NOW)
        self.assertIn("gate_error:ConnectionError", result["steps"][0]["reason"])
        self.assertNotIn("private details", json.dumps(result))
        callbacks.verify_gate = lambda *args: GateResult(args[0], "passed", "verified", ("ref",), {"id": "part"})
        callbacks.apply = unavailable
        self.assertEqual("failed", subject.advance(NOW)["status"])


class ControllerLoaderTests(unittest.TestCase):
    def load(self, events):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "scenarios/journeys"
            path.mkdir(parents=True)
            (path / "controller-events.jsonl").write_text("\n".join(json.dumps(e) for e in events), encoding="utf-8")
            return load_controller(temporary, {"JRN-UNIT": SCENARIO})[0]["JRN-UNIT"]

    def test_unordered_input_sorted_and_identical_duplicate_deduplicated(self):
        rows = self.load([event(2), event(), event()])
        self.assertEqual([1, 2], [e["sequence"] for e in rows])

    def test_conflicting_duplicate_sequence_gap_and_future_dependency_rejected(self):
        for rows in ([event(), event() | {"kind": "human_close"}], [event(2)],
                     [event() | {"requires_event_id": "JRN-UNIT-s02"}, event(2)]):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                self.load(rows)

    def test_explicit_replay_is_retained_and_reported_without_redelivery(self):
        rows = self.load([event(kind="customer_message"),
                          event(kind="customer_message") | {"replay_same_event": True}])
        self.assertEqual(2, len(rows))
        subject, callbacks = driver(rows)
        subject.advance(NOW)
        result = subject.advance(NOW)
        self.assertEqual(1, len(callbacks.deliveries))
        self.assertEqual("duplicate_suppressed", result["steps"][1]["status"])
        self.assertEqual("domain_event:committed", result["steps"][1]["commit_evidence_refs"][0])
