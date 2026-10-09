"""Reuse the accepted second actual reply through current reads and commit, never new quality."""
from copy import deepcopy
import json
from uuid import UUID
from bootstrap import ROOT, digest, write
from draft_prefix import DraftPrefixReplay, load_draft_prefix, semantic_context


def load_second_seed(attempt, case):
    if attempt != "20261008-184615-a6194636":
        raise RuntimeError("second_seed_not_authorized_accepted_origin")
    directory = ROOT / "tmp/phase7-agent-eval" / attempt / case["case_id"]
    from legacy_review import require_compatible_history_review
    require_compatible_history_review(directory)
    prefix = load_draft_prefix("20261008-182447-c623f2cd", case)
    request = json.loads((directory / "request-05.json").read_text(encoding="utf-8"))
    response = json.loads((directory / "response-05.json").read_text(encoding="utf-8"))
    record = json.loads((directory / "run-record.json").read_text(encoding="utf-8"))["record"]
    review = json.loads((directory / "semantic-review.json").read_text(encoding="utf-8"))
    result = json.loads((directory.parent / "result.json").read_text(encoding="utf-8"))
    if record["run"]["status"] != "completed" or len(record["artifacts"]) != 1 or review["status"] != "PASS":
        raise RuntimeError("second_seed_not_accepted_completed_actual_reply")
    if record["usage"]["active_ms"] != 47748 or record["usage"]["model_requests"] != 5 or record["usage"]["unknown_requests"]:
        raise RuntimeError("second_seed_source_accounting_changed")
    from globalmail_agent.agent.outcome_validation import OutcomeReview
    validation = OutcomeReview.model_validate_json(response["content"])
    if not validation.supported or not validation.language_correct or validation.unsupported_claims or (
            response["finish_reason"] != "stop" or response["calls"] or request["schema"] != OutcomeReview.model_json_schema()):
        raise RuntimeError("second_seed_not_actual_supported_review")
    for n in range(1, 5):
        replay = json.loads((directory / f"response-{n:02}.json").read_text(encoding="utf-8"))
        original = prefix[2][n - 1]
        if replay["request_id"] != original["request_id"] or replay["usage"] != original["usage"] or (
                replay["_eval_provenance"]["origin_attempt_id"] != prefix[3]["origin_attempt_id"]):
            raise RuntimeError("second_seed_original_four_usage_provenance_changed")
    files = [directory / f"{kind}-{n:02}.json" for n in range(1, 6) for kind in ("request", "response")]
    files += [directory / "run-record.json", directory / "semantic-review.json", directory.parent / "result.json"]
    metadata = {**prefix[3], "origin": "accepted_actual_second_reply_replayed_only_for_history_initialization",
        "origin_attempt_id": attempt, "origin_run_id": str(record["run"]["id"]), "origin_active_ms": 47748,
        "source_four_generation_origin": "20261008-182447-c623f2cd",
        "source_fifth_actual_validation_origin": attempt, "replayed_requests": 5,
        "time_accounting": "guarded_original_accepted_second_cycle_active_ms_plus_current_engineering_elapsed",
        "source_sampling": result["new_actual_sampling"], "original_usage": record["usage"],
        "accepted_reply_sha256": digest(record["artifacts"][0]["body"].encode()),
        "new_model_http_calls": 0, "new_business_quality_claim": False,
        "source_code_snapshot": result["code_snapshot"],
        "second_source_files_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p.read_bytes()) for p in files}}
    return {"prefix": prefix, "request": request, "response": response, "metadata": metadata}


def initialize_second(fixture, cid, cases, loaded, embedding, settings, private):
    from globalmail_agent.adapters.model_provider import ModelProvider
    from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
    from globalmail_agent.application.run_records import RunRecords
    from globalmail_agent.worker.agent_runner import AgentRunner
    from prefix_replay import seed_ledger_time
    from run_eval import append, outbound
    from recording import instrument, capture_graph_errors
    prefix = loaded["prefix"]
    origin_checker = DraftPrefixReplay(ModelProvider(settings), prefix, private / "second-seed-source-audit")
    source_payload = json.loads(loaded["request"]["messages"][1]["content"])
    origin_checker.compare_context(source_payload["context"])
    origin_checker.compare_observations(source_payload["observations"])
    source_check = origin_checker.verify_validation(loaded["request"]["messages"], current_prompts=False)
    directory = ROOT / "tmp/phase7-agent-eval" / loaded["metadata"]["origin_attempt_id"] / "P7-02-order-and-evidence"
    for n, old in enumerate(prefix[2], 1):
        prior = json.loads((directory / f"response-{n:02}.json").read_text(encoding="utf-8"))
        if old["content"] and origin_checker.map_ids(json.loads(old["content"])) != json.loads(prior["content"]):
            raise RuntimeError("second_seed_source_understanding_payload_changed")
        if len(old["calls"]) != len(prior["calls"]):
            raise RuntimeError("second_seed_source_calls_changed")
        for original_call, prior_call in zip(old["calls"], prior["calls"]):
            if original_call["id"] != prior_call["id"] or original_call["name"] != prior_call["name"] or (
                    origin_checker.map_ids(json.loads(original_call["arguments"])) != json.loads(prior_call["arguments"])):
                raise RuntimeError("second_seed_source_decision_payload_changed")
    source_check["all_four_generation_payloads_equal_after_listed_source_id_mapping"] = True
    write(private / "second-seed-source-data-audit.json", source_check)
    created = append(fixture, cid, cases["closed_loop"]["messages"][1])
    job = fixture.leases.claim("phase7_accepted_second_history_seed")
    if job is None or job["run_id"] != UUID(created["run_id"]):
        raise RuntimeError("second_seed_unexpected_job")
    accounting = (*prefix[:3], loaded["metadata"])
    time_seed = seed_ledger_time(fixture, job, accounting, private / "second-seed")

    class AcceptedSecondReplay(DraftPrefixReplay):
        def request(self, messages, *, schema=None, tools=None, timeout=30):
            if self.index < 4:
                return super().request(messages, schema=schema, tools=tools, timeout=timeout)
            if self.index != 4 or tools is not None:
                raise RuntimeError("second_seed_requested_unpaid_new_response")
            current_check = self.verify_validation(messages)
            composed = {source_id: self.ids[old_id] for old_id, source_id in origin_checker.ids.items()}
            def source_ids(value):
                if isinstance(value, str):
                    return composed.get(value, value)
                if isinstance(value, list):
                    return [source_ids(v) for v in value]
                if isinstance(value, dict):
                    return {k: source_ids(v) for k, v in value.items()}
                return value
            expected = source_ids(source_payload)
            expected["context"] = source_ids(semantic_context(source_payload["context"]))
            expected["observations"] = self.current_observations
            current = json.loads(messages[1]["content"])
            current["context"] = semantic_context(current["context"])
            if expected != current:
                raise RuntimeError("second_seed_accepted_actual_validation_data_changed")
            write(private / "second-seed-current-validation-audit.json", current_check)
            response = deepcopy(loaded["response"])
            response["_eval_provenance"] = {"kind": "already_paid_actual_validation_replayed_only_for_history_seed",
                "origin_attempt_id": loaded["metadata"]["origin_attempt_id"], "origin_request_index": 5,
                "origin_provider_request_id": response["request_id"], "new_http_call": False,
                "sampling": loaded["metadata"]["source_sampling"]}
            self.index += 1
            self.audit()
            return response

    model = AcceptedSecondReplay(ModelProvider(settings), prefix, private / "second-seed")
    requests = instrument(model, private / "second-seed")
    before = outbound(fixture, cid)
    restore = capture_graph_errors(private / "second-seed")
    try:
        output = AgentRunner(fixture.engine, fixture.store, DEFAULT_WORKSPACE_ID, model, embedding).execute(job)
    finally:
        restore()
    record = RunRecords(fixture.engine, fixture.store).get(UUID(created["run_id"]))
    write(private / "history-second-seed-record.json", {"execute": output, "record": record})
    if record["run"]["status"] != "completed" or outbound(fixture, cid) - before != 1 or model.index != 5:
        raise RuntimeError("second_seed_current_graph_commit_failed")
    if digest(record["artifacts"][0]["body"].encode()) != loaded["metadata"]["accepted_reply_sha256"] or (
            record["usage"]["model_requests"] != 5 or record["usage"]["tool_calls"] != 3 or
            record["usage"]["reserved_tokens"] != loaded["metadata"]["original_usage"]["reserved_tokens"] or
            not 47748 <= record["usage"]["active_ms"] <= 120000 or model.new_http_calls):
        raise RuntimeError("second_seed_reply_or_ledger_accounting_changed")
    return {**loaded["metadata"], "status": "completed_history_initialization_not_new_quality",
        "seed_run_id": str(record["run"]["id"]), "seed_trace_id": record["trace_id"],
        "current_usage": record["usage"], "time_ledger_seed": time_seed,
        "all_five_original_responses_accounted": len(requests) == 5, "new_model_http_calls": model.new_http_calls}
