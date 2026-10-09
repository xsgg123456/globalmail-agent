"""Catalog of original 51 inputs and 21 journeys, with isolated controllers."""
from pathlib import Path

from globalmail_agent.evaluation.journey_driver import JourneyDriver, load_controller
from globalmail_agent.evaluation.reporting import suite_report


class ScenarioDriver:
    def __init__(self, package, callbacks, *, state_directory=None):
        self.drivers = {}
        for journeys in (False, True):
            scenarios = {sid: row for sid, row in package.scenarios.items()
                         if sid.startswith("JRN-") == journeys}
            events, source_hash = load_controller(package.root, scenarios, journeys=journeys)
            for sid, scenario in scenarios.items():
                # Paths derive only from the trusted catalog, never HTTP input.
                path = Path(state_directory) / (sid + ".json") if state_directory else None
                self.drivers[sid] = JourneyDriver(scenario, events[sid], source_hash, callbacks, state_path=path)

    def start(self, scenario_id):
        return self.drivers[scenario_id].start()

    def advance(self, scenario_id, now, **checks):
        return self.drivers[scenario_id].advance(now, **checks)

    def report(self):
        return suite_report([driver.report() for driver in self.drivers.values()])
