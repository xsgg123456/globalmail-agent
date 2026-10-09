"""Zero HTTP: change only review task order, retain every original data byte and limit."""
from copy import deepcopy
import json
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4
from pydantic import SecretStr
from bootstrap import ROOT, digest, json_bytes, provider_sampling, write


def main():
    from globalmail_agent.adapters.model_provider import ModelProvider, prompt
    from globalmail_agent.agent.outcome_validation import OutcomeReview
    from globalmail_agent.agent.budget import input_estimate
    from run_eval import code_snapshot
    prior_path = ROOT / "tmp/phase7-agent-eval/20261008-223750-f17bf3c6/manifest-planned-zero-http.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    for relative, expected in prior["trusted_file_sha256"].items():
        if digest((ROOT / relative).read_bytes()) != expected:
            raise RuntimeError("workflow_prior_source_changed_zero_HTTP")
    metadata = deepcopy(prior)
    attempt = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    directory = ROOT / "tmp/phase7-agent-eval" / attempt
    metadata.update(attempt_id=attempt, status="source_first_review_task_prepared_zero_HTTP_not_quality",
        prior_mode_preparation_id=prior["attempt_id"], prior_mode_negative_FAIL_id="20261008-224147-cf5c680c",
        new_actual_sampling=provider_sampling(), code_snapshot=code_snapshot(),
        changed_fields=["messages[0].content"], new_model_http_calls=0)
    files = [prior_path, ROOT / "tmp/phase7-agent-eval/20261008-224147-cf5c680c/result.json"]
    negative = ROOT / "tmp/phase7-agent-eval/20261008-224147-cf5c680c/unsupported_product_and_missing_conditional_original"
    files += [negative / name for name in ("request-01.json", "response-01.json", "provider-payload-01.json")]
    metadata["trusted_file_sha256"].update({str(p.relative_to(ROOT)).replace("\\", "/"): digest(p.read_bytes()) for p in files})
    head = prompt("validation")
    for target in metadata["targets"]:
        before_path = ROOT / target["prepared_file"]
        before = json.loads(before_path.read_text(encoding="utf-8"))
        original_head = before["messages"][0]["content"].split("\n\n")
        current_head = head.split("\n\n")
        if current_head[1:] != [original_head[2], original_head[1], *original_head[3:]]:
            raise RuntimeError("workflow_other_prompt_rules_changed_zero_HTTP")
        current = deepcopy(before)
        current["messages"][0]["content"] = head
        if current["schema"] != OutcomeReview.model_json_schema() or current["messages"][2]["content"] != prompt("validation-grounding"):
            raise RuntimeError("workflow_schema_or_tail_changed_zero_HTTP")
        estimate = input_estimate(current["messages"], [current["schema"]])
        if estimate > 16000:
            raise RuntimeError("workflow_full_input_exceeds_16k_zero_HTTP")
        client = Mock()
        client.with_options.return_value.chat.completions.create.return_value = SimpleNamespace(
            id="zero-http", usage=None, choices=[SimpleNamespace(finish_reason="stop",
                message=SimpleNamespace(content="{}", tool_calls=[]))])
        settings = SimpleNamespace(model_name="qwen3.7-plus", model_api_key=SecretStr("offline-placeholder"),
            model_base_url="https://example.test/v1")
        with patch("globalmail_agent.adapters.model_provider.OpenAI", return_value=client):
            model = ModelProvider(settings)
        model.request(**current)
        payload = client.with_options.return_value.chat.completions.create.call_args.kwargs
        previous_payload = json.loads((ROOT / target["prepared_SDK_file"]).read_text(encoding="utf-8"))
        previous_payload["messages"] = current["messages"]
        if payload != previous_payload:
            raise RuntimeError("workflow_SDK_changed_beyond_full_head_zero_HTTP")
        request_path = directory / target["test_id"] / "prepared-request-before-paid-call.json"
        SDK_path = request_path.parent / "planned-SDK-payload.json"
        write(request_path, current)
        write(SDK_path, payload)
        target.update(prepared_file=str(request_path.relative_to(ROOT)).replace("\\", "/"),
            prepared_file_sha256=digest(request_path.read_bytes()), prepared_request_sha256=digest(json_bytes(current)),
            prepared_SDK_file=str(SDK_path.relative_to(ROOT)).replace("\\", "/"),
            prepared_SDK_file_sha256=digest(SDK_path.read_bytes()), input_proxy=estimate,
            input_headroom=16000-estimate, all_non_head_fields_verbatim_unchanged=True,
            prior_prepared_request_raw_sha256=digest(before_path.read_bytes()))
    metadata["reserved_tokens_for_two_future_controls"] = sum(t["input_proxy"] + 2000 for t in metadata["targets"])
    metadata["system"]["head_sha256"] = digest(head.encode())
    metadata["code_snapshot_after"] = code_snapshot()
    metadata["source_changed_during_preparation"] = metadata["code_snapshot"] != metadata["code_snapshot_after"]
    if metadata["source_changed_during_preparation"] or metadata["reserved_tokens_for_two_future_controls"] > 80000:
        raise RuntimeError("workflow_source_or_budget_changed_zero_HTTP")
    write(directory / "manifest-planned-zero-http.json", metadata)
    write(ROOT / "docs/verification/artifacts/phase7/review-workflow-preparation.json", metadata)
    print(json.dumps({"attempt": attempt, "new_HTTP": 0, "inputs": [t["input_proxy"] for t in metadata["targets"]],
        "trusted_sources": len(metadata["trusted_file_sha256"]), "source_changed": False}))


if __name__ == "__main__":
    main()
