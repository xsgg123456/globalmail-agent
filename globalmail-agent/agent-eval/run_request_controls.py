"""Authorized actual request-coverage/product reviews; negative gate precedes positive."""
import argparse
import json
import sys
import time
from uuid import uuid4
from bootstrap import ROOT, BACKEND, configured_settings, digest, json_bytes, provider_sampling, write
from recording import instrument


def known_usage(response):
    usage = response.get("usage") if response else None
    return bool(usage) and all(type(usage.get(k)) is int and usage[k] >= 0
        for k in ("prompt_tokens", "completion_tokens"))


def effective_control_request(request, active_ms):
    timeout = min(request["timeout"], (120000 - active_ms) / 1000)
    if timeout <= 0:
        raise RuntimeError("cycle_time_exhausted_no_HTTP")
    return dict(request, timeout=timeout)


def validate_negative_history(result, gate, response_path):
    observations = result.get("observations", [])
    if result.get("status") != "awaiting_negative_fulltext_review" or len(observations) != 1:
        raise RuntimeError("negative_not_semantically_accepted_no_positive_HTTP")
    observation = observations[0]
    if observation.get("status") != "PASS" or observation.get("actual_supported") is not False or (
            not known_usage(observation) or observation.get("checks", {}).get("usage_known") is not True or
            not all(observation.get("checks", {}).values()) or
            observation.get("new_model_http_calls") != 1 or result.get("source_changed_during_attempt") is not False or
            result.get("within_original_budget") is not True or gate.get("status") != "PASS" or
            gate.get("reviewer") != "coding_agent_semantic_review_not_external_business_owner" or
            gate.get("negative_reply_failures_explicitly_explained") is not True):
        raise RuntimeError("negative_not_semantically_accepted_no_positive_HTTP")
    if gate.get("actual_response_sha256") != digest(response_path.read_bytes()):
        raise RuntimeError("negative_review_source_changed_no_positive_HTTP")


