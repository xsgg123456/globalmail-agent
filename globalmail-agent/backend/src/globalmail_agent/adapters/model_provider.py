"""Fixed Qwen chat/JSON/tool adapter; network attempts are individually budgeted."""
import json
from pathlib import Path
from openai import OpenAI, APIConnectionError, APITimeoutError, APIStatusError
from globalmail_agent.application.conversation_lock import ServiceError

PROMPTS = Path(__file__).resolve().parents[1] / "agent" / "prompts"
VALIDATION_OPTIONS = {"max_completion_tokens": 3990,
    "extra_body": {"enable_thinking": True, "thinking_budget": 2048}}


class ModelProvider:
    def __init__(self, settings):
        self.model = settings.model_name
        self.configured = bool(settings.model_api_key.get_secret_value() and settings.model_base_url
            and self.model == "qwen3.7-plus")
        self.client = OpenAI(api_key=settings.model_api_key.get_secret_value() or "unconfigured",
            base_url=settings.model_base_url or "http://127.0.0.1:1", timeout=30, max_retries=0)

    def request(self, messages, *, schema=None, tools=None, timeout=30):
        if not self.configured:
            raise ServiceError("model_not_configured", 503)
        options = {"model": self.model, "messages": messages, "max_tokens": 2000,
            "temperature": 0.7, "extra_body": {"enable_thinking": False}}
        if schema and schema.get("title") == "OutcomeReview" and not tools:
            options.pop("max_tokens")
            options.update(max_completion_tokens=VALIDATION_OPTIONS["max_completion_tokens"],
                extra_body=dict(VALIDATION_OPTIONS["extra_body"]))
        if schema:
            options["response_format"] = {"type": "json_schema", "json_schema":
                {"name": "mail_understanding", "strict": True, "schema": schema}}
        if tools:
            choice = {"type": "function", "function": {"name": tools[0]["function"]["name"]}} \
                if len(tools) == 1 else "auto"
            options.update(tools=tools, tool_choice=choice, parallel_tool_calls=False)
        try:
            response = self.client.with_options(timeout=timeout).chat.completions.create(**options)
            choice = response.choices[0]
            usage = response.usage.model_dump() if response.usage else None
            output = {"usage": usage, "request_id": response.id, "finish_reason": choice.finish_reason,
                "content": choice.message.content or "", "calls": []}
            output["reasoning_content"] = getattr(choice.message, "reasoning_content", None)
            for call in choice.message.tool_calls or []:
                output["calls"].append({"id": call.id, "name": call.function.name,
                    "arguments": call.function.arguments})
            return output
        except (APITimeoutError, APIConnectionError):
            raise ServiceError("model_timeout", 503) from None
        except APIStatusError as error:
            code = "model_authentication" if error.status_code in {401, 403} else (
                "model_rate_limited" if error.status_code == 429 else
                "model_unavailable" if error.status_code >= 500 else "model_configuration_error")
            raise ServiceError(code, 503) from None


def prompt(name):
    return (PROMPTS / (name + ".md")).read_text(encoding="utf-8")
