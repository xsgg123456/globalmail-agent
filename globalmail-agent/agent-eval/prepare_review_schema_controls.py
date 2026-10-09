"""Freeze a schema-only candidate; full prior messages and defective evidence remain."""
from copy import deepcopy
import ast
import json
import sys
import time
from uuid import uuid4
from bootstrap import ROOT, BACKEND, digest, frozen_inputs, json_bytes, provider_sampling, write

PRIOR = "20261008-203514-f5ace13f"
FAIL = "20261008-204212-6fd7f486"
ORDER = ["reason", "unsupported_claims", "supported", "language_correct"]


def without_descriptions(value):
    if isinstance(value, dict):
        return {key: without_descriptions(item) for key, item in value.items() if key != "description"}
    if isinstance(value, list):
        return [without_descriptions(item) for item in value]
    return value


def schema_audit(old, new):
    if set(old["properties"]) != set(new["properties"]) or set(old["required"]) != set(new["required"]):
        raise RuntimeError("review_schema_field_or_required_set_changed")
    if list(new["properties"]) != ORDER or new["required"] != ORDER:
        raise RuntimeError("review_schema_candidate_output_order_changed")
    if {k: v for k, v in old.items() if k not in {"properties", "required"}} != (
            {k: v for k, v in new.items() if k not in {"properties", "required"}}):
        raise RuntimeError("review_schema_top_level_contract_changed")
    fields = []
    for name in ORDER:
        if without_descriptions(old["properties"][name]) != without_descriptions(new["properties"][name]):
            raise RuntimeError("review_schema_type_or_bound_changed")
        fields.append({"name": name, "old_description": old["properties"][name].get("description"),
            "new_description": new["properties"][name].get("description"),
            "type_and_bounds_equal": True, "unchanged_field_contract": without_descriptions(old["properties"][name])})
    if new.get("additionalProperties") is not False or new["properties"]["reason"].get("maxLength") != 1500 or (
            new["properties"]["unsupported_claims"].get("maxItems") != 20):
        raise RuntimeError("review_schema_original_strict_limits_changed")
    return {"old_property_order": list(old["properties"]), "new_property_order": list(new["properties"]),
        "old_required_order": old["required"], "new_required_order": new["required"],
        "required_set_equal": True, "additionalProperties_false_preserved": True, "fields": fields,
        "only_output_property_required_order_and_descriptions_changed": True}


