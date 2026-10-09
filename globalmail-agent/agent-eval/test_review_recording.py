"""Zero HTTP: validation limits and reasoning-inclusive usage survive private capture."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from pydantic import SecretStr
from bootstrap import provider_sampling
from recording import instrument
from globalmail_agent.adapters.model_provider import ModelProvider
from globalmail_agent.agent.outcome_validation import OutcomeReview


class ReviewRecordingTests(TestCase):
    def test_private_sdk_capture_has_total_cap_and_stage_specific_sampling(self):
        usage = {"prompt_tokens": 1000, "completion_tokens": 900,
            "completion_tokens_details": {"reasoning_tokens": 512}}
        response = SimpleNamespace(id="test", usage=Mock(), choices=[SimpleNamespace(
            finish_reason="stop", message=SimpleNamespace(content="{}", tool_calls=[], reasoning_content="test"))])
        response.usage.model_dump.return_value = usage
        client = Mock()
        client.with_options.return_value.chat.completions.create.return_value = response
        settings = SimpleNamespace(model_name="qwen3.7-plus", model_api_key=SecretStr("unit-placeholder"),
            model_base_url="https://example.test/v1")
        with patch("globalmail_agent.adapters.model_provider.OpenAI", return_value=client):
            model = ModelProvider(settings)
        with TemporaryDirectory() as folder:
            path = Path(folder)
            traffic = instrument(model, path)
            model.request([{"role": "user", "content": "Complete input."}], schema=OutcomeReview.model_json_schema())
            actual = json.loads((path / "provider-payload-01.json").read_text(encoding="utf-8"))
            self.assertEqual(actual["max_completion_tokens"], 3990)
            self.assertNotIn("max_tokens", actual)
            self.assertEqual(actual["extra_body"], {"enable_thinking": True, "thinking_budget": 2048})
            self.assertEqual(traffic[0]["actual_provider_sampling"]["max_completion_tokens"], 3990)
            self.assertEqual(traffic[0]["response"]["usage"], usage)
            self.assertEqual(traffic[0]["response"]["reasoning_content"], "test")
        sampling = provider_sampling()
        self.assertFalse(sampling["enable_thinking"])
        self.assertEqual(sampling["validation_profile"], {"temperature": 0.7, "enable_thinking": True,
            "thinking_budget": 2048, "max_completion_tokens": 3990, "top_p": "server_default"})
