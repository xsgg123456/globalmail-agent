"""Accepted actual third-mail HITL as history; never reuse the failed fourth reply."""
import json
from uuid import UUID
from bootstrap import ROOT, digest, write
from draft_prefix import DraftPrefixReplay


def load_third_seed(attempt, case):
    if attempt != "20261008-191114-7c80c70b" or case["case_id"] != "P7-03-attempts-failed":
        raise RuntimeError("third_seed_not_authorized_accepted_handoff_origin")
    directory = ROOT / "tmp/phase7-agent-eval" / attempt / case["case_id"]
    requests = [json.loads((directory / f"request-{n:02}.json").read_text(encoding="utf-8")) for n in range(1, 5)]
    responses = [json.loads((directory / f"response-{n:02}.json").read_text(encoding="utf-8")) for n in range(1, 5)]
    old = json.loads(requests[0]["messages"][1]["content"])
    record = json.loads((directory / "run-record.json").read_text(encoding="utf-8"))["record"]
    review = json.loads((directory / "semantic-review.json").read_text(encoding="utf-8"))
    result = json.loads((directory.parent / "result.json").read_text(encoding="utf-8"))
    names = [[], ["get_order_snapshot"], ["search_reference"], ["request_human_review"]]
    if old["messages"][-1]["body"] != case["body"] or old["human_notes"] or len(old["messages"]) != 5:
        raise RuntimeError("third_seed_source_includes_nonfrozen_or_future_input")
    if record["run"]["status"] != "handed_off" or review["status"] != "PASS" or len(record["artifacts"]) != 1 or (
            record["artifacts"][0]["outcome"] != "handoff" or record["usage"]["active_ms"] != 41797):
        raise RuntimeError("third_seed_not_accepted_actual_handoff")
    if [list(c["name"] for c in r["calls"]) for r in responses] != names or (
            record["usage"]["model_requests"] != 4 or record["usage"]["unknown_requests"]):
        raise RuntimeError("third_seed_actual_sequence_or_usage_changed")
    files = [directory / f"{kind}-{n:02}.json" for n in range(1, 5)
        for kind in ("request", "response", "provider-payload")]
    files += [directory / "run-record.json", directory / "semantic-review.json", directory.parent / "result.json",
        directory.parent / "manifest-before-paid-calls.json"]
    metadata = {"origin": "accepted_actual_third_handoff_replayed_only_for_history_initialization",
        "origin_attempt_id": attempt, "origin_run_id": str(record["run"]["id"]),
        "prefix_kind": "actual_under_order_search_handoff", "replayed_requests": 4,
        "origin_sampling": result["new_actual_sampling"], "origin_active_ms": 41797,
        "time_accounting": "guarded_entire_original_accepted_handoff_cycle_base_plus_current_engineering_elapsed",
        "original_usage": record["usage"], "original_four_usage": [r["usage"] for r in responses],
        "source_actual_tool_choices": [json.loads((directory / f"provider-payload-{n:02}.json").read_text(
            encoding="utf-8")).get("tool_choice") for n in range(1, 5)],
        "accepted_unsent_draft_sha256": digest(record["artifacts"][0]["body"].encode()),
        "accepted_core_limits": review["limitations"], "source_code_snapshot": result["code_snapshot"],
        "old_responses_are_new_quality_evidence": False, "new_model_http_calls": 0,
        "failed_fourth_case_reused": False, "future_human_and_fourth_input_loaded": False,
        "trusted_original_file_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p.read_bytes()) for p in files}}
    return old, requests, responses, metadata


def initialize_third(fixture, cid, cases, loaded, embedding, settings, private):
    from globalmail_agent.adapters.model_provider import ModelProvider
    from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
    from globalmail_agent.application.run_records import RunRecords
    from globalmail_agent.worker.agent_runner import AgentRunner
    from prefix_replay import seed_ledger_time
    from run_eval import append, outbound, ledger_snapshot
    from recording import instrument, capture_graph_errors
    before_ledger = digest(json.dumps(ledger_snapshot(fixture, cid), sort_keys=True, default=str).encode())
    created = append(fixture, cid, cases["closed_loop"]["messages"][2])
    job = fixture.leases.claim("phase7_accepted_third_handoff_history_seed")
    if job is None or job["run_id"] != UUID(created["run_id"]):
        raise RuntimeError("third_seed_unexpected_job")
    time_seed = seed_ledger_time(fixture, job, loaded, private / "third-seed")
    class AcceptedThirdReplay(DraftPrefixReplay):
        def request(self, messages, *, schema=None, tools=None, timeout=30):
            if self.index >= 4:
                raise RuntimeError("third_seed_requested_unpaid_new_response")
            return super().request(messages, schema=schema, tools=tools, timeout=timeout)
    model = AcceptedThirdReplay(ModelProvider(settings), loaded, private / "third-seed")
    traffic = instrument(model, private / "third-seed")
    before_out = outbound(fixture, cid)
    restore = capture_graph_errors(private / "third-seed")
    try:
        output = AgentRunner(fixture.engine, fixture.store, DEFAULT_WORKSPACE_ID, model, embedding).execute(job)
    finally:
        restore()
    record = RunRecords(fixture.engine, fixture.store).get(UUID(created["run_id"]))
    write(private / "history-third-seed-record.json", {"execute": output, "record": record,
        "conversation": fixture.service.detail(cid)})
    if record["run"]["status"] != "handed_off":
        raise RuntimeError("third_seed_current_real_graph_did_not_handoff")
    source = ROOT / "tmp/phase7-agent-eval" / loaded[3]["origin_attempt_id"] / "P7-03-attempts-failed/run-record.json"
    if digest(source.read_bytes()) != loaded[3]["trusted_original_file_sha256"][str(source.relative_to(ROOT)).replace("\\", "/")]:
        raise RuntimeError("third_seed_trusted_source_record_changed_after_freeze")
    prior = json.loads(source.read_text(encoding="utf-8"))
    actual_detail = json.loads(json.dumps(fixture.service.detail(cid), default=str))
    review_fields = ("status", "version", "input_revision", "reason", "visible_message_seq", "as_of", "draft", "note", "reply")
    artifact_fields = ("outcome", "language", "citation_ids", "claims", "body")
    domain_checks = {
        "complete_understanding_initial_and_revisions_unchanged": model.map_ids(prior["record"]["understanding"]) == record["understanding"],
        "complete_handoff_summary_gaps_and_unsent_draft_unchanged": all(
            model.map_ids(prior["conversation"]["review"][key]) == actual_detail["review"][key] for key in review_fields),
        "complete_artifact_claims_citations_language_body_unchanged": all(
            model.map_ids(prior["record"]["artifacts"][0][key]) == record["artifacts"][0][key] for key in artifact_fields)}
    write(private / "third-seed-persisted-domain-audit.json", {"checks": domain_checks,
        "identity_mapping": model.ids, "review_fields_compared": review_fields, "artifact_fields_compared": artifact_fields,
        "source_record_path": str(source.relative_to(ROOT)).replace("\\", "/"),
        "current_record_path": str((private / "history-third-seed-record.json").relative_to(ROOT)).replace("\\", "/"),
        "all_other_identity_object_and_storage_timestamps_are_engineering_metadata": True})
    after_ledger = digest(json.dumps(ledger_snapshot(fixture, cid), sort_keys=True, default=str).encode())
    checks = {**domain_checks, "current_real_handoff": record["run"]["status"] == "handed_off",
        "zero_outbound": outbound(fixture, cid) == before_out, "no_new_chat_http": model.new_http_calls == 0,
        "four_actual_original_responses_accounted": model.index == len(traffic) == record["usage"]["model_requests"] == 4,
        "current_actual_gateway_reads_and_terminal": record["usage"]["tool_calls"] == 3,
        "original_usage_known_and_retained": record["usage"]["unknown_requests"] == 0 and
            record["usage"]["reserved_tokens"] == loaded[3]["original_usage"]["reserved_tokens"],
        "original_activity_retained_within_budget": 41797 <= record["usage"]["active_ms"] <= 120000,
        "no_business_ledger_write": before_ledger == after_ledger,
        "accepted_unsent_draft_unchanged": len(record["artifacts"]) == 1 and
            digest(record["artifacts"][0]["body"].encode()) == loaded[3]["accepted_unsent_draft_sha256"]}
    if not all(checks.values()):
        write(private / "third-seed-failed-checks.json", checks)
        raise RuntimeError("third_seed_current_handoff_or_source_accounting_failed")
    return {**loaded[3], "status": "accepted_handoff_history_initialization_not_new_quality",
        "seed_run_id": str(record["run"]["id"]), "seed_trace_id": record["trace_id"],
        "current_usage": record["usage"], "time_ledger_seed": time_seed, "checks": checks}
