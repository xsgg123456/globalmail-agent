"""Real Qwen, real services, disposable PG; freeze checks precede all paid calls."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import time
from uuid import UUID, uuid4
from bootstrap import HERE, ROOT, BACKEND, configured_settings, isolated_database_environment, frozen_inputs, prepare, write, digest, cleanup_verified, provider_sampling, provider_tool_choice_strategy


def outbound(fixture, cid):
    import sqlalchemy as sa
    from globalmail_agent.adapters.conversation_schema import messages
    with fixture.engine.connect() as conn:
        return conn.execute(sa.select(sa.func.count()).select_from(messages).where(
            messages.c.conversation_id == cid, messages.c.sender == "simulated_agent")).scalar_one()


def ledger_snapshot(fixture, cid):
    import sqlalchemy as sa
    from globalmail_agent.adapters import business_schema as business
    with fixture.engine.connect() as conn:
        branch = conn.execute(sa.select(business.simulation_branches.c.branch_id).where(
            business.simulation_branches.c.conversation_id == cid)).scalar_one()
        return {table.name: [dict(row) for row in conn.execute(sa.select(table).where(table.c.branch_id == branch)).mappings()]
            for table in (business.operations, business.executions, business.shipments, business.return_receipts, business.inventory)}


def request_accounting(fixture, run_id):
    import sqlalchemy as sa
    from globalmail_agent.adapters.agent_schema import usage_records
    fields = ("request_key", "stage", "status", "provider_request_id", "input_tokens", "output_tokens", "reserved_tokens")
    with fixture.engine.connect() as conn:
        return [dict(row) for row in conn.execute(sa.select(*(usage_records.c[k] for k in fields)).where(
            usage_records.c.run_id == run_id).order_by(usage_records.c.created_at, usage_records.c.id)).mappings()]


def scene(fixture, package, case, *, human_owner=False):
    from globalmail_agent.application.fixture_conversations import FixtureConversations
    from globalmail_agent.domain.conversation import Command
    isolated = deepcopy(package)
    original = isolated.scenarios[case["scenario"]]
    original["initial_messages"][0]["body"] = case["body"]
    if human_owner:
        original["conversation"]["processing_owner"] = "human_review"
    # The selected scenario still contains only its original allowed initial state.
    isolated.scenarios = {case["scenario"]: original}
    return FixtureConversations(fixture.engine, fixture.store, isolated).create(
        case["scenario"], Command(expected_version=0), uuid4().hex)


def append(fixture, cid, case):
    from globalmail_agent.domain.conversation import AppendMessage
    current = fixture.conversation(cid)
    return fixture.service.append(cid, AppendMessage(expected_version=current["row_version"],
        body=case["body"], source_message_id=case["case_id"]), uuid4().hex)


def human(fixture, cid, cases):
    from globalmail_agent.domain.conversation import HumanReply
    current = fixture.conversation(cid)
    return fixture.service.human_reply(cid, HumanReply(expected_version=current["row_version"],
        expected_input_revision=current["input_revision"], body=cases["human_reply"], note=cases["human_note"]), uuid4().hex)


def execute(fixture, embedding, settings, created, case, directory, prefix=None, engineering_only=False):
    from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
    from globalmail_agent.application.run_records import RunRecords
    from globalmail_agent.adapters.model_provider import ModelProvider
    from globalmail_agent.worker.agent_runner import AgentRunner
    from recording import instrument, summarize, capture_graph_errors
    cid, run_id = UUID(created["conversation_id"]), UUID(created["run_id"])
    job = fixture.leases.claim("phase7_actual_model")
    if job is None or job["run_id"] != run_id:
        raise RuntimeError("unexpected_agent_job")
    model = ModelProvider(settings)
    time_seed = None
    if prefix and case["case_id"] == "P7-02-order-and-evidence":
        from prefix_replay import PrefixReplay, seed_ledger_time
        time_seed = seed_ledger_time(fixture, job, prefix, directory / case["case_id"])
        if prefix[3].get("prefix_kind") == "actual_under_order_search_draft":
            from draft_prefix import DraftPrefixReplay
            if engineering_only:
                raise RuntimeError("use_audit_draft_prefix_for_zero_http_draft_prefix_audit")
            model = DraftPrefixReplay(model, prefix, directory / case["case_id"])
        else:
            model = PrefixReplay(model, prefix, engineering_only=engineering_only)
    requests = instrument(model, directory / case["case_id"])
    before = outbound(fixture, cid)
    ledger_before = digest(json.dumps(ledger_snapshot(fixture, cid), sort_keys=True, default=str).encode())
    started = time.monotonic()
    restore = capture_graph_errors(directory / case["case_id"])
    try:
        output = AgentRunner(fixture.engine, fixture.store, DEFAULT_WORKSPACE_ID, model, embedding).execute(job)
    finally:
        restore()
    record = RunRecords(fixture.engine, fixture.store).get(run_id)
    elapsed = time.monotonic() - started
    write(directory / case["case_id"] / "run-record.json", {"execute": output, "record": record,
        "conversation": fixture.service.detail(cid)})
    summary = summarize(record, requests, before, outbound(fixture, cid), elapsed, case)
    summary["requests_accounting"] = request_accounting(fixture, run_id)
    summary["structural_checks"]["all_graph_requests_accounted_once"] = len(summary["requests_accounting"]) == len(requests)
    summary["new_model_http_calls"] = sum(r.get("new_http_call", True) for r in requests)
    summary["replayed_paid_responses"] = sum(r.get("response", {}).get("_eval_provenance", {}).get("kind") ==
        "replayed_paid_response" for r in requests)
    summary["new_business_quality_evidence"] = not engineering_only
    if prefix and case["case_id"] == "P7-02-order-and-evidence":
        summary["quality_scope"] = "engineering_only" if engineering_only else (
            "new_validation_and_real_commit_only"
            if prefix[3].get("prefix_kind") == "actual_under_order_search_draft" else "new_terminal_decision_and_validation_only")
        summary["time_ledger_seed"] = time_seed
        summary["origin_and_current_active_ms"] = record["usage"]["active_ms"]
        summary["structural_checks"]["ledger_retains_original_active_ms"] = record["usage"]["active_ms"] >= time_seed["seeded_active_ms"]
        summary["structural_checks"]["origin_and_current_within_120s"] = summary["origin_and_current_active_ms"] <= 120000
    ledger_after = digest(json.dumps(ledger_snapshot(fixture, cid), sort_keys=True, default=str).encode())
    summary["ledger_before_sha256"], summary["ledger_after_sha256"] = ledger_before, ledger_after
    summary["structural_checks"]["no_ledger_write"] = ledger_before == ledger_after
    return summary


def code_snapshot():
    paths = [*HERE.glob("*.py"), * (BACKEND / "src/globalmail_agent/agent").glob("*.py"),
        *(BACKEND / "src/globalmail_agent/agent/prompts").glob("*.md"),
        *(BACKEND / "src/globalmail_agent" / path for path in ("worker/agent_runner.py",
            "adapters/model_provider.py", "adapters/checkpoint_repository.py", "application/commit_outcome.py",
            "application/draft_validation.py",
            "application/event_store.py", "observability/local_records.py"))]
    return {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p.read_bytes()) for p in paths}


def main():
    from eval_options import options
    args, cases, frozen, loaded_seed, loaded_prefix, loaded_second, loaded_third = options()
    if args.check_freeze:
        print(json.dumps({"freeze": "verified", "cases": 9, "paid_calls": 0}))
        return
    if sys.prefix.lower() != str(BACKEND / ".venv").lower():
        raise RuntimeError("use_fixed_backend_venv")
    isolated_database_environment()
    # Import only after private DB environment setup, before fixture decorators evaluate.
    from knowledge_helpers import KnowledgeFixture
    from globalmail_agent.adapters.fixture_loader import FixturePackage
    fixture = KnowledgeFixture("runTest")
    settings = configured_settings()
    attempt = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    private = ROOT / "tmp/phase7-agent-eval" / attempt
    artifact = ROOT / "docs/verification/artifacts/phase7/real-model.json"
    result = {"scope": "phase7_synthetic_developer_cases_actual_qwen_and_pg", "attempt_id": attempt,
        "status": "running", "model": settings.model_name, "snapshot": frozen, "code_snapshot": code_snapshot(),
        "new_actual_sampling": provider_sampling(),
        "provider_tool_choice_strategy": provider_tool_choice_strategy(),
        "model_provider_sha256": digest((BACKEND / "src/globalmail_agent/adapters/model_provider.py").read_bytes()),
        "local_semantic_review_gate": args.semantic_gate,
        "observations": [], "limits": cases["limitations"], "original_budget": cases["budget"]}
    from prepare_review_capacity_controls import AUTHORIZED_LIMITS
    result["authorized_stage_limits"] = AUTHORIZED_LIMITS
    if loaded_seed:
        result["history_seed"] = loaded_seed[2]
        result["limits"] = [*result["limits"],
            "P7-01 was previously generated and accepted in another isolated attempt; this attempt reuses its exact paid reply as a history seed, not an independently new four-mail evaluation."]
    if loaded_prefix:
        result["prefix_replay"] = loaded_prefix[3]
        result["limits"] = [*result["limits"],
            "P7-02 reuses four paid prior responses with audited live reads; only later actual HTTP is new quality evidence. "
            "For actual_under_order_search_draft the original draft is unchanged; this attempt adds new validation "
            "and current real commit only. Later mail cases use fresh actual understanding/decisions."]
    if loaded_second:
        result["second_history_seed"] = loaded_second["metadata"]
        result["limits"] = [*result["limits"],
            "P7-02 accepted actual reply/validation also reused only as audited history; new calls start at P7-03."]
    if loaded_third:
        result["third_history_seed"] = loaded_third[3]
        result["limits"] = [*result["limits"], "P7-03 accepted actual HITL also reused only as history; new calls start at P7-04 after current human input."]
    if args.prefix_engineering_only:
        result["scope"] = "engineering_paid_prefix_plus_scripted_terminal_no_new_chat_http_not_business_quality"
    write(private / "manifest-before-paid-calls.json", result)
    try:
        fixture.setUp()
        embedding, result["knowledge_initialization"] = prepare(fixture, settings, cases)
        if args.prepare_only:
            result["status"] = "prepared_only_no_chat_calls"
        else:
            package = FixturePackage()
            actions = []
            cid = None
            if loaded_seed:
                from history_seed import initialize
                cid, result["history_seed"] = initialize(fixture, package, cases, loaded_seed, embedding, private)
            if loaded_second:
                from second_history_seed import initialize_second
                result["second_history_seed"] = initialize_second(fixture, cid, cases, loaded_second, embedding, settings, private)
            if loaded_third:
                from third_history_seed import initialize_third
                result["third_history_seed"] = initialize_third(fixture, cid, cases, loaded_third, embedding, settings, private)
            if args.group in {"closed-loop", "all"} and not (args.second_seed_engineering_only or args.third_seed_engineering_only):
                for index, case in enumerate(cases["closed_loop"]["messages"]):
                    if loaded_seed and index == 0 or loaded_second and index == 1 or loaded_third and index == 2:
                        continue
                    actions.append(("closed", index, case))
            if args.group in {"boundaries", "all"}:
                actions.extend(("boundary", 0, c) for c in cases["boundaries"] if not args.case or c["case_id"] == args.case)
            for kind, index, case in actions[:args.limit]:
                if kind == "closed":
                    if index == 0:
                        created = scene(fixture, package, {**case, "scenario": cases["closed_loop"]["scenario"]})
                        cid = UUID(created["conversation_id"])
                    else:
                        if index == 3:
                            old_count = outbound(fixture, cid)
                            human(fixture, cid, cases["closed_loop"])
                            result["human_reply_did_not_auto_send"] = old_count == outbound(fixture, cid)
                            result["human_wait_gate"] = fixture.conversation(cid)["processing_owner"]
                        created = append(fixture, cid, case)
                else:
                    if case["expect"].get("foreign_order_denied"):
                        victim = package.scenarios["BASE-OUTON-03"]
                        scene(fixture, package, {"scenario": "BASE-OUTON-03",
                            "body": victim["initial_messages"][0]["body"]}, human_owner=True)
                        result["cross_customer_fixture"] = {"scenario": "BASE-OUTON-03",
                            "order_exists_for_other_customer": True, "owner": "human_review", "model_input": False}
                    created = scene(fixture, package, case)
                observation = execute(fixture, embedding, settings, created, case, private, loaded_prefix, args.prefix_engineering_only)
                if kind == "closed" and index == 3:
                    previous_run = result["observations"][-1] if result["observations"] else {
                        "run_id": result["third_history_seed"]["seed_run_id"], "trace_id": result["third_history_seed"]["seed_trace_id"]}
                    observation["structural_checks"]["new_run_and_trace_after_human"] = (
                        observation["run_id"] != previous_run["run_id"] and bool(observation["trace_id"])
                        and observation["trace_id"] != previous_run["trace_id"])
                result["observations"].append(observation)
                write(private / "progress.json", result)
                print(json.dumps({"case": case["case_id"], "status": observation["status"],
                    "error_code": observation["error_code"], "outbound_delta": observation["outbound_delta"],
                    "requests": observation["usage"]["model_requests"]}), flush=True)
                if observation["status"] not in {"completed", "handed_off"}:
                    result["status"] = "stopped_on_engineering_failure"
                    break
                if not all(observation["structural_checks"].values()):
                    result["status"] = "stopped_on_frozen_assertion_failure"
                    break
                if args.semantic_gate:
                    from semantic_review import await_review
                    print(json.dumps({"case": case["case_id"], "awaiting_local_semantic_review": True}), flush=True)
                    observation["business_human_review"] = await_review(private / case["case_id"])
                    write(private / "progress.json", result)
                    if observation["business_human_review"]["status"] != "PASS":
                        result["status"] = "stopped_on_business_semantic_review_failure"
                        break
            else:
                result["status"] = "engineering_completed_no_new_chat_http_not_business_quality" if (
                    args.prefix_engineering_only or args.second_seed_engineering_only or args.third_seed_engineering_only) else "executed_subset_manual_business_review_pending"
    except Exception as error:
        # Do not print arbitrary exception strings: drivers may include connection information.
        result["status"] = "stopped_on_setup_or_script_error"
        result["error_code"] = getattr(error, "code", type(error).__name__)
        import traceback
        result["error_frames"] = [{"file": Path(f.filename).name, "line": f.lineno, "function": f.name}
            for f in traceback.extract_tb(error.__traceback__)][-12:]
        print(json.dumps({"status": result["status"], "error_code": result["error_code"]}), flush=True)
    finally:
        result["cleanup_checks"] = cleanup_verified(fixture)
        removed = all(result["cleanup_checks"].get(k) is True for k in (
            "callbacks_passed", "schema_removed", "temporary_objects_removed"))
        result["cleanup"] = "owned_random_schema_and_temp_object_directory_removed" if removed else "cleanup_not_verified"
        if not removed:
            result["status"] = "stopped_on_cleanup_failure"
        result["code_snapshot_after"] = code_snapshot()
        result["implementation_changed_during_attempt"] = result["code_snapshot_after"] != result["code_snapshot"]
        result["raw_directory"] = str(private.relative_to(ROOT)).replace("\\", "/")
        write(private / "result.json", result)
        # Keep earlier attempts in the safe summary, including FAIL evidence.
        previous = json.loads(artifact.read_text(encoding="utf-8")) if artifact.exists() else {"attempts": []}
        previous["attempts"].append(result)
        write(artifact, previous)
    if result["status"].startswith("stopped"):
        sys.exit(1)


if __name__ == "__main__":
    main()
