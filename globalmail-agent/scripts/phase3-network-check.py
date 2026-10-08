"""Real HTTP/SSE checks against phase3-test-server's disposable local ports."""
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
            result = client.get(path)
            assert result.status_code == 200, (path, result.status_code)
            return result.json()["data"]

        def post(path, payload):
            result = client.post(path, json=payload, headers={"Idempotency-Key": uuid4().hex})
            assert result.status_code in {200, 202}, (path, result.status_code, result.json()["msg"])
            return result.json()["data"]

        def terminal(cid):
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                value = get("/conversations/" + cid)
                if all(run["status"] not in {"queued", "running"} for run in value["runs"]):
                    return value
                time.sleep(0.05)
            raise AssertionError("protocol task did not complete")

        def read_one(cid, headers=None, after=0):
            with client.stream("GET", f"/conversations/{cid}/events?after_seq={after}", headers=headers) as stream:
                assert stream.status_code == 200
                for line in stream.iter_lines():
                    if line.startswith("data: "):
                        return json.loads(line[6:])
            raise AssertionError("no durable SSE event")

        created = post("/conversations", {"expected_version": 0,
            "sender_email": "network." + uuid4().hex + "@example.test", "body": "SSE protocol fixture."})
        cid = created["conversation_id"]
        initial = terminal(cid)
        assert len(initial["messages"]) == len(initial["runs"]) == 1
        assert initial["runs"][0]["outcome"] == "protocol_verified_model_not_connected"
        first = read_one(cid)
        second = read_one(cid, {"Last-Event-ID": str(first["seq"])})
        assert second["seq"] > first["seq"]
        assert first["conversation_id"] == second["conversation_id"] == cid
        assert "body" not in first["payload"] and "SSE protocol fixture" not in str(first)
        checks.append("real_SSE_Last_Event_ID_reconnect_preserves_order_and_scope")
        current = get("/conversations/" + cid)
        start = time.monotonic()
        with client.stream("GET", f"/conversations/{cid}/events?after_seq={current['conversation']['next_seq']}") as stream:
            for line in stream.iter_lines():
                if line == ": heartbeat":
                    assert 14 <= time.monotonic() - start < 20
                    break
            else:
                raise AssertionError("heartbeat missing")
        assert len(get("/conversations/" + cid)["runs"]) == 1
        checks.append("15_second_heartbeat_and_read_only_reconnect_no_new_task")
        assert client.get(f"/conversations/{cid}/events", headers={"Last-Event-ID": "-1"}).status_code == 422
        assert client.get(f"/conversations/{cid}/events?after_seq=999999").status_code == 409
        checks.append("invalid_and_future_event_cursors_rejected")

        example = get("/imports/example")
        example["source_conversation_id"] += "-network-" + uuid4().hex
        imported = post("/imports", example)
        historical_id = imported["conversation_id"]
        first_cut = terminal(historical_id)
        assert len(first_cut["messages"]) == 1 and "DEMO-1001" not in str(first_cut)
        post(f"/conversations/{historical_id}/takeover", {
            "expected_version": first_cut["conversation"]["row_version"]})
        review = get("/conversations/" + historical_id)
        post(f"/conversations/{historical_id}/human-replies", {
            "expected_version": review["conversation"]["row_version"],
            "expected_input_revision": review["conversation"]["input_revision"],
            "body": "NETWORK_COMPARISON_SENTINEL"})
        reviewed = get("/conversations/" + historical_id)
        assert len(reviewed["messages"]) == 1 and len(reviewed["comparisons"]) == 1
        post(f"/conversations/{historical_id}/replay/next", {
            "expected_version": reviewed["conversation"]["row_version"]})
        next_cut = terminal(historical_id)
        assert [m["sender"] for m in next_cut["messages"]] == ["customer", "historical_staff", "customer"]
        assert "NETWORK_COMPARISON_SENTINEL" not in str(next_cut["messages"] + next_cut["facts"])
        assert next_cut["conversation"]["lifecycle"] == "open"
        checks.append("real_HTTP_history_prefix_and_human_comparison_isolation")
    report = {"status": "passed", "checks": checks, "provider_calls": 0,
              "isolation": "phase3-test-server disposable PostgreSQL schema and objects"}
    (ROOT / "tmp/phase3-network-check.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()
