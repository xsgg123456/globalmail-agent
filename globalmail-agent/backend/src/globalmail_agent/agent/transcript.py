"""Keep complete observations while removing an equivalent terminal proposal echo."""
import json
from globalmail_agent.knowledge.base import canonical


def repair_history(messages):
    terminal = {call["id"]: call["function"]["name"] for message in messages if message["role"] == "assistant"
        for call in message.get("tool_calls", []) if call["function"]["name"] in
        {"create_reply_draft", "request_human_review"}}
    result = []
    for message in messages:
        if message["role"] == "assistant" and message.get("tool_calls"):
            remaining = [call for call in message["tool_calls"] if call["id"] not in terminal]
            if remaining:
                result.append({**message, "tool_calls": remaining})
        elif message["role"] == "tool" and message["tool_call_id"] in terminal:
            # The validated result includes every proposal field, including defaults. Keep it in full.
            result.append({"role": "user", "content": canonical({"rejected_terminal_result":
                json.loads(message["content"]), "tool_name": terminal[message["tool_call_id"]],
                "provider_tool_call_id": message["tool_call_id"]}).decode()})
        else:
            result.append(message)
    return result