def main():
    from globalmail_agent.adapters.model_provider import prompt
    from globalmail_agent.agent.budget import input_estimate
    from globalmail_agent.agent.outcome_validation import OutcomeReview
    from run_eval import code_snapshot
    if sys.prefix.lower() != str(BACKEND / ".venv").lower():
        raise RuntimeError("use_fixed_backend_venv")
    _, freeze = frozen_inputs()
    prior_dir = ROOT / "tmp/phase7-agent-eval" / PRIOR
    prior_manifest_path = prior_dir / "manifest-planned-zero-http.json"
    prior = json.loads(prior_manifest_path.read_text(encoding="utf-8"))
    planned_path = ROOT / "tmp/phase7-planned-outcome-review-schema.json"
    planned_source = ROOT / "tmp/phase7-planned-outcome-review.py"
    candidate = json.loads(planned_path.read_text(encoding="utf-8"))
    source_tree = ast.parse(planned_source.read_text(encoding="utf-8"))
    planned_class = next(node for node in source_tree.body if isinstance(node, ast.ClassDef) and node.name == "OutcomeReview")
    source_order = [node.target.id for node in planned_class.body if isinstance(node, ast.AnnAssign)]
    if source_order != ORDER:
        raise RuntimeError("planned_schema_source_order_mismatch")
    attempt = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    private = ROOT / "tmp/phase7-agent-eval" / attempt
    trusted = dict(prior["trusted_file_sha256"])
    more = [prior_manifest_path, *[ROOT / t["prepared_file"] for t in prior["targets"]], planned_path, planned_source]
    failed_dir = ROOT / "tmp/phase7-agent-eval" / FAIL
    more += [failed_dir / "unsupported_product_and_missing_conditional_original" / name
        for name in ("request-01.json", "response-01.json", "provider-payload-01.json")]
    more += [failed_dir / name for name in ("manifest-before-paid-calls.json", "manifest-before-negative-call.json",
        "result.json", "negative-semantic-review.json", "actual-source-SDK-audit.json")]
    for relative, expected in trusted.items():
        if digest((ROOT / relative).read_bytes()) != expected:
            raise RuntimeError("original_21_trusted_source_SHA_changed")
    trusted.update({str(p.relative_to(ROOT)).replace("\\", "/"): digest(p.read_bytes()) for p in more})
    metadata = {"attempt_id": attempt, "status": "candidate_schema_only_zero_HTTP_not_quality",
        "scope": "planned_review_schema_adaptation_not_business_cycle", "origin_attempt": prior["origin_attempt"],
        "original_case": prior["original_case"], "prior_preparation_id": PRIOR, "actual_negative_FAIL_id": FAIL,
        "original_quality_FAIL_and_control_FAIL_preserved": True, "new_model_http_calls": 0,
        "business_commit": False, "business_outbound": 0, "original_cycle_request_count_changed": False,
        "trusted_file_sha256": trusted, "code_snapshot": code_snapshot(), "freeze": freeze,
        "new_actual_sampling": provider_sampling(), "runtime": prior["runtime"],
        "candidate_is_product_schema": OutcomeReview.model_json_schema() == candidate,
        "candidate_is_proven_root_cause": False,
        "original_budget": prior["original_budget"], "targets": [],
        "quality_limit": "Same known contrasts and original wrong understanding; schema candidate not business PASS."}
    for target in prior["targets"]:
        path = ROOT / target["prepared_file"]
        before = json.loads(path.read_text(encoding="utf-8"))
        if before["messages"][0]["content"] != prompt("validation") or before["messages"][2]["content"] != prompt("validation-grounding"):
            raise RuntimeError("frozen_complete_system_messages_changed")
        if OutcomeReview.model_json_schema() not in (before["schema"], candidate):
            raise RuntimeError("current_product_schema_not_old_or_planned_candidate")
        audit = schema_audit(before["schema"], candidate)
        current = deepcopy(before)
        current["schema"] = deepcopy(candidate)
        if {k: v for k, v in before.items() if k != "schema"} != {k: v for k, v in current.items() if k != "schema"}:
            raise RuntimeError("schema_only_preparation_changed_messages_or_other_fields")
        estimate = input_estimate(current["messages"], [current["schema"]])
        if estimate > 16000:
            raise RuntimeError("input_budget_exceeded_zero_HTTP")
        destination = private / target["test_id"] / "prepared-request-before-paid-call.json"
        write(destination, current)
        metadata["targets"].append({"test_id": target["test_id"], "expected_supported": target["expected_supported"],
            "prepared_file": str(destination.relative_to(ROOT)).replace("\\", "/"), "prepared_file_sha256": digest(destination.read_bytes()),
            "prepared_request_sha256": digest(json_bytes(current)), "original_schema_sha256": digest(json_bytes(before["schema"])),
            "candidate_schema_sha256": digest(json_bytes(candidate)), "schema_audit": audit, "only_changed_field": "schema",
            "messages_full_unchanged": True, "complete_user_data_unchanged": True,
            "full_messages_sha256": digest(json_bytes(current["messages"])), "input_proxy": estimate,
            "original_input_proxy": target["input_proxy"], "original_synthetic_variant": target["synthetic_variant"]})
    metadata["reserved_tokens_for_two_future_controls"] = sum(t["input_proxy"] + 2000 for t in metadata["targets"])
    metadata["code_snapshot_after"] = code_snapshot()
    metadata["source_changed_during_preparation"] = metadata["code_snapshot"] != metadata["code_snapshot_after"]
    if metadata["source_changed_during_preparation"] or metadata["reserved_tokens_for_two_future_controls"] > 80000:
        raise RuntimeError("candidate_source_or_original_budget_changed")
    write(private / "manifest-planned-zero-http.json", metadata)
    print(json.dumps({"attempt": attempt, "status": metadata["status"], "new_model_http_calls": 0,
        "trusted_files": len(trusted), "targets": [{"test": t["test_id"], "input_proxy": t["input_proxy"]} for t in metadata["targets"]]}))


if __name__ == "__main__":
    main()
