"""Original package coverage and visibility, not a fabricated 72-case run."""
import unittest
from pathlib import Path
from unittest.mock import patch

from journey_driver_fixture import CallbackHarness
from globalmail_agent.adapters.fixture_loader import FixturePackage
from globalmail_agent.evaluation.journey_driver import load_controller
from globalmail_agent.evaluation.journey_gates import KNOWN_GATES
from globalmail_agent.evaluation.scenario_driver import ScenarioDriver


class OriginalScenarioDriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = FixturePackage()

    def test_catalog_reports_all_original_inputs_and_journeys_as_not_run(self):
        result = ScenarioDriver(self.package, CallbackHarness()).report()
        self.assertEqual(72, result["scenario_count"])
        self.assertEqual({"not_run": 72}, result["statuses"])
        originals = [s for s in result["scenarios"] if not s["scenario_id"].startswith("JRN-")]
        journeys = [s for s in result["scenarios"] if s["scenario_id"].startswith("JRN-")]
        self.assertEqual(51, len(originals))
        self.assertEqual(21, len(journeys))
        self.assertEqual(48, sum(len(s["steps"]) for s in originals))
        self.assertEqual(287, sum(len(s["steps"]) for s in journeys))
        self.assertTrue(all(step["status"] == "not_run" for s in result["scenarios"] for step in s["steps"]))
        self.assertIsNone(result["production_accuracy"])

    def test_every_original_gate_and_trigger_has_a_named_handler(self):
        for journeys in (True, False):
            scenarios = {sid: row for sid, row in self.package.scenarios.items()
                         if sid.startswith("JRN-") == journeys}
            grouped, _ = load_controller(self.package.root, scenarios, journeys=journeys)
            rows = [r for events in grouped.values() for r in events]
            names = {g for r in rows for g in r.get("gate", {}).get("required_business_checks", [])}
            names |= {g for r in rows for g in r.get("trigger_condition", {})}
            self.assertFalse(names - KNOWN_GATES)
            if journeys:
                self.assertEqual(81, sum(r["kind"] == "checkpoint" for r in rows))
                self.assertEqual(24, len(names))
            else:
                self.assertEqual({"after_initial_agent_turn", "after_matching_internal_request",
                                  "after_internal_return_request"}, names)

    def test_controller_loader_never_opens_evaluation_or_readable_stories(self):
        opened = []
        original = Path.read_bytes
        def audit(path):
            opened.append(path.as_posix())
            return original(path)
        with patch.object(Path, "read_bytes", audit):
            ScenarioDriver(self.package, CallbackHarness())
        self.assertEqual(2, len(opened))
        self.assertTrue(all(path.endswith("controller-events.jsonl") for path in opened))

    def test_missing_stock_specification_and_snapshot_are_not_filled(self):
        before = [dict(row) for row in self.package.scenarios["JRN-01"]["initial_state"]["inventory"]]
        ScenarioDriver(self.package, CallbackHarness())
        after = self.package.scenarios["JRN-01"]["initial_state"]["inventory"]
        self.assertEqual(before, after)
        self.assertTrue(all("region_spec" not in row and "snapshot_at" not in row for row in after))
