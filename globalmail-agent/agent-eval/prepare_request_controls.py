"""Zero-HTTP full-source intent-coverage/product-name contrasts for the failed P7-06."""
from copy import deepcopy
import json
import sys
import time
from uuid import uuid4
from bootstrap import ROOT, BACKEND, digest, frozen_inputs, json_bytes, provider_sampling, provider_tool_choice_strategy, write
from prepare_cause_controls import field_changes

ORIGIN = "20261008-202431-2f2a7ecc"
CASE = "P7-06-conditional-refund"
BEFORE = "The parcel containing your OUTON ceiling light (SKU: H-CTD16-US-BK) is currently marked"
AFTER = "The parcel is currently marked"
PREFERENCE = "You said that if the parcel still does not arrive, you will want a refund then, and that you are not asking for a refund now."
SOURCE_QUOTE = "If it still does not arrive, I will want a refund then, but I am not asking you to refund it now."


def synthetic_positive(original):
    payload = deepcopy(original)
    draft = payload["draft"]
    original_draft = original["draft"]
    if len(draft["claims"]) != 3 or draft["body"] != "\n\n".join(c["text"] for c in draft["claims"]):
        raise RuntimeError("request_control_original_claim_structure_changed")
    if draft["body"].count(BEFORE) != 1 or draft["claims"][1]["text"].count(BEFORE) != 1 or (
            draft["claims"][1]["kind"] != "order_fact"):
        raise RuntimeError("request_control_original_unsupported_prefix_changed")
    sources = [m for m in original["context"]["messages"] if m["sender"] == "customer" and SOURCE_QUOTE in m["body"]]
    if len(sources) != 1:
        raise RuntimeError("request_control_future_preference_source_not_unique")
    draft["claims"][1]["text"] = draft["claims"][1]["text"].replace(BEFORE, AFTER, 1)
    added = {"kind": "customer_fact", "text": PREFERENCE, "source_ids": [sources[0]["message_id"]]}
    draft["claims"].append(added)
    draft["body"] = "\n\n".join(c["text"] for c in draft["claims"])
    if field_changes(original_draft["claims"], draft["claims"][:3]) != ["[1].text"] or (
            {k: v for k, v in original_draft.items() if k not in {"body", "claims"}} !=
            {k: v for k, v in draft.items() if k not in {"body", "claims"}} or
            {k: v for k, v in original.items() if k != "draft"} != {k: v for k, v in payload.items() if k != "draft"}):
        raise RuntimeError("request_control_changed_other_source_data")
    expected_body = original_draft["body"].replace(BEFORE, AFTER, 1) + "\n\n" + PREFERENCE
    if draft["body"] != expected_body:
        raise RuntimeError("request_control_body_contains_other_changes")
    operations = [
        {"field": "draft.body", "operation": "replace_unsupported_product_prefix_once", "before": BEFORE, "after": AFTER, "count": 1},
        {"field": "draft.claims[1].text", "operation": "replace_same_prefix_once", "before": BEFORE, "after": AFTER, "count": 1},
        {"field": "draft.body", "operation": "append_one_customer_preference_paragraph", "separator": "\n\n", "text": PREFERENCE},
        {"field": "draft.claims[3]", "operation": "append_customer_fact_with_original_customer_source", "value": added}]
    return payload, {"origin": "explicit_synthetic_reply_contrast_not_new_model_draft_or_understanding",
        "operations": operations, "source_quote": SOURCE_QUOTE, "source_message_id": sources[0]["message_id"],
        "all_non_draft_DATA_including_original_wrong_understanding_unchanged": True,
        "all_existing_claim_fields_and_sources_except_claim1_text_unchanged": True,
        "original_three_claim_order_preserved_new_fact_appended": True,
        "positive_not_evidence_of_correct_understanding": True,
        "body_equals_exact_ordered_claim_join": True}


