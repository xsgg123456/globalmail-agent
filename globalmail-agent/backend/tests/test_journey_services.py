"""Real isolated services/Graph observations; authored checkpoints never become fake approvals."""
from uuid import UUID
import json
from pathlib import Path
from agent_fixture import AgentFixture, ScriptedModel, understanding, call
from globalmail_agent.adapters.fixture_loader import FixturePackage
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
from globalmail_agent.evaluation.scenario_driver import ScenarioDriver
from globalmail_agent.evaluation.service_adapter import ServiceAdapter
from globalmail_agent.worker.agent_runner import AgentRunner
from globalmail_agent.evaluation.reporting import save_json


class JourneyServiceTests(AgentFixture):
    def test_actual_graph_handoff_is_observed_but_text_checkpoint_is_still_pending(self):
        package = FixturePackage()
        model = ScriptedModel(understanding([]), {"calls": [call("request_human_review", {
            "reason": "no_applicable_evidence", "summary": "隔离工程运行：尚未核验资料", "gaps": ["需核对当前资料"], "draft": ""})]})
        runner = AgentRunner(self.engine, self.store, DEFAULT_WORKSPACE_ID, model, None)
        adapter = ServiceAdapter(self.engine, self.store, package, runner=runner)
        driver = ScenarioDriver(package, adapter, state_directory=Path(self.temp.name) / "controller")
        driver.start("JRN-01")
        scenario = driver.drivers["JRN-01"]
        observed = adapter.observe("JRN-01", scenario.state["resources"])
        self.assertEqual(observed["run"]["status"], "handed_off")
        self.assertIn("initial_message", observed["run"]["observed_steps"])
        report = driver.advance("JRN-01", "2026-10-08T10:12:00+08:00")
        self.assertEqual(scenario.state["position"], 0)
        self.assertIn("awaiting_checkpoint", str(report))
        self.assertEqual(len(model.requests), 2)
        self.assertEqual(self.outbound(UUID(scenario.state["resources"]["conversation_id"])), [])
        self.assertEqual(len(driver.report()["scenarios"]), 72)
        output = Path(self.temp.name) / "actual-report.json"
        save_json(output, driver.report())
        persisted = json.loads(output.read_text(encoding="utf-8"))
        actual = next(r for r in persisted["scenarios"] if r["scenario_id"] == "JRN-01")
        self.assertIsInstance(actual["steps"][0]["run"]["started_at"], str)
        self.assertTrue((Path(self.temp.name) / "controller/JRN-01.json").is_file())
