"""Read real HTTP/SSE from the isolated Phase 7 manual-agent server, with no model calls."""
import json
from pathlib import Path
import time
from uuid import uuid4
import httpx

API = "http://127.0.0.1:18181/api/v1"
ORIGIN = "http://127.0.0.1:15174"
ROOT = Path(__file__).resolve().parents[2]


def main():
    checks = []
    with httpx.Client(base_url=API, headers={"Origin": ORIGIN}, timeout=20, trust_env=False) as client:
        def get(path):
            response = client.get(path)
            assert response.status_code == 200, (path, response.status_code)
            return response.json()["data"]

        def post(path, payload):
            response = client.post(path, json=payload, headers={"Idempotency-Key": uuid4().hex})
            assert response.status_code in {200, 202}, (path, response.status_code, response.json()["msg"])
            return response.json()["data"]

        def event(cid, after=0, headers=None):
            with client.stream("GET", f"/conversations/{cid}/events?after_seq={after}", headers=headers) as stream:
                assert stream.status_code == 200
                for line in stream.iter_lines():
                    if line.startswith("data: "):
                        return json.loads(line[6:])
            raise AssertionError("No durable SSE event")

        runtime = get("/runtime-config")
        assert runtime["phase"] == 7 and runtime["features"]["agent"]
        assert not runtime["model_configured"]  # This disposable server cannot call Qwen.
        created = post("/conversations", {"expected_version": 0,
            "sender_email": f"phase7.sse.{uuid4().hex}@example.test", "body": "SSE_BODY_MUST_NOT_LEAK"})
        cid, run_id = created["conversation_id"], created["run_id"]
        initial = get(f"/conversations/{cid}")
        post(f"/runs/{run_id}/stop", {"expected_version": initial["conversation"]["row_version"]})
        detail = get(f"/conversations/{cid}")
        assert detail["runs"][0]["status"] == "stopped"
        first = event(cid)
        second = event(cid, headers={"Last-Event-ID": str(first["seq"])})
        assert first["seq"] < second["seq"]
        assert first["conversation_id"] == second["conversation_id"] == cid
        assert "body" not in first["payload"] and "SSE_BODY_MUST_NOT_LEAK" not in str(first) + str(second)
        checks.append("SSE_reconnect_monotonic_scope_safe_payload")
        start = time.monotonic()
        with client.stream("GET", f"/conversations/{cid}/events?after_seq={detail['conversation']['next_seq']}") as stream:
            for line in stream.iter_lines():
                if line == ": heartbeat":
                    elapsed = time.monotonic() - start
                    assert 14 <= elapsed < 20
                    break
            else:
                raise AssertionError("Heartbeat missing")
        after = get(f"/conversations/{cid}")
        assert len(after["runs"]) == len(detail["runs"]) == 1
        assert len(after["messages"]) == 1
        assert client.get(f"/conversations/{cid}/events", headers={"Last-Event-ID": "-1"}).status_code == 422
        assert client.get(f"/conversations/{cid}/events?after_seq=999999").status_code == 409
        checks += ["15_second_heartbeat_reconnect_no_new_run_or_mail", "invalid_and_future_cursor_rejected"]
        assert get(f"/runs/{run_id}")["usage"]["model_requests"] == 0
    report = {"status": "passed", "checks": checks, "provider_calls": 0,
        "heartbeat_seconds": round(elapsed, 3), "isolation": "random Phase7 PostgreSQL schema and temporary objects"}
    output = ROOT / "docs/verification/artifacts/phase7/network-check.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