def main():
    from globalmail_agent.adapters.model_provider import prompt
    from globalmail_agent.agent.budget import input_estimate
    from globalmail_agent.agent.outcome_validation import OutcomeReview
    from globalmail_agent.knowledge.base import canonical
    from run_eval import code_snapshot
    if sys.prefix.lower() != str(BACKEND / ".venv").lower():
        raise RuntimeError("use_fixed_backend_venv")
    _, freeze = frozen_inputs()
    source = ROOT / "tmp/phase7-agent-eval" / ORIGIN
    request_path = source / CASE / "request-05.json"
    prior = json.loads(request_path.read_text(encoding="utf-8"))
    head, tail = prompt("validation"), prompt("validation-grounding")
    planned_path = ROOT / "tmp/phase7-request-review-tail.md"
    planned_tail = planned_path.read_text(encoding="utf-8")
    if not planned_tail.strip() or [m["role"] for m in prior["messages"]] != ["system", "user", "system"]:
        raise RuntimeError("request_control_unexpected_original_structure")
    if prior["messages"][0]["content"] != head or prior["messages"][2]["content"] != tail:
        raise RuntimeError("request_control_current_source_changed_before_freeze")
    if prior["schema"] != OutcomeReview.model_json_schema() or prior["tools"] is not None:
        raise RuntimeError("request_control_original_schema_changed")
    original_payload = json.loads(prior["messages"][1]["content"])
    positive_payload, variant = synthetic_positive(original_payload)
    attempt = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    private = ROOT / "tmp/phase7-agent-eval" / attempt
    trusted = [source / CASE / f"{kind}-{i:02}.json" for i in range(1, 6) for kind in ("request", "response", "provider-payload")]
    trusted += [source / CASE / "run-record.json", source / CASE / "semantic-review.json",
        source / "result.json", source / "manifest-before-paid-calls.json", source / "progress.json", planned_path]
    metadata = {"attempt_id": attempt, "status": "planned_request_review_tail_frozen_zero_HTTP_not_quality",
        "scope": "standalone_intent_coverage_and_product_source_contrast_not_business_cycle", "origin_attempt": ORIGIN,
        "original_case": CASE, "original_quality_FAIL_preserved": True, "new_model_HTTP_calls": 0,
        "business_commit": False, "business_outbound": 0, "original_cycle_request_count_changed": False,
        "trusted_file_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p.read_bytes()) for p in trusted},
        "code_snapshot": code_snapshot(), "freeze": freeze, "new_actual_sampling": provider_sampling(),
        "provider_tool_choice_strategy": provider_tool_choice_strategy(),
        "runtime": {"fixed_python": str(BACKEND / ".venv/Scripts/python.exe"), "python_version": sys.version.split()[0]},
        "system": {"head_sha256": digest(head.encode()), "unchanged_original_tail_sha256": digest(tail.encode()),
            "planned_tail_text_sha256": digest(planned_tail.encode()), "combined_prepared_tail_sha256": digest((tail + "\n" + planned_tail).encode()),
            "join_rule": "current_tail + one_newline + planned_tail_verbatim", "planned_tail_is_product_source": False,
            "actual_source_and_input_proxy_must_be_rechecked_before_any_future_HTTP": True},
        "original_budget": {"model_requests": 6, "tools": 12, "input": 16000, "output": 2000, "tokens": 80000, "active_ms": 120000},
        "targets": [], "quality_limit": "Synthetic diagnostic only; wrong original understanding retained, no fresh business PASS."}
    non_draft = {k: v for k, v in original_payload.items() if k != "draft"}
    for name, supported, payload in (("unsupported_product_and_missing_conditional_original", False, original_payload),
            ("generic_parcel_and_customer_preference_synthetic", True, positive_payload)):
        current = deepcopy(prior)
        current["messages"][2]["content"] = tail + "\n" + planned_tail
        if supported:
            current["messages"][1]["content"] = canonical(payload).decode()
        if not supported and current["messages"][1] != prior["messages"][1]:
            raise RuntimeError("request_control_negative_user_changed")
        estimate = input_estimate(current["messages"], [current["schema"]])
        if estimate > 16000:
            raise RuntimeError("input_budget_exceeded_zero_HTTP")
        destination = private / name / "prepared-request-before-paid-call.json"
        write(destination, current)
        metadata["targets"].append({"test_id": name, "expected_supported": supported, "input_proxy": estimate,
            "prepared_file": str(destination.relative_to(ROOT)).replace("\\", "/"), "prepared_file_sha256": digest(destination.read_bytes()),
            "prepared_request_sha256": digest(json_bytes(current)), "schema_sha256": digest(json_bytes(current["schema"])),
            "original_user_sha256": digest(prior["messages"][1]["content"].encode()),
            "prepared_user_sha256": digest(current["messages"][1]["content"].encode()),
            "all_non_draft_data_sha256": digest(json_bytes(non_draft)), "complete_negative_DATA_unchanged": not supported,
            "synthetic_variant": variant if supported else None})
    metadata["reserved_tokens_for_two_future_controls"] = sum(t["input_proxy"] + 2000 for t in metadata["targets"])
    metadata["code_snapshot_after"] = code_snapshot()
    metadata["source_changed_during_preparation"] = metadata["code_snapshot"] != metadata["code_snapshot_after"]
    if metadata["source_changed_during_preparation"] or metadata["reserved_tokens_for_two_future_controls"] > 80000:
        raise RuntimeError("request_control_source_or_budget_changed")
    write(private / "manifest-planned-zero-http.json", metadata)
    print(json.dumps({"attempt": attempt, "status": metadata["status"], "new_model_HTTP_calls": 0,
        "targets": [{"test": t["test_id"], "input_proxy": t["input_proxy"]} for t in metadata["targets"]]}))


if __name__ == "__main__":
    main()
