"""Zero HTTP experiment: only losslessly decode observation content, no Graph deployment."""
from copy import deepcopy
import json
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4
from pydantic import SecretStr
from bootstrap import ROOT, digest, json_bytes, provider_sampling, write
from review_observations import original_observations, parsed_observations
from globalmail_agent.knowledge.base import canonical


def main():
    from globalmail_agent.adapters.model_provider import ModelProvider, prompt
    from globalmail_agent.agent.outcome_validation import OutcomeReview
    from globalmail_agent.agent.review_audit import audit_sources
    from globalmail_agent.agent.budget import input_estimate
    from run_eval import code_snapshot
    prior_path = ROOT / "tmp/phase7-agent-eval/20261008-230632-1305d8d9/manifest-planned-zero-http.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    for relative, expected in prior["trusted_file_sha256"].items():
        if digest((ROOT / relative).read_bytes()) != expected:
            raise RuntimeError("observation_prior_source_changed_zero_HTTP")
    metadata = deepcopy(prior)
    attempt = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    directory = ROOT / "tmp/phase7-agent-eval" / attempt
    metadata.update(attempt_id=attempt, status="parsed_observations_experiment_prepared_zero_HTTP_not_quality",
        scope="eval_presentation_prototype_not_current_Graph_not_business_cycle",
        prior_contract_preparation_id=prior["attempt_id"], prior_contract_negative_manual_FAIL_id="20261008-230652-194e6b3f",
        new_actual_sampling=provider_sampling(), code_snapshot=code_snapshot(),
        changed_fields=["messages[1].content observations[].content JSON string to full object"],
        Graph_has_not_adopted_experimental_representation=True, new_model_http_calls=0)
    negative = ROOT / "tmp/phase7-agent-eval/20261008-230652-194e6b3f/unsupported_product_and_missing_conditional_original"
    files = [prior_path, negative.parent / "result.json"]
    files += [negative / name for name in ("request-01.json", "response-01.json", "provider-payload-01.json")]
    metadata["trusted_file_sha256"].update({str(p.relative_to(ROOT)).replace("\\", "/"): digest(p.read_bytes()) for p in files})
    for target in metadata["targets"]:
        before = json.loads((ROOT / target["prepared_file"]).read_text(encoding="utf-8"))
        current = deepcopy(before)
        data = json.loads(before["messages"][1]["content"])
        original = deepcopy(data)
        data["observations"] = parsed_observations(data["observations"])
        restored = deepcopy(data)
        restored["observations"] = original_observations(restored["observations"])
        assert restored == original and canonical(restored).decode() == before["messages"][1]["content"]
        original_sources = audit_sources(original["context"], original["observations"])
        restored_sources = audit_sources(restored["context"], restored["observations"])
        assert original_sources == restored_sources
        current["messages"][1]["content"] = canonical(data).decode()
        assert current["messages"][0]["content"] == prompt("validation")
        assert current["messages"][2]["content"] == prompt("validation-grounding")
        assert current["schema"] == OutcomeReview.model_json_schema()
        estimate = input_estimate(current["messages"], [current["schema"]])
        if estimate > 16000:
            raise RuntimeError("observation_full_input_exceeds_16k_zero_HTTP")
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
        planned["messages"] = current["messages"]
        assert payload == planned
        path = directory / target["test_id"] / "prepared-request.json"
        sdk_path = directory / target["test_id"] / "prepared-SDK-payload.json"
        write(path, current)
        write(sdk_path, payload)
        target.update(prepared_file=str(path.relative_to(ROOT)).replace("\\", "/"),
            prepared_file_sha256=digest(path.read_bytes()), prepared_request_sha256=digest(json_bytes(current)),
            prepared_SDK_file=str(sdk_path.relative_to(ROOT)).replace("\\", "/"),
            prepared_SDK_file_sha256=digest(sdk_path.read_bytes()), input_proxy=estimate, input_headroom=16000 - estimate,
            complete_roundtrip_original_DATA_raw_bytes_equal=True,
            original_canonical_source_body_sha256={key: digest(value.encode()) for key, value in original_sources.items()})
    metadata["original_budget_preflight"] = {"input_proxies": [t["input_proxy"] for t in metadata["targets"]],
        "reserved_tokens_for_both": sum(t["input_proxy"] + 2000 for t in metadata["targets"]),
        "model_requests": 2, "tools": 0, "budget_or_material_limits_changed": False}
    metadata["reserved_tokens_for_two_future_controls"] = metadata["original_budget_preflight"]["reserved_tokens_for_both"]
    metadata["code_snapshot_after"] = code_snapshot()
    metadata["source_changed_during_preparation"] = metadata["code_snapshot_after"] != metadata["code_snapshot"]
    assert not metadata["source_changed_during_preparation"]
    write(directory / "manifest-planned-zero-http.json", metadata)
    write(ROOT / "docs/verification/artifacts/phase7/review-observation-preparation.json", metadata)
    print(json.dumps({"preparation": attempt, "HTTP": 0, "input": metadata["original_budget_preflight"]["input_proxies"]}))


if __name__ == "__main__":
    main()
