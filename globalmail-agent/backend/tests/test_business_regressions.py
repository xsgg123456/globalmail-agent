"""Review regressions exercise persisted facts through actual query/service boundaries."""
from copy import deepcopy
from uuid import UUID, uuid4

from globalmail_agent.adapters.fixture_loader import FixturePackage
from globalmail_agent.application.fixture_conversations import FixtureConversations
from globalmail_agent.application.business_queries import BusinessQueries
from globalmail_agent.domain.conversation import Command
from globalmail_agent.domain.policy import EligibilityRequest
from globalmail_agent.adapters import business_schema as bs
from sqlalchemy import select
from fastapi.testclient import TestClient
from pathlib import Path
from globalmail_agent.main import create_app
from globalmail_agent.settings import Settings
from test_protocol import ProtocolFixture


class BusinessRegressionTests(ProtocolFixture):
    def setUp(self):
        super().setUp()
        self.package = FixturePackage()
        self.fixtures = FixtureConversations(self.engine, self.service.store, self.package)
        self.queries = BusinessQueries(self.engine)
        self.client = TestClient(create_app(Settings(object_root=Path(self.temp.name)),
            engine=self.engine, start_worker=False), base_url="http://127.0.0.1:18080")
        self.addCleanup(self.client.close)

    def preview(self, cid, command):
        response = self.client.post(f"/api/v1/conversations/{cid}/eligibility",
            json=command.model_dump(), headers={"Origin": "http://127.0.0.1:15173"})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]

    def create(self, scenario):
        self.package.validate(scenario)
        self.package.scenarios[scenario["scenario_id"]] = scenario
        return UUID(self.fixtures.create(scenario["scenario_id"],
            Command(expected_version=0), uuid4().hex)["conversation_id"])

    def test_inspected_share_survives_database_projection_and_service(self):
        for inspected_quantity, inspected_units, expected in (
                (1, ["0"], "wait"), (2, ["0", "1"], "fulfilled"), (1, None, "needs_input")):
            with self.subTest(inspected_quantity=inspected_quantity, inspected_units=inspected_units):
                scenario = deepcopy(self.package.scenarios["BASE-OUTON-04"])
                scenario["scenario_id"] = "TEST-INSPECTION-" + uuid4().hex
                state = scenario["initial_state"]
                line = state["orders"][0]["lines"][0]
                line["quantity"] = 2
                state["customer_choices"][0].update(order_line_id=line["line_id"], quantity=2)
                receipt = state["returns"][0]
                receipt.update(quantity=2, inspected_quantity=inspected_quantity)
                if inspected_units is not None:
                    receipt["inspected_unit_ids"] = inspected_units
                cid = self.create(scenario)
                projected = self.queries.eligibility_context(cid)["data"]["state"]["returns"][0]
                self.assertEqual(projected["inspected_quantity"], inspected_quantity)
                self.assertEqual(projected.get("inspected_unit_ids"), inspected_units)
                response = self.preview(cid, EligibilityRequest(
                    action="refund", order_line_id=line["line_id"], quantity=2,
                    amount_minor=5499, currency="USD"))
                self.assertEqual(response["status"], "ok")
                decision = response["data"]
                statuses = [c["status"] for c in decision["conditions"] if c["code"] == "warehouse_inspection"]
                self.assertIn(expected, statuses)
                self.assertEqual(decision["outcome"] == "eligible", expected == "fulfilled")
                self.assertFalse(decision["authorized"])

    def test_historical_parent_does_not_authorize_synthetic_child_line(self):
        scenario = deepcopy(self.package.scenarios["SCN-029"])
        scenario["scenario_id"] = "TEST-HISTORY-MIXED"
        order = scenario["initial_state"]["orders"][0]
        order["source_kind"] = "historical_order_snapshot"
        cid = self.create(scenario)
        result = self.queries.detail(cid)
        self.assertEqual(result["status"], "needs_input")
        self.assertEqual(len(result["data"]["orders"]), 1)
        self.assertEqual(result["data"]["orders"][0]["lines"], [])
        self.assertNotIn("H-CTD16-US-BK", str(result))
        self.assertEqual(self.queries.eligibility_context(cid)["status"], "needs_input")

    def test_public_choices_exclude_future_messages_and_private_address_tokens(self):
        scenario = deepcopy(self.package.scenarios["BASE-OUTON-04"])
        scenario["scenario_id"] = "TEST-VISIBLE-CHOICE"
        scenario["initial_state"]["customer_choices"].append({"kind": "replacement", "accepted": True,
            "source_message_id": "FUTURE-NOT-VISIBLE", "address_version": 99})
        cid = self.create(scenario)
        data = self.queries.detail(cid)["data"]
        choice, = data["customer_choices"]
        self.assertEqual(choice["action"], "refund")
        self.assertTrue(choice["accepted"])
        self.assertEqual(choice["amount_minor"], 5499)
        self.assertEqual(choice["quantity"], 1)
        self.assertEqual(choice["source_message_seq"], 1)
        self.assertEqual(choice["order_line_id"], data["orders"][0]["lines"][0]["line_id"])
        self.assertEqual(data["address_confirmation"]["version"], 1)
        self.assertNotIn("address_token", str(data))
        self.assertNotIn("FUTURE-NOT-VISIBLE", str(data))
        with self.engine.connect() as conn:
            state = conn.execute(select(bs.simulation_branches.c.state).where(
                bs.simulation_branches.c.conversation_id == cid)).scalar_one()
        self.assertEqual(len(state["customer_choices"]), 2)  # Hidden input really exists in the DB.

    def test_multi_line_choice_remains_unbound_without_explicit_target(self):
        scenario = deepcopy(self.package.scenarios["SCN-008"])
        scenario["scenario_id"] = "TEST-CHOICE-AMBIGUOUS"
        scenario["initial_state"]["customer_choices"] = [{"kind": "refund", "accepted": True,
            "source_message_id": scenario["initial_messages"][0]["message_id"]}]
        cid = self.create(scenario)
        detail = self.queries.detail(cid)
        self.assertEqual(detail["status"], "needs_input")
        choice, = detail["data"]["customer_choices"]
        self.assertNotIn("order_line_id", choice)
        self.assertNotIn("quantity", choice)

    def test_latest_choice_uses_message_sequence_not_fixture_array_order(self):
        for changed in ({"accepted": False}, {"kind": "return", "accepted": True},
                        {"accepted": True, "order_line_id": None}):
            with self.subTest(changed=changed):
                scenario = deepcopy(self.package.scenarios["BASE-OUTON-04"])
                scenario["scenario_id"] = "TEST-CHOICE-ORDER-" + uuid4().hex
                line = scenario["initial_state"]["orders"][0]["lines"][0]
                older = scenario["initial_state"]["customer_choices"][0]
                older.update(order_line_id=line["line_id"], quantity=1)
                latest = {**older, **changed, "source_message_id": "TEST-LATEST-MESSAGE"}
                scenario["initial_state"]["customer_choices"] = [latest, older]
                message = {**scenario["initial_messages"][0], "message_id": "TEST-LATEST-MESSAGE",
                    "received_at": "2026-10-08T10:01:00+08:00", "body": "I changed my decision. Please check my latest request."}
                scenario["initial_messages"].append(message)
                cid = self.create(scenario)
                choices = self.queries.detail(cid)["data"]["customer_choices"]
                self.assertEqual([c["source_message_seq"] for c in choices], [1, 2])
                decision = self.preview(cid, EligibilityRequest(
                    action="refund", quantity=1, amount_minor=5499, currency="USD"))["data"]
                self.assertNotEqual(decision["outcome"], "eligible")
                self.assertIn("needs_input", [c["status"] for c in decision["conditions"]
                    if c["code"] == "customer_choice"])

    def test_inventory_time_gap_cannot_become_eligible_in_formal_http(self):
        for snapshot in (None, "2026-10-08T09:00:00+08:00", "2026-10-09T09:00:00+08:00"):
            with self.subTest(snapshot=snapshot):
                scenario = deepcopy(self.package.scenarios["BASE-OUTON-04"])
                scenario["scenario_id"] = "TEST-STOCK-TIME-" + uuid4().hex
                state = scenario["initial_state"]
                line = state["orders"][0]["lines"][0]
                sku = line["sku"]
                self.package.by_sku[sku]["market"] = "US"  # Explicit simulated specification, not SKU inference.
                state["defect_confirmed_in_simulation"] = True
                state["customer_choices"][0].update(kind="replacement", quantity=1,
                    order_line_id=line["line_id"], item_id=sku, address_version=1)
                stock = state["inventory"][0]
                stock.update(region_spec="US", hardware_revision="SIM-V1", snapshot_at=snapshot)
                cid = self.create(scenario)
                availability = self.queries.availability(cid, line["line_id"], sku)
                valid = snapshot == "2026-10-08T09:00:00+08:00"
                self.assertEqual(availability["status"], "ok" if valid else "unknown")
                if not valid:
                    self.assertIsNone(availability["data"]["available_quantity"])
                decision = self.preview(cid, EligibilityRequest(action="replacement",
                    order_line_id=line["line_id"], quantity=1, item_id=sku))["data"]
                self.assertEqual(decision["outcome"], "eligible" if valid else "needs_input")
                self.assertFalse(decision["authorized"])
                self.assertIn("fulfilled" if valid else "needs_input", [c["status"]
                    for c in decision["conditions"] if c["code"] == "inventory"])

    def test_loading_fixture_cannot_upgrade_visual_evidence_to_warehouse_fact(self):
        scenario = deepcopy(self.package.scenarios["BASE-OUTON-04"])
        scenario["scenario_id"] = "TEST-VISUAL-NOT-WAREHOUSE"
        scenario["initial_state"]["returns"][0]["source_kind"] = "visual_observation"
        cid = self.create(scenario)
        decision = self.preview(cid, EligibilityRequest(action="refund", quantity=1,
            amount_minor=5499, currency="USD"))["data"]
        self.assertNotEqual(decision["outcome"], "eligible")
        self.assertNotIn("fulfilled", [c["status"] for c in decision["conditions"]
            if c["code"] == "warehouse_receipt"])

    def test_future_address_confirmation_is_not_projected_or_used(self):
        scenario = deepcopy(self.package.scenarios["BASE-OUTON-07"])
        scenario["scenario_id"] = "TEST-FUTURE-ADDRESS"
        scenario["initial_state"]["address_confirmation"]["source_message_id"] = "NOT-YET-VISIBLE"
        cid = self.create(scenario)
        self.assertIsNone(self.queries.detail(cid)["data"]["address_confirmation"])
        self.assertNotIn("address_confirmation", self.queries.eligibility_context(cid)["data"]["state"])