def main():
    from globalmail_agent.adapters.model_provider import ModelProvider, prompt
    from globalmail_agent.agent.budget import input_estimate, output_limit, network_timeout
    from globalmail_agent.agent.outcome_validation import OutcomeReview
    from item_audit import evaluate_item_audit
    from run_eval import code_snapshot
    from prepare_review_capacity_controls import AUTHORIZED_LIMITS
    if sys.prefix.lower() != str(BACKEND / ".venv").lower():
        raise RuntimeError("use_fixed_backend_venv")
    parser = argparse.ArgumentParser()
    parser.add_argument("--preparation")
    parser.add_argument("--attempt")
    parser.add_argument("--step", choices=("negative", "positive"), required=True)
    args = parser.parse_args()
    if args.step == "negative":
        if not args.preparation or args.attempt:
            raise RuntimeError("negative_requires_preparation_only")
        prep_dir = ROOT / "tmp/phase7-agent-eval" / args.preparation
        prepared_manifest = prep_dir / "manifest-planned-zero-http.json"
        preparation = json.loads(prepared_manifest.read_text(encoding="utf-8"))
        attempt = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
        private = ROOT / "tmp/phase7-agent-eval" / attempt
        result = {"attempt_id": attempt, "scope": "standalone_actual_request_coverage_product_validator_adaptation_not_business_cycle",
            "status": "running", "preparation_id": args.preparation,
            "preparation_manifest_sha256": digest(prepared_manifest.read_bytes()), "preparation": preparation,
            "code_snapshot": code_snapshot(), "new_actual_sampling": provider_sampling(),
            "model_provider_sha256": digest((BACKEND / "src/globalmail_agent/adapters/model_provider.py").read_bytes()),
            "observations": [], "active_ms": 0, "reserved_or_known_tokens": 0,
            "business_commit": False, "business_outbound": 0, "original_cycle_request_count_changed": False,
            "original_P7_06_FAIL_and_nine_business_targets_preserved": True,
            "quality_limit": "Known synthetic reply contrast; original wrong understanding retained, no new business PASS."}
    else:
        if not args.attempt or args.preparation:
            raise RuntimeError("positive_requires_existing_attempt_only")
        private = ROOT / "tmp/phase7-agent-eval" / args.attempt
        result = json.loads((private / "result.json").read_text(encoding="utf-8"))
        preparation = result["preparation"]
        prep_dir = ROOT / "tmp/phase7-agent-eval" / result["preparation_id"]
        prepared_manifest = prep_dir / "manifest-planned-zero-http.json"
        gate = json.loads((private / "negative-semantic-review.json").read_text(encoding="utf-8"))
        response_path = private / preparation["targets"][0]["test_id"] / "response-01.json"
        validate_negative_history(result, gate, response_path)
        result["negative_semantic_review_sha256"] = digest((private / "negative-semantic-review.json").read_bytes())
    if preparation.get("origin_attempt") != "20261008-202431-2f2a7ecc" or (
            preparation.get("original_case") != "P7-06-conditional-refund"):
        raise RuntimeError("request_review_origin_changed_no_HTTP")
    if (preparation.get("authorized_stage_limits") != AUTHORIZED_LIMITS or
            preparation.get("source_changed_during_preparation") is not False or
            preparation.get("code_snapshot") != code_snapshot() or
            preparation.get("code_snapshot_after") != code_snapshot()):
        raise RuntimeError("authorized_capacity_preparation_not_current_no_HTTP")
    if digest(prepared_manifest.read_bytes()) != result["preparation_manifest_sha256"]:
        raise RuntimeError("prepared_manifest_changed_no_HTTP")
    if result["code_snapshot"] != code_snapshot() or result["new_actual_sampling"] != provider_sampling():
        raise RuntimeError("actual_control_source_or_sampling_changed_no_HTTP")
    for relative, expected in preparation["trusted_file_sha256"].items():
        if digest((ROOT / relative).read_bytes()) != expected:
            raise RuntimeError("trusted_original_source_changed_no_HTTP")
    targets = preparation["targets"]
    if [t["expected_supported"] for t in targets] != [False, True]:
        raise RuntimeError("control_targets_changed_no_HTTP")
    index = 0 if args.step == "negative" else 1
    target = targets[index]
    request_path = ROOT / target["prepared_file"]
    request = json.loads(request_path.read_text(encoding="utf-8"))
    planned_SDK = None
    if target.get("prepared_SDK_file"):
        SDK_path = ROOT / target["prepared_SDK_file"]
        if digest(SDK_path.read_bytes()) != target["prepared_SDK_file_sha256"]:
            raise RuntimeError("prepared_SDK_changed_no_HTTP")
        planned_SDK = json.loads(SDK_path.read_text(encoding="utf-8"))
    if digest(request_path.read_bytes()) != target["prepared_file_sha256"] or digest(json_bytes(request)) != target["prepared_request_sha256"]:
        raise RuntimeError("prepared_request_changed_no_HTTP")
    if request["messages"][0]["content"] != prompt("validation") or request["messages"][2]["content"] != prompt("validation-grounding"):
        raise RuntimeError("actual_full_source_prompts_not_prepared_no_HTTP")
    if request["schema"] != OutcomeReview.model_json_schema() or request["tools"] is not None:
        raise RuntimeError("actual_review_schema_changed_no_HTTP")
    estimate = input_estimate(request["messages"], [request["schema"]])
    if estimate != target["input_proxy"] or estimate > 16000 or (
            len(result["observations"]) >= 2 or result["active_ms"] >= 120000 or
            result["reserved_or_known_tokens"] + estimate + output_limit("validation") > 80000):
        raise RuntimeError("original_control_budget_exceeded_no_HTTP")
    if not 0 < request["timeout"] <= network_timeout("validation"):
        raise RuntimeError("unexpected_frozen_timeout_no_HTTP")
    effective_request = effective_control_request(request, result["active_ms"])
    if not (private / "manifest-before-paid-calls.json").exists():
        write(private / "manifest-before-paid-calls.json", result)
    write(private / f"manifest-before-{args.step}-call.json", result)
    started = time.monotonic()
    model = ModelProvider(configured_settings())
    traffic = instrument(model, private / target["test_id"])
    observation = {"test_id": target["test_id"], "expected_supported": target["expected_supported"],
        "prepared_request_sha256": target["prepared_request_sha256"],
        "effective_request_sha256": digest(json_bytes(effective_request)),
        "effective_timeout": effective_request["timeout"]}
    reserved = estimate + output_limit("validation")
    response = None
    known = False
    try:
        response = model.request(**effective_request)
        usage = response.get("usage")
        known = known_usage(response)
        if known:
            reserved = usage["prompt_tokens"] + usage["completion_tokens"]
        review = OutcomeReview.model_validate_json(response["content"])
        complete_audit, audit_summary = evaluate_item_audit(review, json.loads(request["messages"][1]["content"]))
        audit_path = private / target["test_id"] / "actual-item-audit.json"
        write(audit_path, complete_audit)
        actual = json.loads((private / target["test_id"] / "request-01.json").read_text(encoding="utf-8"))
        checks = {"supported_matches_frozen_target": review.supported == target["expected_supported"],
            "language_correct": review.language_correct, "unsupported_claim_direction": bool(review.unsupported_claims) != target["expected_supported"],
            "usage_known": known, "finish_complete": response["finish_reason"] == "stop",
            "actual_request_equals_prepared_with_remaining_time_cap": actual == effective_request,
            "single_input_output_within_authorized_stage_limits": known and usage["prompt_tokens"] <= 16000
                and usage["completion_tokens"] <= output_limit("validation"),
            "item_audit_matches_frozen_target": audit_summary["audit_accepts"] == target["expected_supported"],
            "effective_supported_AND_matches_frozen_target": audit_summary["effective_supported_AND"] == target["expected_supported"]}
        if planned_SDK is not None:
            actual_SDK = json.loads((private / target["test_id"] / "provider-payload-01.json").read_text(encoding="utf-8"))
            reasoning = (usage or {}).get("completion_tokens_details", {}).get("reasoning_tokens")
            checks.update(actual_complete_SDK_equals_planned=actual_SDK == planned_SDK,
                reasoning_usage_included_in_total=known and type(reasoning) is int
                    and 0 <= reasoning <= usage["completion_tokens"])
        observation.update({"actual_supported": review.supported, "actual_language_correct": review.language_correct,
            "unsupported_claim_count": len(review.unsupported_claims), "reason_sha256": digest(review.reason.encode()),
            "item_audit": audit_summary, "complete_item_audit_file": str(audit_path.relative_to(ROOT)).replace("\\", "/"),
            "complete_item_audit_file_sha256": digest(audit_path.read_bytes()),
            "usage": usage, "provider_request_id": response.get("request_id"), "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL"})
    except Exception as error:
        observation.update({"status": "FAIL", "error_type": type(error).__name__, "error_code": getattr(error, "code", None),
            "usage": response.get("usage") if response else None, "unknown_usage_not_zero": not known,
            "provider_request_id": response.get("request_id") if response else None})
    finally:
        observation["new_model_http_calls"] = len(traffic)
        observation["seconds"] = round(sum(t["seconds"] for t in traffic), 3)
        result["observations"].append(observation)
        result["active_ms"] += int((time.monotonic() - started) * 1000)
        result["reserved_or_known_tokens"] += reserved
        result["new_model_http_calls"] = sum(o["new_model_http_calls"] for o in result["observations"])
        result["code_snapshot_after"] = code_snapshot()
        result["source_changed_during_attempt"] = result["code_snapshot_after"] != result["code_snapshot"]
        result["within_original_budget"] = result["active_ms"] <= 120000 and result["reserved_or_known_tokens"] <= 80000 and result["new_model_http_calls"] <= 2
        result["semantic_gate_idle_time_excluded_from_active_ms"] = True
        result["status"] = ("stopped_on_first_adaptation_failure" if observation["status"] != "PASS" or
            result["source_changed_during_attempt"] or not result["within_original_budget"] else
            "awaiting_negative_fulltext_review" if index == 0 else "two_controls_executed_manual_fulltext_review_pending")
        write(private / "result.json", result)
        artifact = ROOT / "docs/verification/artifacts/phase7/real-model.json"
        previous = json.loads(artifact.read_text(encoding="utf-8"))
        prior_results = previous.setdefault("standalone_adaptation_tests", [])
        prior_results[:] = [r for r in prior_results if r.get("attempt_id") != result["attempt_id"]]
        prior_results.append(result)
        write(artifact, previous)
    print(json.dumps({"attempt": result["attempt_id"], "test": target["test_id"], "status": result["status"],
        "supported": observation.get("actual_supported"), "new_model_http_calls": result["new_model_http_calls"]}))
    if result["status"] == "stopped_on_first_adaptation_failure":
        sys.exit(1)


if __name__ == "__main__":
    main()
