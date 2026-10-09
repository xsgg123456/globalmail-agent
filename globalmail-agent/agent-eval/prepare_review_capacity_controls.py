"""Zero HTTP: current authorized profile with the prior full parsed controls."""
from copy import deepcopy
import json
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4
from pydantic import SecretStr
from bootstrap import ROOT, digest, write, json_bytes, provider_sampling
from globalmail_agent.adapters.model_provider import ModelProvider, prompt, VALIDATION_OPTIONS
from globalmail_agent.agent.budget import input_estimate, output_limit, network_timeout
from globalmail_agent.agent.outcome_validation import OutcomeReview
from globalmail_agent.agent.review_audit import audit_sources
from globalmail_agent.knowledge.base import canonical
from review_observations import original_observations
from run_eval import code_snapshot

PRIOR = "20261008-231517-bd82a595"
AUTHORIZED_LIMITS = {"validation_output": 4000, "validation_network_seconds": 60,
    "other_output": 2000, "other_network_seconds": 30, "cycle_requests": 6,
    "cycle_tools": 12, "cycle_active_ms": 120000, "input": 16000, "cycle_tokens": 80000}


def main():
    load = lambda path: json.loads(path.read_text(encoding="utf-8"))
    prior_path = ROOT / "tmp/phase7-agent-eval" / PRIOR / "manifest-planned-zero-http.json"
    prior = load(prior_path)
    for relative, expected in prior["trusted_file_sha256"].items():
        assert digest((ROOT / relative).read_bytes()) == expected
    assert VALIDATION_OPTIONS == {"max_completion_tokens": 3990,
        "extra_body": {"enable_thinking": True, "thinking_budget": 2048}}
    assert (output_limit("validation"), network_timeout("validation")) == (4000, 60)
    assert (output_limit("understanding"), network_timeout("decision")) == (2000, 30)
    attempt = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    directory = ROOT / "tmp/phase7-agent-eval" / attempt
    metadata = deepcopy(prior)
    metadata["prior_observation_original_budget_preflight"] = metadata.pop("original_budget_preflight")
    metadata.update(attempt_id=attempt, status="authorized_capacity_prepared_zero_HTTP",
        prior_observation_preparation_id=PRIOR, authorization="2026-10-09 user: 好的那你继续",
        authorized_stage_limits=AUTHORIZED_LIMITS, code_snapshot=code_snapshot(),
        new_actual_sampling=provider_sampling(), prior_observation_negative_FAIL_id="20261008-231655-cc7aba7c",
        changed_fields=["validation max_completion_tokens 1990 to 3990",
            "validation thinking_budget 512 to 2048", "validation timeout 30 to 60"],
        Graph_has_not_adopted_experimental_representation=True)
    metadata["trusted_file_sha256"][str(prior_path.relative_to(ROOT)).replace("\\", "/")] = digest(prior_path.read_bytes())
    for target in metadata["targets"]:
        old_path = ROOT / target["prepared_file"]
        old_sdk_path = ROOT / target["prepared_SDK_file"]
        assert digest(old_path.read_bytes()) == target["prepared_file_sha256"]
        assert digest(old_sdk_path.read_bytes()) == target["prepared_SDK_file_sha256"]
        for path in (old_path, old_sdk_path):
            metadata["trusted_file_sha256"][str(path.relative_to(ROOT)).replace("\\", "/")] = digest(path.read_bytes())
        original = load(old_path)
        current = deepcopy(original)
        current["timeout"] = network_timeout("validation")
        assert current["messages"][0]["content"] == prompt("validation")
        assert current["messages"][2]["content"] == prompt("validation-grounding")
        assert current["schema"] == OutcomeReview.model_json_schema()
        data = load_data = json.loads(current["messages"][1]["content"])
        restored = deepcopy(load_data)
        restored["observations"] = original_observations(restored["observations"])
        sources = audit_sources(restored["context"], restored["observations"])
        assert {key: digest(value.encode()) for key, value in sources.items()} == target["original_canonical_source_body_sha256"]
        assert data == json.loads(original["messages"][1]["content"])
        assert {k: v for k, v in current.items() if k != "timeout"} == {k: v for k, v in original.items() if k != "timeout"}
        client = Mock()
        client.with_options.return_value.chat.completions.create.return_value = SimpleNamespace(
            id="zero-http", usage=None, choices=[SimpleNamespace(finish_reason="stop",
                message=SimpleNamespace(content="{}", tool_calls=[]))])
        settings = SimpleNamespace(model_name="qwen3.7-plus", model_api_key=SecretStr("offline-placeholder"),
            model_base_url="https://example.test/v1")
        with patch("globalmail_agent.adapters.model_provider.OpenAI", return_value=client):
            model = ModelProvider(settings)
        model.request(**current)
        sdk = client.with_options.return_value.chat.completions.create.call_args.kwargs
        expected_sdk = load(old_sdk_path)
        expected_sdk.update(max_completion_tokens=3990,
            extra_body={"enable_thinking": True, "thinking_budget": 2048})
        assert sdk == expected_sdk and client.with_options.call_args.kwargs == {"timeout": 60}
        estimate = input_estimate(current["messages"], [current["schema"]])
        assert estimate == target["input_proxy"] and estimate <= 16000
        path, sdk_path = (directory / target["test_id"] / name for name in
            ("prepared-request.json", "prepared-SDK-payload.json"))
        write(path, current)
        write(sdk_path, sdk)
        target.update(prepared_file=str(path.relative_to(ROOT)).replace("\\", "/"),
            prepared_file_sha256=digest(path.read_bytes()), prepared_request_sha256=digest(json_bytes(current)),
            prepared_SDK_file=str(sdk_path.relative_to(ROOT)).replace("\\", "/"),
            prepared_SDK_file_sha256=digest(sdk_path.read_bytes()), input_headroom=16000-estimate)
    metadata["authorized_budget_preflight"] = {"input_proxies": [t["input_proxy"] for t in metadata["targets"]],
        "reserved_tokens_for_both": sum(t["input_proxy"] + 4000 for t in metadata["targets"]),
        "model_requests": 2, "tools": 0, "materials_changed": False}
    metadata["reserved_tokens_for_two_future_controls"] = metadata["authorized_budget_preflight"]["reserved_tokens_for_both"]
    assert metadata["reserved_tokens_for_two_future_controls"] == 38448
    metadata["code_snapshot_after"] = code_snapshot()
    metadata["source_changed_during_preparation"] = metadata["code_snapshot_after"] != metadata["code_snapshot"]
    assert not metadata["source_changed_during_preparation"]
    write(directory / "manifest-planned-zero-http.json", metadata)
    write(ROOT / "docs/verification/artifacts/phase7/review-capacity-preparation.json", metadata)
    print(json.dumps({"preparation": attempt, "HTTP": 0, "inputs": metadata["authorized_budget_preflight"]["input_proxies"]}))


if __name__ == "__main__":
    main()
