"""HTTP business boundaries against disposable PostgreSQL; no model or production writes."""
import json
import tempfile
import unittest
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from globalmail_agent.adapters.schema import metadata
from globalmail_agent.main import create_app
from globalmail_agent.settings import Settings
from test_protocol import ProtocolFixture


class BusinessUnavailableApiTests(unittest.TestCase):
    def test_unconfigured_database_is_not_reported_as_no_order(self):
        with tempfile.TemporaryDirectory(prefix="globalmail_business_api_") as root:
            with TestClient(create_app(Settings(object_root=Path(root)), start_worker=False),
                            base_url="http://127.0.0.1:18080") as client:
                cid = str(uuid4())
                queries = (f"/conversations/{cid}/business",
                           f"/conversations/{cid}/availability?order_line_id=DEMO-L1&item_id=DEMO-SKU")
                for path in queries:
                    result = client.get("/api/v1" + path)
                    self.assertEqual(result.status_code, 503, result.text)
                    self.assertEqual(result.json()["msg"], "database_unavailable")
                    self.assertNotIn("postgresql", result.text)
                result = client.post(f"/api/v1/conversations/{cid}/eligibility",
                    json={"action": "refund", "quantity": 1},
                    headers={"Origin": "http://127.0.0.1:15173"})
                self.assertEqual(result.status_code, 503, result.text)


class BusinessApiTests(ProtocolFixture):
    def setUp(self):
        super().setUp()
        self.client = TestClient(create_app(Settings(object_root=Path(self.temp.name)),
            engine=self.engine, start_worker=False), base_url="http://127.0.0.1:18080")
        self.addCleanup(self.client.close)
        self.headers = {"Origin": "http://127.0.0.1:15173"}

    def post(self, path, body, key=None):
        return self.client.post("/api/v1" + path, json=body,
            headers={**self.headers, "Idempotency-Key": key or uuid4().hex})

    def scene(self, scenario="BASE-OUTON-07"):
        result = self.post(f"/business/scenarios/{scenario}/conversations", {"expected_version": 0})
        self.assertEqual(result.status_code, 202, result.text)
        return result.json()["data"]["conversation_id"]

    def query(self, cid, **params):
        result = self.client.get(f"/api/v1/conversations/{cid}/business", params=params)
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()["data"]

    def counts(self):
        with self.engine.connect() as conn:
            return {name: conn.execute(select(func.count()).select_from(metadata.tables[name])).scalar_one()
                for name in ("messages", "jobs", "domain_events", "operations", "executions", "inventory")}

    def test_catalogue_and_current_details_exclude_controller_and_answers(self):
        catalog = self.client.get("/api/v1/business/scenarios")
        self.assertEqual(catalog.status_code, 200)
        self.assertEqual(len(catalog.json()["data"]["items"]), 72)
        cid = self.scene("SCN-025")
        details = self.query(cid)
        self.assertEqual(details["status"], "ok")
        self.assertEqual(len(details["data"]["shipments"]), 1)
        self.assertEqual(details["data"]["shipments"][0]["status"], "in_transit")
        content = json.dumps([catalog.json(), details])
        for forbidden in ("controller_events_ref", "reference_reply", "tool_overrides",
                          "expected_action", "authoring/support-journeys", "evaluation/"):
            self.assertNotIn(forbidden, content)

    def test_scene_idempotency_and_scope_cannot_be_supplied_by_browser(self):
        key = uuid4().hex
        path = "/business/scenarios/BASE-OUTON-07/conversations"
        first = self.post(path, {"expected_version": 0}, key)
        second = self.post(path, {"expected_version": 0}, key)
        self.assertEqual(first.status_code, 202, first.text)
        self.assertEqual(first.json()["data"], second.json()["data"])
        conflict = self.post("/business/scenarios/BASE-BELEEV-07/conversations", {"expected_version": 0}, key)
        self.assertEqual(conflict.status_code, 409)
        for field in ("customer_id", "branch_id", "as_of", "policy_version", "evidence"):
            bad = self.post(path, {"expected_version": 0, field: "untrusted"})
            self.assertEqual(bad.status_code, 422)
        cid = first.json()["data"]["conversation_id"]
        duplicate = self.scene()
        one = self.client.get(f"/api/v1/conversations/{cid}").json()["data"]["conversation"]
        two = self.client.get(f"/api/v1/conversations/{duplicate}").json()["data"]["conversation"]
        self.assertNotEqual(one["id"], two["id"])

    def test_reads_and_eligibility_do_not_execute_or_enqueue(self):
        cid = self.scene()
        detail = self.query(cid)
        line = detail["data"]["orders"][0]["lines"][0]["line_id"]
        before = self.counts()
        for _ in range(2):
            self.query(cid, order_line_id=line)
            preview = self.post(f"/conversations/{cid}/eligibility",
                {"action": "spare_part", "order_line_id": line, "quantity": 1,
                 "item_id": "SIM-OUTON-01-REMOTE-01"})
            self.assertEqual(preview.status_code, 200, preview.text)
            verdict = preview.json()["data"]["data"]
            self.assertFalse(verdict["authorized"])
            self.assertEqual(verdict["publication_status"], "unpublished")
        self.assertEqual(before, self.counts())

    def test_cross_scope_and_manual_lookup_cannot_bind_foreign_order(self):
        cid = self.scene()
        other = self.scene("BASE-BELEEV-07")
        foreign = self.query(other)["data"]["orders"][0]
        denied = self.query(cid, order_number=foreign["display_order_number"])
        self.assertIn(denied["status"], ("empty", "denied"))
        self.assertEqual((denied["data"] or {}).get("orders", []), [])
        line = foreign["lines"][0]["line_id"]
        result = self.post(f"/conversations/{cid}/eligibility",
            {"action": "refund", "order_line_id": line, "quantity": 1})
        self.assertEqual(result.status_code, 200, result.text)
        self.assertIn(result.json()["data"]["status"], ("empty", "denied", "needs_input"))
        manual = self.post("/conversations", {"expected_version": 0,
            "sender_email": "manual-api@example.test", "body": foreign["display_order_number"]})
        self.assertEqual(manual.status_code, 202)
        empty = self.query(manual.json()["data"]["conversation_id"],
            order_number=foreign["display_order_number"])
        self.assertEqual((empty["data"] or {}).get("orders", []), [])

    def test_money_quantity_and_evidence_request_inputs_are_strict(self):
        cid = self.scene()
        path = f"/conversations/{cid}/eligibility"
        base = {"action": "refund", "quantity": 1}
        for updates in ({"quantity": True}, {"quantity": 1.2}, {"quantity": 0},
                        {"amount_minor": 99.5}, {"amount_minor": True}, {"amount_minor": -1},
                        {"evidence": [{"kind": "tool_fact"}]}, {"address_confirmed": True},
                        {"consent": True}, {"policy_version": "2.0.0"}):
            with self.subTest(updates=updates):
                result = self.post(path, {**base, **updates})
                self.assertEqual(result.status_code, 422, result.text)
        for query in ({"order_number": "x" * 101}, {"customer_id": "forged"},
                      {"as_of": "2099-01-01T00:00:00Z"}, {"branch_id": str(uuid4())}):
            result = self.client.get(f"/api/v1/conversations/{cid}/business", params=query)
            self.assertEqual(result.status_code, 422, result.text)


if __name__ == "__main__":
    unittest.main()
