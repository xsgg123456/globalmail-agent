"""Zero HTTP: preserve both known contrasts while adopting the actual item-audit contract."""
from copy import deepcopy
import json
import sys
import time
from uuid import uuid4
from bootstrap import ROOT, BACKEND, digest, frozen_inputs, json_bytes, provider_sampling, write

PRIOR = "20261008-205035-42aa62d8"
FAIL = "20261008-205412-fa4c0ce9"
NEW_FIELDS = {"request_checks", "source_checks"}


def repair_positive_sources(payload):
    """An explicit synthetic source repair; never alter the old draft or materials."""
    repaired = deepcopy(payload)
    receipts = [json.loads(row['content']) for row in payload['observations']]
    shipment = next(row['command_source_id'] for row in receipts if row.get('data', {}).get('shipments'))
    order = next(row['command_source_id'] for row in receipts if row.get('data', {}).get('orders'))
    customer = payload['context']['trigger_message_id']
    claims = repaired['draft']['claims']
    if len(claims) != 4 or claims[0]['source_ids'] != [order] or (
            claims[2]['kind'] != 'clarification' or claims[2]['source_ids'] != []):
        raise RuntimeError('item_audit_positive_original_source_premise_changed')
    operations = [
        {'field': 'draft.claims[0].source_ids', 'before': [order], 'after': [order, shipment]},
        {'field': 'draft.claims[2].kind', 'before': 'clarification', 'after': 'order_fact'},
        {'field': 'draft.claims[2].source_ids', 'before': [], 'after': [shipment, customer]}]
    claims[0]['source_ids'] = [order, shipment]
    claims[2]['kind'], claims[2]['source_ids'] = 'order_fact', [shipment, customer]
    assert repaired['draft']['body'] == payload['draft']['body']
    assert [row['text'] for row in claims] == [row['text'] for row in payload['draft']['claims']]
    assert {k: v for k, v in repaired.items() if k != 'draft'} == {k: v for k, v in payload.items() if k != 'draft'}
    return repaired, operations


def prepare_request(before, schema, head, tail, *, positive_sources=False):
    from globalmail_agent.agent.review_audit import trigger_units
    from globalmail_agent.knowledge.base import canonical
    if [m["role"] for m in before["messages"]] != ["system", "user", "system"] or before["tools"] is not None:
        raise RuntimeError("item_audit_original_request_structure_changed")
    if before["messages"][2]["content"] != tail:
        raise RuntimeError("item_audit_tail_must_remain_verbatim")
    old_fields = set(before["schema"]["properties"])
    if old_fields != {"reason", "unsupported_claims", "supported", "language_correct"} or (
            set(schema["properties"]) != old_fields | NEW_FIELDS or
            set(schema["required"]) != old_fields | NEW_FIELDS or schema.get("additionalProperties") is not False):
        raise RuntimeError("item_audit_schema_not_required_current_contract")
    if schema["properties"]["reason"].get("maxLength") != 1500 or (
            schema["properties"]["unsupported_claims"].get("maxItems") != 20):
        raise RuntimeError("item_audit_original_bounds_changed")
    payload = json.loads(before["messages"][1]["content"])
    if "trigger_units" in payload:
        raise RuntimeError("item_audit_prior_DATA_already_has_units")
    units = trigger_units(payload["context"])
    trigger = next(row["body"] for row in payload["context"]["messages"]
        if row["message_id"] == payload["context"]["trigger_message_id"])
    if not units or "".join(units) != trigger:
        raise RuntimeError("item_audit_trigger_units_not_lossless")
    base, repairs = repair_positive_sources(payload) if positive_sources else (deepcopy(payload), [])
    expanded = {**base, "trigger_units": units}
    current = deepcopy(before)
    current["schema"] = deepcopy(schema)
    current["messages"][0]["content"] = head
    current["messages"][1]["content"] = canonical(expanded).decode()
    unchanged = {k: v for k, v in expanded.items() if k != "trigger_units"}
    if unchanged != base or {k: v for k, v in current.items() if k not in {"messages", "schema"}} != (
            {k: v for k, v in before.items() if k not in {"messages", "schema"}}):
        raise RuntimeError("item_audit_existing_DATA_or_request_field_changed")
    audit = {"changed_fields": ["schema", "messages[0].content", "messages[1].content.trigger_units",
        *["messages[1].content." + row['field'] for row in repairs]],
        "explicit_synthetic_positive_source_only_repairs": repairs,
        "all_non_draft_DATA_verbatim_values_unchanged": True,
        "draft_body_and_all_claim_texts_verbatim_unchanged": True,
        "original_user_sha256": digest(before["messages"][1]["content"].encode()),
        "original_DATA_sha256": digest(json_bytes(payload)), "existing_DATA_sha256": digest(json_bytes(unchanged)),
        "existing_DATA_fields": {k: {"equal": v == unchanged[k], "sha256": digest(json_bytes(v))} for k, v in payload.items()},
        "original_head": before["messages"][0]["content"], "current_head": head,
        "tail_verbatim_unchanged": True, "full_tail_sha256": digest(tail.encode()),
        "old_schema": before["schema"], "current_schema": schema,
        "old_required": before["schema"]["required"], "current_required": schema["required"],
        "trigger_message_id": payload["context"]["trigger_message_id"], "trigger_units": units,
        "trigger_units_join_sha256": digest("".join(units).encode()), "trigger_body_sha256": digest(trigger.encode()),
        "trigger_unit_count": len(units), "same_complete_trigger_body": True}
    return current, audit


