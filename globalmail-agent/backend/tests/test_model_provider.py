"""Capture actual OpenAI SDK arguments without network or real credentials."""
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import Mock, patch
from pydantic import SecretStr
from globalmail_agent.adapters.model_provider import ModelProvider
from globalmail_agent.agent.tool_schemas import schemas


class ModelProviderTests(TestCase):
    def provider(self):
        response = SimpleNamespace(id="protocol-response", usage=Mock(), choices=[SimpleNamespace(
            finish_reason="tool_calls", message=SimpleNamespace(content=None, tool_calls=[]))])
        response.usage.model_dump.return_value = {"prompt_tokens": 21, "completion_tokens": 9}
        client = Mock()
        client.with_options.return_value.chat.completions.create.return_value = response
        settings = SimpleNamespace(model_name="qwen3.7-plus", model_api_key=SecretStr("protocol-test-placeholder"),
            model_base_url="https://example.test/v1")
        with patch("globalmail_agent.adapters.model_provider.OpenAI", return_value=client) as sdk:
            model = ModelProvider(settings)
        self.assertEqual(sdk.call_args.kwargs["max_retries"], 0)
        return model, client, response

    def test_single_tool_names_the_allowed_function_in_actual_sdk_request(self):
        model, client, response = self.provider()
        tools = schemas({"request_human_review"})
        messages = [{"role": "user", "content": "Complete input is retained."}]
        output = model.request(messages, tools=tools, timeout=12)
        options = client.with_options.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(options["tool_choice"], {"type": "function", "function": {"name": "request_human_review"}})
        self.assertEqual(options["messages"], messages)
        self.assertEqual(options["tools"], tools)
        self.assertEqual(options["max_tokens"], 2000)
        self.assertEqual(options["temperature"], 0.7)
        self.assertEqual(options["extra_body"], {"enable_thinking": False})
        self.assertFalse(options["parallel_tool_calls"])
        client.with_options.assert_called_once_with(timeout=12)
        self.assertEqual(output["usage"], {"prompt_tokens": 21, "completion_tokens": 9})

    def test_multiple_tools_keep_dynamic_choice_with_supported_auto_protocol(self):
        model, client, _ = self.provider()
        tools = schemas({"get_order_snapshot", "request_human_review"})
        model.request([], tools=tools)
        options = client.with_options.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(options["tool_choice"], "auto")
        self.assertEqual(options["tools"], tools)
        self.assertFalse(options["parallel_tool_calls"])

    def test_schema_request_does_not_add_a_tool_selection(self):
        model, client, _ = self.provider()
        schema = {"type": "object", "properties": {}}
        model.request([], schema=schema)
        options = client.with_options.return_value.chat.completions.create.call_args.kwargs
        self.assertNotIn("tool_choice", options)
        self.assertNotIn("tools", options)
        self.assertEqual(options["response_format"]["json_schema"]["schema"], schema)

    def test_unknown_usage_remains_unknown_in_normalized_tool_response(self):
        model, client, response = self.provider()
        response.usage = None
        response.choices[0].message.tool_calls = [SimpleNamespace(id="call-one", function=SimpleNamespace(
            name="request_human_review", arguments='{"reason":"cannot_decide"}'))]
        output = model.request([], tools=schemas({"request_human_review"}))
        self.assertIsNone(output["usage"])
        self.assertEqual(output["calls"], [{"id": "call-one", "name": "request_human_review",
            "arguments": '{"reason":"cannot_decide"}'}])

    def test_only_outcome_review_uses_bounded_thinking_and_preserves_full_input(self):
        from globalmail_agent.agent.outcome_validation import OutcomeReview
        model, client, response = self.provider()
        response.choices[0].message.reasoning_content = "Private provider reasoning."
        usage = {"prompt_tokens": 1200, "completion_tokens": 850,
            "completion_tokens_details": {"reasoning_tokens": 512}}
        response.usage.model_dump.return_value = usage
        messages = [{"role": "user", "content": "Full original customer and source material."}]
        schema = OutcomeReview.model_json_schema()
        output = model.request(messages, schema=schema, timeout=9)
        options = client.with_options.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(options["messages"], messages)
        self.assertEqual(options["response_format"]["json_schema"]["schema"], schema)
        self.assertEqual(options["extra_body"], {"enable_thinking": True, "thinking_budget": 2048})
        self.assertEqual(options["max_completion_tokens"], 3990)
        self.assertNotIn("max_tokens", options)
        self.assertNotIn("tools", options)
        self.assertEqual(options["temperature"], 0.7)
        client.with_options.assert_called_once_with(timeout=9)
        self.assertEqual(output["usage"], usage)
        self.assertEqual(output["reasoning_content"], "Private provider reasoning.")

    def test_understanding_after_review_still_uses_non_thinking_profile(self):
        from globalmail_agent.agent.outcome_validation import OutcomeReview
        from globalmail_agent.agent.understanding import Understanding
        model, client, _ = self.provider()
        model.request([], schema=OutcomeReview.model_json_schema())
        model.request([], schema=Understanding.model_json_schema())
        options = client.with_options.return_value.chat.completions.create.call_args.kwargs
        self.assertEqual(options["extra_body"], {"enable_thinking": False})
        self.assertEqual(options["max_tokens"], 2000)
        self.assertNotIn("max_completion_tokens", options)
