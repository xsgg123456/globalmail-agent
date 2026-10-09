"""Zero HTTP: align schema task order and field meanings without changing DATA or limits."""
from copy import deepcopy
import json
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4
from pydantic import SecretStr
from bootstrap import ROOT, digest, json_bytes, provider_sampling, write


def structural_schema(value):
    if isinstance(value, dict):
        return {key: sorted(item) if key == "required" else structural_schema(item)
            for key, item in value.items() if key != "description"}
    if isinstance(value, list):
        return [structural_schema(item) for item in value]
    return value


def main():
    from globalmail_agent.adapters.model_provider import ModelProvider, prompt
    from globalmail_agent.agent.outcome_validation import OutcomeReview
    from globalmail_agent.agent.budget import input_estimate
    from run_eval import code_snapshot
    prior_path = ROOT / "tmp/phase7-agent-eval/20261008-225009-b474db52/manifest-planned-zero-http.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    for relative, expected in prior["trusted_file_sha256"].items():
        if digest((ROOT / relative).read_bytes()) != expected:
            raise RuntimeError("contract_prior_source_changed_zero_HTTP")
    metadata = deepcopy(prior)
    attempt = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    directory = ROOT / "tmp/phase7-agent-eval" / attempt
    metadata.update(attempt_id=attempt, status="review_field_contract_prepared_zero_HTTP_not_quality",
        prior_workflow_preparation_id=prior["attempt_id"], prior_workflow_negative_manual_FAIL_id="20261008-225432-d2f20860",
        new_actual_sampling=provider_sampling(), code_snapshot=code_snapshot(),
        changed_fields=["schema property/required order", "three schema field descriptions"], new_model_http_calls=0)
    negative = ROOT / "tmp/phase7-agent-eval/20261008-225432-d2f20860/unsupported_product_and_missing_conditional_original"
    files = [prior_path, negative.parent / "result.json"]
    superseded = ROOT / "tmp/phase7-agent-eval/20261008-225934-25e32f19/manifest-planned-zero-http.json"
    files.append(superseded)
    metadata["superseded_zero_HTTP_metadata_preparation_id"] = "20261008-225934-25e32f19"
    files += [negative / name for name in ("request-01.json", "response-01.json", "provider-payload-01.json")]
    metadata["trusted_file_sha256"].update({str(p.relative_to(ROOT)).replace("\\", "/"): digest(p.read_bytes()) for p in files})
    schema = OutcomeReview.model_json_schema()
    assert list(schema["properties"]) == ["source_checks", "request_checks", "reason", "unsupported_claims", "supported", "language_correct"]
    for target in metadata["targets"]:
        before = json.loads((ROOT / target["prepared_file"]).read_text(encoding="utf-8"))
        assert structural_schema(before["schema"]) == structural_schema(schema)
        current = deepcopy(before)
        current["schema"] = schema
        assert current["messages"][0]["content"] == prompt("validation")
        assert current["messages"][2]["content"] == prompt("validation-grounding")
        estimate = input_estimate(current["messages"], [schema])
        if estimate > 16000:
            raise RuntimeError("contract_full_input_exceeds_16k_zero_HTTP")
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
        planned = json.loads((ROOT / target["prepared_SDK_file"]).read_text(encoding="utf-8"))
        planned["response_format"]["json_schema"]["schema"] = schema
        assert payload == planned
        path = directory / target["test_id"] / "prepared-request.json"
        sdk_path = directory / target["test_id"] / "prepared-SDK-payload.json"
        write(path, current)
        write(sdk_path, payload)
        target.update(prepared_file=str(path.relative_to(ROOT)).replace("\\", "/"),
            prepared_file_sha256=digest(path.read_bytes()), prepared_request_sha256=digest(json_bytes(current)),
            prepared_SDK_file=str(sdk_path.relative_to(ROOT)).replace("\\", "/"),
            prepared_SDK_file_sha256=digest(sdk_path.read_bytes()), input_proxy=estimate, input_headroom=16000 - estimate)
    metadata["original_budget_preflight"] = {"input_proxies": [t["input_proxy"] for t in metadata["targets"]],
        "reserved_tokens_for_both": sum(t["input_proxy"] + 2000 for t in metadata["targets"]),
        "model_requests": 2, "tools": 0, "budget_or_material_limits_changed": False}
    metadata["reserved_tokens_for_two_future_controls"] = metadata["original_budget_preflight"]["reserved_tokens_for_both"]
    metadata["code_snapshot_after"] = code_snapshot()
    metadata["source_changed_during_preparation"] = metadata["code_snapshot_after"] != metadata["code_snapshot"]
    assert not metadata["source_changed_during_preparation"]
    write(directory / "manifest-planned-zero-http.json", metadata)
    write(ROOT / "docs/verification/artifacts/phase7/review-contract-preparation.json", metadata)
    print(json.dumps({"preparation": attempt, "HTTP": 0, "input": metadata["original_budget_preflight"]["input_proxies"]}))


if __name__ == "__main__":
    main()
