"""Zero HTTP: freeze the authorized validation profile with both original full requests."""
from copy import deepcopy
import json
import sys
import time
from types import SimpleNamespace
from unittest.mock import Mock, patch
from uuid import uuid4
from pydantic import SecretStr
from bootstrap import ROOT, BACKEND, digest, frozen_inputs, provider_sampling, write

PRIOR = "20261008-212036-809e5d7f"


def main():
    from globalmail_agent.adapters.model_provider import ModelProvider, prompt
    from globalmail_agent.agent.outcome_validation import OutcomeReview
    from globalmail_agent.agent.budget import input_estimate
    from run_eval import code_snapshot
    if sys.prefix.lower() != str(BACKEND / ".venv").lower():
        raise RuntimeError("use_fixed_backend_venv")
    prior_path = ROOT / "tmp/phase7-agent-eval" / PRIOR / "manifest-planned-zero-http.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    for relative, expected in prior["trusted_file_sha256"].items():
        if digest((ROOT / relative).read_bytes()) != expected:
            raise RuntimeError("thinking_control_original_source_changed_zero_HTTP")
    _, freeze = frozen_inputs()
    if freeze != prior["freeze"]:
        raise RuntimeError("thinking_control_frozen_cases_or_SOP_changed_zero_HTTP")
    attempt = time.strftime("%Y%m%d-%H%M%S") + "-" + uuid4().hex[:8]
    directory = ROOT / "tmp/phase7-agent-eval" / attempt
    metadata = deepcopy(prior)
    metadata.update(attempt_id=attempt, status="authorized_review_thinking_prepared_zero_HTTP_not_quality",
        prior_item_audit_preparation_id=PRIOR, code_snapshot=code_snapshot(),
        new_actual_sampling=provider_sampling(), new_model_http_calls=0,
        authorization="User requested proceeding with the presented proposal and completing Phase7.")
    metadata["trusted_file_sha256"][str(prior_path.relative_to(ROOT)).replace("\\", "/")] = digest(prior_path.read_bytes())
    for target in metadata["targets"]:
        source = ROOT / target["prepared_file"]
        request = json.loads(source.read_text(encoding="utf-8"))
        if digest(source.read_bytes()) != target["prepared_file_sha256"] or (
                request["schema"] != OutcomeReview.model_json_schema() or request["tools"] is not None or
                request["messages"][0]["content"] != prompt("validation") or
                request["messages"][2]["content"] != prompt("validation-grounding") or
                input_estimate(request["messages"], [request["schema"]]) != target["input_proxy"]):
            raise RuntimeError("thinking_control_full_request_contract_changed_zero_HTTP")
        client = Mock()
        client.with_options.return_value.chat.completions.create.return_value = SimpleNamespace(
            id="zero-http-payload-capture", usage=None, choices=[SimpleNamespace(finish_reason="stop",
                message=SimpleNamespace(content="{}", tool_calls=[]))])
        settings = SimpleNamespace(model_name="qwen3.7-plus", model_api_key=SecretStr("offline-placeholder"),
            model_base_url="https://example.test/v1")
        with patch("globalmail_agent.adapters.model_provider.OpenAI", return_value=client):
            model = ModelProvider(settings)
        model.request(**request)
        payload = client.with_options.return_value.chat.completions.create.call_args.kwargs
        planned_path = ROOT / "tmp/phase7-agent-eval/planned-review-thinking-512" / target["test_id"] / "planned-SDK-payload.json"
        if payload != json.loads(planned_path.read_text(encoding="utf-8")):
            raise RuntimeError("thinking_actual_adapter_differs_from_approved_proposal_zero_HTTP")
        destination = directory / target["test_id"] / "planned-SDK-payload.json"
        write(destination, payload)
        target.update(prepared_SDK_file=str(destination.relative_to(ROOT)).replace("\\", "/"),
            prepared_SDK_file_sha256=digest(destination.read_bytes()))
        metadata["trusted_file_sha256"][str(source.relative_to(ROOT)).replace("\\", "/")] = digest(source.read_bytes())
    metadata["code_snapshot_after"] = code_snapshot()
    metadata["source_changed_during_preparation"] = metadata["code_snapshot"] != metadata["code_snapshot_after"]
    if metadata["source_changed_during_preparation"]:
        raise RuntimeError("thinking_preparation_code_changed_zero_HTTP")
    write(directory / "manifest-planned-zero-http.json", metadata)
    write(ROOT / "docs/verification/artifacts/phase7/review-thinking-authorized-preparation.json", metadata)
    print(json.dumps({"attempt": attempt, "new_model_HTTP": 0, "inputs": [t["input_proxy"] for t in metadata["targets"]],
        "trusted_files": len(metadata["trusted_file_sha256"]), "source_changed": False}))


if __name__ == "__main__":
    main()
