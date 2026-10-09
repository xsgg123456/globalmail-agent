"""Freeze full H11 cause contrasts with a planned tail; deliberately no HTTP path."""
from copy import deepcopy
import json
import sys
import time
from uuid import uuid4
from bootstrap import ROOT, BACKEND, digest, frozen_inputs, json_bytes, provider_sampling, provider_tool_choice_strategy, write

ORIGIN = "20261008-200822-db9f795d"
CASE = "P7-05-german"
REMOVED = "Da die Lampe selbst reagiert, liegt das Problem wahrscheinlich an der Verbindung zur Fernbedienung. "


def field_changes(before, after, path=""):
    if type(before) is not type(after):
        return [path]
    if isinstance(before, dict):
        if before.keys() != after.keys():
            return [path]
        return [change for key in before for change in field_changes(before[key], after[key], f"{path}.{key}".strip("."))]
    if isinstance(before, list):
        if len(before) != len(after):
            return [path]
        return [change for i, (old, new) in enumerate(zip(before, after)) for change in field_changes(old, new, f"{path}[{i}]")]
    return [] if before == after else [path]


def synthetic_positive(original):
    """Remove exactly one whole causal sentence in the body and its sole claim."""
    payload = deepcopy(original)
    draft = payload["draft"]
    counts = [claim["text"].count(REMOVED) for claim in draft["claims"]]
    if draft["body"].count(REMOVED) != 1 or sum(counts) != 1 or 1 not in counts:
        raise RuntimeError("cause_control_expected_one_body_and_one_claim_occurrence")
    index = counts.index(1)
    draft["body"] = draft["body"].replace(REMOVED, "", 1)
    draft["claims"][index]["text"] = draft["claims"][index]["text"].replace(REMOVED, "", 1)
    expected = ["draft.body", f"draft.claims[{index}].text"]
    changes = field_changes(original, payload)
    if sorted(changes) != sorted(expected):
        raise RuntimeError("cause_control_changed_other_data")
    return payload, {"origin": "explicit_synthetic_contrast_not_actual_new_model_draft",
        "modified_fields": changes, "removed_exact_sentence": REMOVED,
        "removed_sentence_sha256": digest(REMOVED.encode()), "body_deletions": 1, "claim_deletions": 1,
        "all_other_data_schema_questions_and_citations_unchanged": True}


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
    request_path = source / CASE / "request-06.json"
    prior = json.loads(request_path.read_text(encoding="utf-8"))
    head, tail = prompt("validation"), prompt("validation-grounding")
    planned_path = ROOT / "tmp/phase7-cause-validator-tail.md"
    planned_tail = planned_path.read_text(encoding="utf-8")
    if not planned_tail.strip() or [m["role"] for m in prior["messages"]] != ["system", "user", "system"]:
        raise RuntimeError("cause_control_unexpected_original_structure")
    if prior["messages"][0]["content"] != head or prior["messages"][2]["content"] != tail:
        raise RuntimeError("cause_control_current_prompt_changed_before_freeze")
    if prior["schema"] != OutcomeReview.model_json_schema() or prior["tools"] is not None:
        raise RuntimeError("cause_control_original_schema_changed")
    combined_tail = tail + "\n" + planned_tail
    original_payload = json.loads(prior["messages"][1]["content"])
    positive_payload, variant = synthetic_positive(original_payload)
    attempt = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    private = ROOT / "tmp/phase7-agent-eval" / attempt
    trusted = [request_path, source / CASE / "response-06.json", source / CASE / "provider-payload-06.json",
        source / CASE / "run-record.json", source / CASE / "semantic-review.json",
        source / "result.json", source / "manifest-before-paid-calls.json", planned_path]
    metadata = {"attempt_id": attempt, "status": "planned_tail_frozen_zero_http_not_quality",
        "scope": "standalone_cause_boundary_preparation_not_business_cycle",
        "original_attempt": ORIGIN, "original_case": CASE, "original_quality_FAIL_preserved": True,
        "new_model_http_calls": 0, "business_commit": False, "business_outbound": 0,
        "original_cycle_request_count_changed": False, "nine_frozen_business_targets_changed": False,
        "trusted_file_sha256": {str(path.relative_to(ROOT)).replace("\\", "/"): digest(path.read_bytes()) for path in trusted},
        "code_snapshot": code_snapshot(), "freeze": freeze, "new_actual_sampling": provider_sampling(),
        "provider_tool_choice_strategy": provider_tool_choice_strategy(),
        "runtime": {"fixed_python": str(BACKEND / ".venv/Scripts/python.exe"), "python_version": sys.version.split()[0]},
        "system": {"head_sha256": digest(head.encode()), "unchanged_original_tail_sha256": digest(tail.encode()),
            "planned_tail_text_sha256": digest(planned_tail.encode()), "combined_prepared_tail_sha256": digest(combined_tail.encode()),
            "join_rule": "current_tail + one_newline + planned_tail_verbatim",
            "planned_tail_is_product_source": False, "must_match_actual_source_before_any_future_HTTP": True},
        "original_budget": {"model_requests": 6, "tools": 12, "input": 16000, "output": 2000, "tokens": 80000, "active_ms": 120000},
        "targets": [], "quality_limit": "Known-material diagnostic contrasts; no independent holdout or new business PASS."}
    original_non_draft = {k: v for k, v in original_payload.items() if k != "draft"}
    for name, supported, payload in (("unsupported_cause_original", False, original_payload),
            ("question_without_cause_synthetic", True, positive_payload)):
        prepared = deepcopy(prior)
        prepared["messages"][2]["content"] = combined_tail
        if supported:
            prepared["messages"][1]["content"] = canonical(payload).decode()
        if prepared["schema"] != prior["schema"] or prepared["messages"][0] != prior["messages"][0]:
            raise RuntimeError("cause_control_changed_head_or_schema")
        if not supported and prepared["messages"][1] != prior["messages"][1]:
            raise RuntimeError("cause_control_negative_data_changed")
        estimate = input_estimate(prepared["messages"], [prepared["schema"]])
        if estimate > 16000:
            raise RuntimeError("input_budget_exceeded_no_HTTP")
        target = {"test_id": name, "expected_supported": supported, "input_proxy": estimate,
            "prepared_file": str((private / name / "prepared-request-before-paid-call.json").relative_to(ROOT)).replace("\\", "/"),
            "prepared_request_sha256": digest(json_bytes(prepared)),
            "original_user_sha256": digest(prior["messages"][1]["content"].encode()),
            "prepared_user_sha256": digest(prepared["messages"][1]["content"].encode()),
            "schema_sha256": digest(json_bytes(prepared["schema"])), "all_non_draft_data_sha256": digest(json_bytes(original_non_draft)),
            "data_field_changes": field_changes(original_payload, payload),
            "synthetic_variant": variant if supported else None}
        write(private / name / "prepared-request-before-paid-call.json", prepared)
        target["prepared_file_sha256"] = digest((private / name / "prepared-request-before-paid-call.json").read_bytes())
        metadata["targets"].append(target)
    metadata["reserved_tokens_for_two_future_controls"] = sum(t["input_proxy"] + 2000 for t in metadata["targets"])
    metadata["code_snapshot_after"] = code_snapshot()
    metadata["source_changed_during_preparation"] = metadata["code_snapshot"] != metadata["code_snapshot_after"]
    if metadata["source_changed_during_preparation"] or metadata["reserved_tokens_for_two_future_controls"] > 80000:
        raise RuntimeError("cause_control_source_or_original_budget_changed")
    write(private / "manifest-planned-zero-http.json", metadata)
    print(json.dumps({"attempt": attempt, "status": metadata["status"], "new_model_http_calls": 0,
        "targets": [{"test": t["test_id"], "input_proxy": t["input_proxy"], "changes": t["data_field_changes"]} for t in metadata["targets"]]}))


if __name__ == "__main__":
    main()
