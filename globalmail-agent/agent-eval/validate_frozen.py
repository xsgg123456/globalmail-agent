"""Two actual provider reviews of frozen full inputs; not a seventh business-cycle request."""
from copy import deepcopy
import argparse
import json
import sys
import time
from uuid import uuid4
from bootstrap import ROOT, BACKEND, configured_settings, frozen_inputs, provider_sampling, write, digest, json_bytes
from recording import instrument


def main():
    from globalmail_agent.adapters.model_provider import ModelProvider, prompt
    from globalmail_agent.agent.budget import input_estimate
    from globalmail_agent.agent.outcome_validation import OutcomeReview
    if sys.prefix.lower() != str(BACKEND / ".venv").lower():
        raise RuntimeError("use_fixed_backend_venv")
    _, freeze = frozen_inputs()
    parser = argparse.ArgumentParser()
    parser.add_argument("--pure-question-variant", action="store_true",
        help="Authorized synthetic contrast: delete the vague physical-check prefix, preserve all other source data")
    parser.add_argument("--conditional-when-request", action="store_true",
        help="Review complete actual 182447 conditional When request; keep its draft and every source unchanged")
    parser.add_argument("--human-plan-request", action="store_true",
        help="Original actual04 pending-to-current execution negative and explicitly synthetic awaiting variant")
    parser.add_argument("--preflight-only", action="store_true", help="Freeze full prepared requests and proxy limits; no HTTP")
    args = parser.parse_args()
    targets = [("neutral_yes_no", "20261008-180804-6cae1f4f", "P7-02-order-and-evidence", 6, True),
        ("unsupported_when", "20261008-175613-3c27e549", "P7-02-order-and-evidence", 5, False)]
    if args.conditional_when_request:
        if args.pure_question_variant:
            raise RuntimeError("choose_one_frozen_positive_input")
        targets[0] = ("conditional_when_full_actual_draft", "20261008-182447-c623f2cd", "P7-02-order-and-evidence", 5, True)
    if args.human_plan_request:
        if args.pure_question_variant or args.conditional_when_request:
            raise RuntimeError("choose_one_frozen_boundary_pair")
        targets = [("human_plan_promoted_to_current_original", "20261008-191114-7c80c70b", "P7-04-after-human", 4, False),
            ("human_plan_awaiting_synthetic_variant", "20261008-191114-7c80c70b", "P7-04-after-human", 4, True)]
    attempt = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    private = ROOT / "tmp/phase7-agent-eval" / attempt
    from run_eval import code_snapshot
    result = {"attempt_id": attempt, "scope": "standalone_actual_qwen_outcome_review_adaptation_not_business_cycle",
        "status": "running", "new_actual_sampling": provider_sampling(), "snapshot": freeze,
        "code_snapshot": code_snapshot(),
        "model_provider_sha256": digest((BACKEND / "src/globalmail_agent/adapters/model_provider.py").read_bytes()),
        "validation_prompt_sha256": digest(prompt("validation").encode()),
        "validation_grounding_prompt_sha256": digest(prompt("validation-grounding").encode()),
        "graph_sha256": digest((BACKEND / "src/globalmail_agent/agent/graph.py").read_bytes()),
        "targets": [], "observations": [],
        "business_outbound": 0, "business_commit": False, "original_cycle_request_count_changed": False,
        "quality_limit": "Two material-aware frozen contrast examples; no independent holdout or new closed-loop PASS.",
        "original_budget": {"model_requests": 6, "input": 16000, "output": 2000, "tokens": 80000, "active_ms": 120000}}
    prepared = []
    for identity, origin, case_id, index, supported in targets:
        path = ROOT / "tmp/phase7-agent-eval" / origin / case_id / f"request-{index:02}.json"
        prior = json.loads(path.read_text(encoding="utf-8"))
        current = deepcopy(prior)
        if [m["role"] for m in prior["messages"]] not in (["system", "user"], ["system", "user", "system"]):
            raise RuntimeError("frozen_validation_message_structure_changed")
        current["messages"] = current["messages"][:2]
        current["messages"][0]["content"] = prompt("validation")
        if prior["schema"] != OutcomeReview.model_json_schema() or prior["tools"] is not None:
            raise RuntimeError("frozen_validation_schema_changed")
        variant = None
        if args.pure_question_variant and identity == "neutral_yes_no":
            original_payload = json.loads(prior["messages"][1]["content"])
            payload = deepcopy(original_payload)
            draft = payload["draft"]
            first, second = draft["body"].split("\n\n", 1)
            questions = second[second.index("Have you tried"):]
            order_claim = deepcopy(draft["claims"][0])
            question_claim = deepcopy(draft["claims"][-1])
            if order_claim["text"] != first or question_claim["kind"] != "clarification":
                raise RuntimeError("synthetic_variant_unexpected_source_structure")
            question_claim["text"] = questions
            draft["body"], draft["claims"] = first + "\n\n" + questions, [order_claim, question_claim]
            original_data = {k: v for k, v in original_payload.items() if k != "draft"}
            if {k: v for k, v in payload.items() if k != "draft"} != original_data:
                raise RuntimeError("synthetic_variant_changed_non_draft_data")
            from globalmail_agent.knowledge.base import canonical
            current["messages"][1]["content"] = canonical(payload).decode()
            identity = "neutral_pure_question_synthetic_variant"
            variant = {"origin": "authorized_synthetic_boundary_variant_not_actual_new_model_draft",
                "modified_fields": ["draft.body", "draft.claims"], "kept_order_fact_paragraph_and_claim_exactly": True,
                "removed_prefix_sha256": digest(second[:second.index("Have you tried")].encode()),
                "removed_prefix_chars": second.index("Have you tried"), "removed_customer_fact_claims": 1,
                "clarification_text_equals_question_paragraph": True,
                "original_draft_sha256": digest(json_bytes(original_payload["draft"])),
                "all_non_draft_data_sha256": digest(json_bytes(original_data)), "all_non_draft_data_unchanged": True,
                "does_not_change_original_181311_target_or_nine_business_cases": True}
        if identity == "human_plan_awaiting_synthetic_variant":
            original_payload = json.loads(prior["messages"][1]["content"])
            payload = deepcopy(original_payload)
            before = "Our staff is currently checking the compatible remote specifications before proposing any next steps."
            after = "We are awaiting staff review of the compatible remote specifications before proposing any next steps."
            draft = payload["draft"]
            if draft["body"].count(before) != 1 or sum(c["text"].count(before) for c in draft["claims"]) != 1:
                raise RuntimeError("synthetic_human_plan_unexpected_source_clause")
            draft["body"] = draft["body"].replace(before, after)
            for claim in draft["claims"]:
                claim["text"] = claim["text"].replace(before, after)
            original_data = {k: v for k, v in original_payload.items() if k != "draft"}
            if {k: v for k, v in payload.items() if k != "draft"} != original_data:
                raise RuntimeError("synthetic_human_plan_changed_non_draft_data")
            from globalmail_agent.knowledge.base import canonical
            current["messages"][1]["content"] = canonical(payload).decode()
            variant = {"origin": "authorized_synthetic_human_plan_boundary_variant_not_actual_new_model_draft",
                "modified_fields": ["draft.body", "draft.claims[1].text"],
                "original_status_clause": before, "synthetic_status_clause": after,
                "kept_all_other_draft_fields_and_claim_source_ids": True,
                "original_draft_sha256": digest(json_bytes(original_payload["draft"])),
                "all_non_draft_data_sha256": digest(json_bytes(original_data)), "all_non_draft_data_unchanged": True,
                "does_not_change_original_191114_quality_FAIL_or_nine_business_cases": True}
        if not variant and current["messages"][1] != prior["messages"][1]:
            raise RuntimeError("frozen_validation_data_changed")
        current["messages"].append({"role": "system", "content": prompt("validation-grounding")})
        estimate = input_estimate(current["messages"], [current["schema"]])
        if estimate > 16000:
            raise RuntimeError("input_budget_exceeded_no_paid_calls")
        payload = json.loads(current["messages"][1]["content"])
        metadata = {"test_id": identity, "origin_attempt_id": origin, "origin_request_index": index,
            "expected_supported": supported, "source_request_sha256": digest(path.read_bytes()),
            "new_request_sha256": digest(json_bytes(current)), "input_proxy": estimate,
            "draft_sha256": digest(json_bytes(payload["draft"])),
            "source_messages": [{"message_id": m["message_id"], "seq": m["seq"], "sender": m["sender"],
                "body_sha256": digest(m["body"].encode())} for m in payload["context"]["messages"]],
            "complete_user_data_unchanged": variant is None,
            "message_roles_match_current_graph": [m["role"] for m in current["messages"]] == ["system", "user", "system"],
            "system_changes": "replace_first_validation_and_append_current_validation_grounding",
            "synthetic_variant": variant}
        prepared.append((metadata, current))
        result["targets"].append(metadata)
        write(private / identity / "prepared-request-before-paid-call.json", current)
    write(private / "manifest-before-paid-calls.json", result)
    if args.preflight_only:
        result["status"] = "frozen_preflight_only_zero_http_not_quality"
        result["new_model_http_calls"] = 0
        write(private / "preflight.json", result)
        print(json.dumps({"attempt": attempt, "status": result["status"],
            "targets": [{"test": t["test_id"], "input_proxy": t["input_proxy"]} for t in result["targets"]]}))
        return
    started = time.monotonic()
    reserved = 0
    try:
        for target, request in prepared:
            reserved += target["input_proxy"] + 2000
            if len(result["observations"]) >= 6 or reserved > 80000 or time.monotonic() - started >= 120:
                raise RuntimeError("standalone_original_budget_exhausted")
            model = ModelProvider(configured_settings())
            traffic = instrument(model, private / target["test_id"])
            observation = {"test_id": target["test_id"], "expected_supported": target["expected_supported"]}
            try:
                response = model.request(request["messages"], schema=request["schema"], tools=None,
                    timeout=min(30, 120 - (time.monotonic() - started)))
                review = OutcomeReview.model_validate_json(response["content"])
                usage = response.get("usage")
                known = bool(usage) and all(type(usage.get(k)) is int and usage[k] >= 0
                    for k in ("prompt_tokens", "completion_tokens"))
                if known:
                    reserved += usage["prompt_tokens"] + usage["completion_tokens"] - target["input_proxy"] - 2000
                checks = {"supported_matches_frozen_target": review.supported == target["expected_supported"],
                    "language_correct": review.language_correct,
                    "unsupported_claim_direction": bool(review.unsupported_claims) != target["expected_supported"],
                    "usage_known": known, "single_input_output_within_original_limits": known
                        and usage["prompt_tokens"] <= 16000 and usage["completion_tokens"] <= 2000,
                    "finish_complete": response["finish_reason"] == "stop"}
                observation.update({"actual_supported": review.supported, "actual_language_correct": review.language_correct,
                    "unsupported_claim_count": len(review.unsupported_claims), "reason_sha256": digest(review.reason.encode()),
                    "provider_request_id": response.get("request_id"), "usage": usage, "checks": checks,
                    "status": "PASS" if all(checks.values()) else "FAIL"})
            except Exception as error:
                observation.update({"status": "FAIL", "error_code": getattr(error, "code", type(error).__name__),
                    "usage": None, "unknown_usage_not_zero": True})
            observation["new_model_http_calls"] = len(traffic)
            observation["seconds"] = round(sum(t["seconds"] for t in traffic), 3)
            result["observations"].append(observation)
            print(json.dumps({"test": target["test_id"], "status": observation["status"],
                "supported": observation.get("actual_supported"), "error_code": observation.get("error_code")}), flush=True)
            if observation["status"] != "PASS":
                result["status"] = "stopped_on_first_adaptation_failure"
                break
        else:
            result["status"] = "two_frozen_adaptation_examples_pass_not_business_cycle_pass"
    finally:
        result["active_ms"] = int((time.monotonic() - started) * 1000)
        result["reserved_or_known_tokens"] = reserved
        result["new_model_http_calls"] = sum(o["new_model_http_calls"] for o in result["observations"])
        result["validation_prompt_sha256_after"] = digest(prompt("validation").encode())
        result["validation_grounding_prompt_sha256_after"] = digest(prompt("validation-grounding").encode())
        result["graph_sha256_after"] = digest((BACKEND / "src/globalmail_agent/agent/graph.py").read_bytes())
        result["code_snapshot_after"] = code_snapshot()
        result["implementation_changed_during_attempt"] = result["code_snapshot"] != result["code_snapshot_after"]
        result["within_original_budget"] = len(result["observations"]) <= 6 and reserved <= 80000 and result["active_ms"] <= 120000
        write(private / "result.json", result)
        artifact = ROOT / "docs/verification/artifacts/phase7/real-model.json"
        previous = json.loads(artifact.read_text(encoding="utf-8"))
        previous.setdefault("standalone_adaptation_tests", []).append(result)
        write(artifact, previous)
    if result["status"] != "two_frozen_adaptation_examples_pass_not_business_cycle_pass":
        sys.exit(1)


if __name__ == "__main__":
    main()