def main():
    from globalmail_agent.adapters.model_provider import prompt
    from globalmail_agent.agent.budget import input_estimate
    from globalmail_agent.agent.outcome_validation import OutcomeReview
    from run_eval import code_snapshot
    if sys.prefix.lower() != str(BACKEND / ".venv").lower():
        raise RuntimeError("use_fixed_backend_venv")
    _, freeze = frozen_inputs()
    prior_dir = ROOT / "tmp/phase7-agent-eval" / PRIOR
    prior_path = prior_dir / "manifest-planned-zero-http.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    trusted = dict(prior["trusted_file_sha256"])
    for relative, expected in trusted.items():
        if digest((ROOT / relative).read_bytes()) != expected:
            raise RuntimeError("item_audit_prior_trusted_source_changed")
    failed = ROOT / "tmp/phase7-agent-eval" / FAIL
    files = [prior_path, *[ROOT / target["prepared_file"] for target in prior["targets"]]]
    files += [failed / "unsupported_product_and_missing_conditional_original" / name
        for name in ("request-01.json", "response-01.json", "provider-payload-01.json")]
    files += [failed / name for name in ("manifest-before-paid-calls.json", "manifest-before-negative-call.json",
        "result.json", "negative-semantic-review.json", "actual-schema-order-SDK-audit.json")]
    superseded = ROOT / 'tmp/phase7-agent-eval/20261008-211045-f459af6f'
    superseded_manifest = json.loads((superseded / 'manifest-planned-zero-http.json').read_text(encoding='utf-8'))
    files += [superseded / 'manifest-planned-zero-http.json', superseded / 'eval-selfcheck-zero-http.json']
    files += [ROOT / target[key] for target in superseded_manifest['targets']
        for key in ('prepared_file', 'complete_preparation_diff')]
    trusted.update({str(p.relative_to(ROOT)).replace("\\", "/"): digest(p.read_bytes()) for p in files})
    attempt = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    private = ROOT / "tmp/phase7-agent-eval" / attempt
    schema = OutcomeReview.model_json_schema()
    head, tail = prompt("validation"), prompt("validation-grounding")
    metadata = {"attempt_id": attempt, "status": "actual_item_audit_contract_prepared_zero_HTTP_not_quality",
        "scope": "standalone_item_audit_review_contrast_not_business_cycle", "origin_attempt": prior["origin_attempt"],
        "original_case": prior["original_case"], "prior_preparation_id": PRIOR, "actual_negative_FAIL_id": FAIL,
        "superseded_zero_HTTP_positive_source_gap_preparation": '20261008-211045-f459af6f',
        "original_quality_and_all_control_FAIL_preserved": True, "new_model_http_calls": 0,
        "business_commit": False, "business_outbound": 0, "original_cycle_request_count_changed": False,
        "trusted_file_sha256": trusted, "code_snapshot": code_snapshot(), "freeze": freeze,
        "new_actual_sampling": provider_sampling(), "runtime": prior["runtime"], "original_budget": prior["original_budget"],
        "review_contract": "required_request_checks_and_source_checks_v1", "targets": [],
        "system": {"head_sha256": digest(head.encode()), "tail_sha256": digest(tail.encode())},
        "quality_limit": "Original wrong understanding retained; synthetic positive is not fresh understanding or business PASS."}
    for target in prior["targets"]:
        before = json.loads((ROOT / target["prepared_file"]).read_text(encoding="utf-8"))
        current, audit = prepare_request(before, schema, head, tail, positive_sources=target['expected_supported'])
        estimate = input_estimate(current["messages"], [schema])
        if estimate > 16000:
            raise RuntimeError("item_audit_input_budget_exceeded_zero_HTTP")
        destination = private / target["test_id"] / "prepared-request-before-paid-call.json"
        write(destination, current)
        audit_path = destination.parent / "complete-preparation-diff.json"
        write(audit_path, audit)
        metadata["targets"].append({"test_id": target["test_id"], "expected_supported": target["expected_supported"],
            "prepared_file": str(destination.relative_to(ROOT)).replace("\\", "/"),
            "prepared_file_sha256": digest(destination.read_bytes()), "prepared_request_sha256": digest(json_bytes(current)),
            "schema_sha256": digest(json_bytes(schema)), "schema_order_sha256": digest(json.dumps(schema, ensure_ascii=False).encode()),
            "input_proxy": estimate, "input_headroom": 16000 - estimate, "original_input_proxy": target["input_proxy"],
            "complete_preparation_diff": str(audit_path.relative_to(ROOT)).replace("\\", "/"),
            "complete_preparation_diff_sha256": digest(audit_path.read_bytes()),
            "existing_DATA_sha256": audit["existing_DATA_sha256"], "trigger_unit_count": audit["trigger_unit_count"],
            "explicit_synthetic_positive_source_only_repairs": audit['explicit_synthetic_positive_source_only_repairs'],
            "synthetic_variant": target["original_synthetic_variant"]})
    metadata["reserved_tokens_for_two_future_controls"] = sum(t["input_proxy"] + 2000 for t in metadata["targets"])
    metadata["code_snapshot_after"] = code_snapshot()
    metadata["source_changed_during_preparation"] = metadata["code_snapshot"] != metadata["code_snapshot_after"]
    if metadata["source_changed_during_preparation"] or metadata["reserved_tokens_for_two_future_controls"] > 80000:
        raise RuntimeError("item_audit_source_or_budget_changed_zero_HTTP")
    write(private / "manifest-planned-zero-http.json", metadata)
    print(json.dumps({"attempt": attempt, "status": metadata["status"], "new_model_http_calls": 0,
        "trusted_files": len(trusted), "targets": [{"test": t["test_id"], "input_proxy": t["input_proxy"],
            "headroom": t["input_headroom"]} for t in metadata["targets"]]}))


if __name__ == "__main__":
    main()
