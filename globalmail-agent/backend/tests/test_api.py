import tempfile
import unittest
from pathlib import Path

from fastapi import Request
from fastapi.testclient import TestClient

from globalmail_agent.main import create_app
from globalmail_agent.settings import Settings


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.settings = Settings(object_root=Path(self.temp.name), model_api_key="SECRET_MARKER",
                                 model_name="qwen3.7-plus", model_base_url="http://example.invalid")
        self.app = create_app(self.settings)
        self.client = TestClient(self.app, base_url="http://127.0.0.1:18080")

    def tearDown(self):
        self.client.close()
        self.temp.cleanup()

    def test_live_and_safe_runtime(self):
        for path in ("health/live", "runtime-config"):
            result = self.client.get("/api/v1/" + path)
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.json()["code"], 200)
            self.assertEqual(result.headers["x-request-id"], result.json()["request_id"])
            self.assertNotIn("SECRET_MARKER", result.text)
        self.assertTrue(result.json()["data"]["model_configured"])
        self.assertEqual(result.json()["data"]["phase"], 7)
        self.assertEqual(result.json()["data"]["features"],
                         {"conversations": True, "business_queries": True,
                          "knowledge": True, "agent": True})

    def test_readiness_degraded_without_database(self):
        result = self.client.get("/api/v1/health/ready")
        self.assertEqual(result.status_code, 503)
        self.assertEqual(result.json()["data"]["database"], "unavailable")
        self.assertEqual(result.json()["data"]["object_store"], "ready")

    def test_bad_hosts_and_origins_rejected(self):
        for host in ("evil.example", "localhost.evil", "localhost@evil.example", "127.0.0.1:bad"):
            self.assertEqual(self.client.get("/api/v1/health/live", headers={"Host": host}).status_code, 400)
        for origin in ("https://evil.example", "null", "http://127.0.0.1:9999"):
            self.assertEqual(self.client.get("/api/v1/health/live", headers={"Origin": origin}).status_code, 403)

    def test_preflight_and_write_protection(self):
        headers = {"Origin": "http://127.0.0.1:15173"}
        result = self.client.options("/api/v1/health/live", headers=headers)
        self.assertEqual(result.status_code, 200)
        self.assertIn("request_id", result.json())
        self.assertEqual(result.headers["access-control-allow-origin"], headers["Origin"])
        self.assertEqual(self.client.post("/api/v1/health/live", json={}).status_code, 403)
        self.assertEqual(self.client.post("/api/v1/health/live", headers=headers, content="x").status_code, 415)

    def test_validation_and_exceptions_are_sanitized(self):
        @self.app.get("/test/{number}")
        def typed(number: int):
            return number

        @self.app.get("/failure")
        def failure():
            raise RuntimeError("SECRET_MARKER")

        for path, expected in (("/test/SECRET_MARKER", 422), ("/failure", 500), ("/missing", 404)):
            result = self.client.get(path)
            self.assertEqual(result.status_code, expected)
            self.assertNotIn("SECRET_MARKER", result.text)
            self.assertTrue(result.json()["request_id"])

    def test_non_local_config_rejected(self):
        with self.assertRaises(ValueError):
            Settings(allowed_origins=("http://evil.example",))

