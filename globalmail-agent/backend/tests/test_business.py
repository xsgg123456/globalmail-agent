"""Business ledger checks run only in ProtocolFixture's disposable PG schema."""
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from uuid import UUID, uuid4
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from test_protocol import ProtocolFixture
from globalmail_agent.adapters import business_schema as bs
from globalmail_agent.adapters.conversation_schema import jobs, human_reviews, replay_cursors, conversations
from globalmail_agent.adapters.fixture_loader import FixturePackage
from globalmail_agent.application.fixture_conversations import FixtureConversations
from globalmail_agent.application.business_queries import BusinessQueries
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.domain.conversation import Command
from globalmail_agent.adapters.schema import SCOPE_KEYS


class BusinessTests(ProtocolFixture):
    def setUp(self):
        super().setUp()
        self.package = FixturePackage()
        self.fixtures = FixtureConversations(self.engine, self.service.store, self.package)
        self.queries = BusinessQueries(self.engine)

    def scene(self, name="BASE-OUTON-01", key=None):
        return self.fixtures.create(name, Command(expected_version=0), key or uuid4().hex)

    def test_whitelist_sources_and_policy_bundle_are_verified(self):
        accessed = []
        original = Path.read_bytes
        def reading(path):
            accessed.append(path.relative_to(self.package.root).as_posix())
            return original(path)
        with patch.object(Path, "read_bytes", reading):
            loaded = FixturePackage()
        self.assertEqual(len(loaded.scenarios), 72)
        self.assertEqual(set(accessed), {"products.json", "parts.json", "compatibility.json", "inventory.json",
            "policies/policy-profile.json", "policies/policy-profile.md", "authoring/policy-profile.json",
            "sources/policy-render.json", "scenarios/inputs.jsonl", "scenarios/journeys/inputs.jsonl"})
        def corrupt(path):
            data = original(path)
            return data + b"changed" if path.name == "policy-profile.md" else data
        with patch.object(Path, "read_bytes", corrupt), self.assertRaisesRegex(ValueError, "policy_bundle_mismatch"):
            FixturePackage()

    def test_scene_receipt_reuse_and_dataset_separation(self):
        key = uuid4().hex
        first = self.scene(key=key)
        self.assertEqual(self.scene(key=key), first)
        with self.assertRaises(ServiceError) as error:
            self.scene("BASE-OUTON-02", key)
        self.assertEqual(error.exception.code, "idempotency_conflict")
        second = self.scene("JRN-01")  # Same sender in the prepared inputs.
        with self.engine.connect() as conn:
            rows = conn.execute(sa.select(conversations).where(conversations.c.id.in_(
                [UUID(first["conversation_id"]), UUID(second["conversation_id"])]))).mappings().all()
        for key in ("dataset_id", "identity_id", "branch_id", "customer_id"):
            self.assertNotEqual(rows[0][key], rows[1][key])
        before = self.count(jobs)
        for _ in range(2):
            self.queries.detail(UUID(first["conversation_id"]))
            self.queries.eligibility_context(UUID(first["conversation_id"]))
        self.assertEqual(self.count(jobs), before)

    def test_order_facts_unknown_inventory_and_visible_choices(self):
        cid = UUID(self.scene("BASE-OUTON-04")["conversation_id"])
        detail = self.queries.detail(cid)
        self.assertEqual(detail["status"], "ok")
        order, = detail["data"]["orders"]
        line, = order["lines"]
        self.assertEqual(order["display_order_number"], "999-7100004-8100000")
        self.assertEqual(line["paid_minor"], 5499)
        self.assertFalse(order["is_realtime"])
        availability = self.queries.availability(cid, line["line_id"], line["sku"])
        self.assertEqual(availability["status"], "unknown")
        self.assertEqual(availability["data"]["on_hand"], 5)
        self.assertIsNone(availability["data"]["snapshot_at"])
        self.assertIsNone(availability["data"]["available_quantity"])
        context = self.queries.eligibility_context(cid)["data"]
        self.assertEqual(context["state"]["customer_choices"][0]["source_kind"], "verified_fixture")
        self.assertEqual(context["policy_metadata"]["publication_status"], "unpublished")
        self.assertNotIn("tool_overrides", context["state"])

    def test_every_scenario_initial_ledger_can_be_materialized(self):
        for name in self.package.scenarios:
            with self.subTest(scenario=name):
                cid = UUID(self.scene(name)["conversation_id"])
                response = self.queries.detail(cid)
                self.assertNotEqual(response["status"], "error")
        self.assertEqual(self.count(bs.simulation_branches), 72)
        self.assertEqual(self.count(bs.operations), 5)
        self.assertEqual(self.count(bs.executions), 2)
        self.assertEqual(self.count(bs.shipments), 12)
        self.assertEqual(self.count(bs.return_receipts), 14)

    def test_multi_line_and_cross_scope_are_explicit(self):
        name = next(k for k, row in self.package.scenarios.items()
            if sum(len(o["lines"]) for o in row["initial_state"]["orders"]) > 1)
        cid = UUID(self.scene(name)["conversation_id"])
        response = self.queries.detail(cid)
        self.assertEqual(response["status"], "needs_input")
        self.assertIsNone(response["data"]["selected_line_id"])
        self.assertEqual(self.queries.detail(cid, "OTHER-ORDER")["status"], "denied")
        self.assertEqual(self.queries.detail(cid, order_line_id="OTHER-LINE")["status"], "denied")
        self.assertIsNone(self.queries.detail(cid, "OTHER-ORDER")["data"])

    def test_mock_history_cannot_read_and_cursor_uses_real_message(self):
        cid = UUID(self.scene("SCN-029")["conversation_id"])
        with self.engine.connect() as conn:
            cursor = conn.execute(sa.select(replay_cursors.c.as_of).where(replay_cursors.c.conversation_id == cid)).scalar_one()
        self.assertEqual(cursor.isoformat(), "2026-10-08T02:00:00+00:00")
        response = self.queries.detail(cid)
        self.assertEqual(response["status"], "unavailable")
        self.assertEqual(response["data"]["orders"], [])
        self.assertIsNone(response["data"]["policy"])

    def test_legal_history_future_snapshot_never_leaks_sku(self):
        row = deepcopy(self.package.scenarios["SCN-029"])
        row["scenario_id"] = "TEST-LEGAL-HISTORY"
        order = row["initial_state"]["orders"][0]
        order["source_kind"] = "historical_order_snapshot"
        order["snapshot_at"] = "2026-10-09T09:00:00+08:00"
        self.package.scenarios[row["scenario_id"]] = row
        cid = UUID(self.scene(row["scenario_id"])["conversation_id"])
        response = self.queries.detail(cid)
        self.assertEqual(response["status"], "unavailable")
        self.assertEqual(response["reason_code"], "historical_snapshot_unavailable")
        self.assertNotIn("H-CTD16", str(response))

    def test_human_initial_state_has_open_review_and_no_job(self):
        before = self.count(jobs)
        cid = UUID(self.scene("SCN-028")["conversation_id"])
        self.assertEqual(self.count(jobs), before)
        conversation = self.service.detail(cid)["conversation"]
        self.assertEqual(conversation["processing_owner"], "human_review")
        self.assertEqual(conversation["auto_run_gate"], "disabled")
        with self.engine.connect() as conn:
            review = conn.execute(sa.select(human_reviews).where(human_reviews.c.conversation_id == cid)).mappings().one()
        self.assertEqual(review["status"], "open")

    def test_source_snapshot_immutable_and_ledger_foreign_keys(self):
        first = UUID(self.scene("SCN-025")["conversation_id"])
        second = UUID(self.scene("SCN-012")["conversation_id"])
        with self.engine.connect() as conn:
            order = conn.execute(sa.select(bs.branch_orders).where(bs.branch_orders.c.conversation_id == first)).mappings().one()
            shipment = conn.execute(sa.select(bs.shipments).where(bs.shipments.c.order_id == order["id"])).mappings().one()
            other = conn.execute(sa.select(bs.operations).join(bs.branch_orders,
                bs.operations.c.order_id == bs.branch_orders.c.id).where(bs.branch_orders.c.conversation_id == second)).mappings().one()
        self.assertEqual(other["status"], "succeeded")
        self.assertEqual(other["source_snapshot"]["status"], "completed")
        context = self.queries.eligibility_context(first)["data"]
        self.assertEqual(context["state"]["operations"][0]["status"], "succeeded")
        self.assertEqual(context["state"]["execution_records"][0]["status"], "shipped")
        with self.assertRaises(SQLAlchemyError), self.engine.begin() as conn:
            conn.execute(bs.branch_orders.update().where(bs.branch_orders.c.id == order["id"]).values(paid_minor=1))
        with self.assertRaises(SQLAlchemyError), self.engine.begin() as conn:
            conn.execute(bs.policy_profiles.update().values(description="changed without a new version"))
        copied = dict(shipment)
        for key in ("created_at", "updated_at"):
            copied.pop(key)
        copied.update(id=uuid4(), external_id="UNRELATED", operation_id=other["id"], execution_id=None)
        with self.assertRaises(SQLAlchemyError), self.engine.begin() as conn:
            conn.execute(bs.shipments.insert().values(**copied))
        copied.update(operation_id=shipment["operation_id"], execution_id=shipment["execution_id"])
        with self.assertRaises(SQLAlchemyError), self.engine.begin() as conn:
            conn.execute(bs.return_receipts.insert().values(**{k: v for k, v in copied.items() if k != "parcel_purpose"}, quantity=0))
        with self.engine.begin() as conn:
            line = dict(conn.execute(sa.select(bs.branch_order_lines).where(
                bs.branch_order_lines.c.id == shipment["order_line_id"])).mappings().one())
            line.update(id=uuid4(), external_id="TEST-SECOND-LINE")
            conn.execute(bs.branch_order_lines.insert().values(**line))
            execution = dict(conn.execute(sa.select(bs.executions).where(bs.executions.c.id == shipment["execution_id"])).mappings().one())
        execution.update(id=uuid4(), external_id="TEST-WRONG-LINE", order_line_id=line["id"])
        with self.assertRaises(SQLAlchemyError), self.engine.begin() as conn:
            conn.execute(bs.executions.insert().values(**execution))

    def test_technical_fault_is_not_empty_and_injection_is_internal(self):
        for fault, status in (("query_failed", "error"), ("empty", "empty")):
            scenario = deepcopy(self.package.scenarios["BASE-OUTON-01"])
            scenario["scenario_id"] = "TEST-FAULT-" + fault
            scenario["tool_overrides"] = [{"tool": "get_order_snapshot", "fault": fault}]
            self.package.scenarios[scenario["scenario_id"]] = scenario
            cid = UUID(self.scene(scenario["scenario_id"])["conversation_id"])
            response = self.queries.detail(cid)
            self.assertEqual(response["status"], status)
            self.assertNotIn("tool_overrides", str(response))
            self.assertEqual(response["retryable"], status == "error")

    def test_exact_inventory_uses_only_current_branch_and_known_specification(self):
        scenario = deepcopy(self.package.scenarios["BASE-OUTON-01"])
        scenario["scenario_id"] = "TEST-EXACT-STOCK"
        sku = scenario["initial_state"]["orders"][0]["lines"][0]["sku"]
        row = scenario["initial_state"]["inventory"][0]
        row.update(region_spec="US", hardware_revision="SIM-V1", snapshot_at="2026-10-08T09:00:00+08:00", reserved=2)
        self.package.scenarios[scenario["scenario_id"]] = scenario
        cid = UUID(self.scene(scenario["scenario_id"])["conversation_id"])
        response = self.queries.availability(cid, item_id=sku)
        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["data"]["available_quantity"], 3)
        other = UUID(self.scene()["conversation_id"])
        self.assertEqual(self.queries.availability(other, item_id=sku)["status"], "unknown")
        scenario["scenario_id"] = "TEST-NO-STOCK"
        scenario["initial_state"]["inventory"] = []
        self.package.scenarios[scenario["scenario_id"]] = scenario
        empty = UUID(self.scene(scenario["scenario_id"])["conversation_id"])
        response = self.queries.availability(empty, item_id=sku)
        self.assertIsNone(response["data"]["available_quantity"])
        self.assertIn("inventory", response["data"]["missing_fields"])

    def test_all_statements_share_repeatable_read_snapshot(self):
        cid = UUID(self.scene()["conversation_id"])
        from globalmail_agent.application.business_read_model import read_model
        with self.engine.connect() as conn:
            branch = conn.execute(sa.select(bs.simulation_branches).where(bs.simulation_branches.c.conversation_id == cid)).mappings().one()
            row = conn.execute(sa.select(bs.inventory).where(bs.inventory.c.branch_id == branch["id"],
                bs.inventory.c.item_id == "H-CTD16-US-BK")).mappings().one()
        def interleaved(conn, conversation, workspace):
            before = conn.execute(sa.select(bs.inventory.c.on_hand).where(bs.inventory.c.id == row["id"])).scalar_one()
            with self.engine.begin() as other:
                other.execute(bs.inventory.update().where(bs.inventory.c.id == row["id"]).values(on_hand=before - 1))
            model = read_model(conn, conversation, workspace)
            self.assertEqual(next(s["on_hand"] for s in model["inventory"] if s["item_id"] == "H-CTD16-US-BK"), before)
            return model
        with patch("globalmail_agent.application.business_queries.read_model", interleaved):
            self.assertEqual(self.queries.detail(cid)["status"], "ok")
        with self.engine.connect() as conn:
            self.assertEqual(conn.execute(sa.select(bs.inventory.c.on_hand).where(bs.inventory.c.id == row["id"])).scalar_one(), 4)
