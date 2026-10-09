"""0 new chat HTTP: replay four paid responses and stop before validation reserve."""
import json
import time
from uuid import UUID, uuid4
from bootstrap import ROOT, BACKEND, configured_settings, isolated_database_environment, frozen_inputs, prepare, write, digest, cleanup_verified


def main():
    cases, frozen = frozen_inputs()
    from history_seed import load_seed, initialize
    seed = load_seed("20261008-172034-8484f882", cases["closed_loop"]["messages"][0])
    from draft_prefix import load_draft_prefix, DraftPrefixReplay
    loaded = load_draft_prefix("20261008-182447-c623f2cd", cases["closed_loop"]["messages"][1])
    isolated_database_environment()
    from knowledge_helpers import KnowledgeFixture
    from globalmail_agent.adapters.fixture_loader import FixturePackage
    from globalmail_agent.adapters.model_provider import ModelProvider
    from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
    from globalmail_agent.application.run_records import RunRecords
    from globalmail_agent.worker.agent_runner import AgentRunner
    from globalmail_agent.agent.graph import AgentGraph
    from globalmail_agent.agent.budget import input_estimate
    from prefix_replay import seed_ledger_time
    from recording import instrument, capture_graph_errors
    from run_eval import append, code_snapshot, ledger_snapshot, outbound, request_accounting
    attempt = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    private = ROOT / "tmp/phase7-agent-eval" / attempt
    fixture = KnowledgeFixture("runTest")
    result = {"attempt_id": attempt, "scope": "paid_actual_draft_prefix_engineering_audit_no_new_chat_http_not_business_quality",
        "status": "running", "snapshot": frozen, "code_snapshot": code_snapshot(),
        "prefix_replay": loaded[3], "new_model_http_calls": 0, "business_commit": False, "business_outbound": 0,
        "failure_response_05_reused": False, "expected_engineering_stop": "eval_preflight_completed_no_model_http"}
    write(private / "manifest-before-engineering-replay.json", result)
    original = AgentGraph.request
    try:
        fixture.setUp()
        settings = configured_settings()
        embedding, result["knowledge_initialization"] = prepare(fixture, settings, cases)
        package = FixturePackage()
        cid, result["history_seed"] = initialize(fixture, package, cases, seed, embedding, private)
        created = append(fixture, cid, cases["closed_loop"]["messages"][1])
        job = fixture.leases.claim("phase7_draft_prefix_engineering_audit")
        if job["run_id"] != UUID(created["run_id"]):
            raise RuntimeError("draft_prefix_unexpected_job")
        result["time_ledger_seed"] = seed_ledger_time(fixture, job, loaded, private)
        model = DraftPrefixReplay(ModelProvider(settings), loaded, private)
        traffic = instrument(model, private / "P7-02-order-and-evidence")
        before = digest(json.dumps(ledger_snapshot(fixture, cid), sort_keys=True, default=str).encode())
        count = outbound(fixture, cid)

        def intercept(graph, messages, stage, *, schema=None, tools=None):
            if stage != "validation":
                return original(graph, messages, stage, schema=schema, tools=tools)
            result["validation_data_audit"] = model.verify_validation(messages)
            estimate = input_estimate(messages, [schema])
            if estimate > 16000 or tools is not None or model.index != 4:
                raise RuntimeError("draft_prefix_preflight_not_within_original_budget")
            result["next_validation_input_proxy"] = estimate
            write(private / "next-validation-request-before-reserve.json", {
                "messages": messages, "schema": schema, "tools": tools, "timeout": 30})
            raise ServiceError("eval_preflight_completed_no_model_http", 503)

        AgentGraph.request = intercept
        restore = capture_graph_errors(private)
        try:
            output = AgentRunner(fixture.engine, fixture.store, DEFAULT_WORKSPACE_ID, model, embedding).execute(job)
        finally:
            restore()
            AgentGraph.request = original
        record = RunRecords(fixture.engine, fixture.store).get(UUID(created["run_id"]))
        write(private / "run-record.json", {"execute": output, "record": record})
        result["usage"] = record["usage"]
        result["requests_accounting"] = request_accounting(fixture, UUID(created["run_id"]))
        result["business_outbound"] = outbound(fixture, cid) - count
        result["new_model_http_calls"] = model.new_http_calls
        after = digest(json.dumps(ledger_snapshot(fixture, cid), sort_keys=True, default=str).encode())
        usage_total = sum(r["usage"]["prompt_tokens"] + r["usage"]["completion_tokens"] for r in loaded[2])
        result["checks"] = {
            "actual_graph_built_current_full_validation_request": bool(result.get("validation_data_audit")),
            "no_new_chat_http": model.new_http_calls == 0,
            "no_business_commit_or_outbound": result["business_outbound"] == 0 and not record["artifacts"],
            "intentional_stop_before_validation_reserve": record["run"]["error_code"] == result["expected_engineering_stop"],
            "four_original_requests_accounted": record["usage"]["model_requests"] == len(traffic) == 4,
            "four_original_usage_accounted": record["usage"]["reserved_tokens"] == usage_total,
            "three_actual_gateway_tools": record["usage"]["tool_calls"] == 3,
            "whole_original_time_retained_within_120s": 37515 <= record["usage"]["active_ms"] <= 120000,
            "no_business_ledger_write": before == after,
            "next_request_within_16k": result.get("next_validation_input_proxy", 16001) <= 16000}
        result["status"] = "PASS_engineering_audit_only" if all(result["checks"].values()) else "FAIL_engineering_audit"
    except Exception as error:
        result["status"] = "FAIL_engineering_audit"
        result["error_code"] = getattr(error, "code", type(error).__name__)
        import traceback
        from pathlib import Path
        result["error_frames"] = [{"file": Path(f.filename).name, "line": f.lineno, "function": f.name}
            for f in traceback.extract_tb(error.__traceback__)][-12:]
    finally:
        AgentGraph.request = original
        result["cleanup_checks"] = cleanup_verified(fixture)
        result["code_snapshot_after"] = code_snapshot()
        result["implementation_changed_during_attempt"] = result["code_snapshot_after"] != result["code_snapshot"]
        write(private / "result.json", result)
        artifact = ROOT / "docs/verification/artifacts/phase7/real-model.json"
        previous = json.loads(artifact.read_text(encoding="utf-8"))
        previous.setdefault("prefix_engineering_audits", []).append(result)
        write(artifact, previous)
    print(json.dumps({"attempt": attempt, "status": result["status"], "error_code": result.get("error_code"),
        "checks": result.get("checks"), "next_input_proxy": result.get("next_validation_input_proxy"),
        "new_http": result["new_model_http_calls"]}))
    if result["status"] != "PASS_engineering_audit_only":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
