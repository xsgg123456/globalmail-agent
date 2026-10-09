"""Record actual ModelProvider traffic privately; no fake responses or extra requests."""
from copy import deepcopy
import json
import time
import traceback
from bootstrap import digest, json_bytes, write


def instrument(model, directory):
    original = model.request
    requests = []
    provider = model
    while hasattr(provider, "real"):
        provider = provider.real
    if hasattr(provider, "client"):
        original_options = provider.client.with_options
        def observed_options(**options):
            client = original_options(**options)
            create = client.chat.completions.create
            def observed_create(**payload):
                allowed = {"model", "messages", "max_tokens", "max_completion_tokens", "temperature", "extra_body", "top_p",
                    "response_format", "tools", "tool_choice", "parallel_tool_calls"}
                captured = {k: deepcopy(v) for k, v in payload.items() if k in allowed}
                index = len(requests)
                write(directory / f"provider-payload-{index:02}.json", captured)
                if requests:
                    requests[-1]["actual_provider_tool_choice"] = captured.get("tool_choice")
                    requests[-1]["actual_provider_sampling"] = {"temperature": captured.get("temperature"),
                        "enable_thinking": captured.get("extra_body", {}).get("enable_thinking"),
                        "thinking_budget": captured.get("extra_body", {}).get("thinking_budget"),
                        "max_tokens": captured.get("max_tokens"),
                        "max_completion_tokens": captured.get("max_completion_tokens"),
                        "top_p": captured.get("top_p", "server_default")}
                return create(**payload)
            client.chat.completions.create = observed_create
            return client
        provider.client.with_options = observed_options

    def actual(messages, *, schema=None, tools=None, timeout=30):
        index = len(requests) + 1
        item = {"messages": deepcopy(messages), "schema": schema, "tools": tools, "timeout": timeout}
        requests.append(item)
        write(directory / f"request-{index:02}.json", item)
        started = time.monotonic()
        previous_http_count = getattr(model, "new_http_calls", None)
        try:
            response = original(messages, schema=schema, tools=tools, timeout=timeout)
            write(directory / f"response-{index:02}.json", response)
            item["response"] = response
            return response
        except Exception as error:
            item["error"] = getattr(error, "code", type(error).__name__)
            write(directory / f"response-{index:02}.json", {"error_code": item["error"]})
            raise
        finally:
            item["seconds"] = round(time.monotonic() - started, 3)
            item["new_http_call"] = (model.new_http_calls > previous_http_count
                if previous_http_count is not None else True)

    model.request = actual
    return requests


def capture_graph_errors(directory):
    """Keep exception class/frames only; rethrow unchanged before Runner handles it."""
    from globalmail_agent.agent.graph import AgentGraph
    original = AgentGraph.invoke
    def invoke(graph):
        try:
            return original(graph)
        except Exception as error:
            frames = [{"file": f.filename.replace("\\", "/").split("/globalmail-agent/")[-1],
                "line": f.lineno, "function": f.name} for f in traceback.extract_tb(error.__traceback__)]
            write(directory / "graph-error.json", {"type": type(error).__name__,
                "code": getattr(error, "code", None), "frames": frames[-20:]})
            if getattr(error, "code", None) == "input_budget_exceeded":
                trace = error.__traceback__
                while trace:
                    frame = trace.tb_frame
                    if frame.f_code.co_name == "request" and frame.f_globals.get("__name__") == "globalmail_agent.agent.graph":
                        local = frame.f_locals
                        write(directory / "blocked-next-request.json", {
                            "provenance": "actual_graph_request_locals_at_budget_rejection_before_model_http",
                            "messages": local["messages"], "schema": local.get("schema"), "tools": local.get("tools"),
                            "stage": local["stage"], "new_model_http_call": False})
                        break
                    trace = trace.tb_next
            raise
    AgentGraph.invoke = invoke
    return lambda: setattr(AgentGraph, "invoke", original)


def source_scope(requests):
    if not requests:
        return {"messages": [], "human_notes": [], "model_requests": []}
    raw = json.loads(requests[0]["messages"][1]["content"])
    return {"mode": raw["mode"], "as_of": raw["as_of"], "trigger_message_id": raw["trigger_message_id"],
        "case_revision": raw["case_revision"], "case_fact_count": len(raw["case_facts"]),
        "messages": [{"message_id": m["message_id"], "seq": m["seq"], "sender": m["sender"],
            "body_sha256": digest(m["body"].encode()), "body_chars": len(m["body"])} for m in raw["messages"]],
        "human_notes": [{"message_id": m["message_id"], "body_sha256": digest(m["body"].encode())}
            for m in raw["human_notes"]],
        "model_requests": [{"index": n + 1, "input_sha256": digest(json_bytes({k: r[k]
            for k in ("messages", "schema", "tools", "timeout")})), "seconds": r["seconds"],
            "system_prompt_sha256": [digest(m["content"].encode()) for m in r["messages"]
                if m["role"] == "system" and isinstance(m.get("content"), str)],
            "provider_request_id": r.get("response", {}).get("request_id"),
            "actual_provider_tool_choice": r.get("actual_provider_tool_choice"),
            "actual_provider_sampling": r.get("actual_provider_sampling"),
            "provenance": r.get("response", {}).get("_eval_provenance", {"kind": "new_actual_http"
                if r.get("new_http_call", True) else "failed_before_new_http", "new_http_call": r.get("new_http_call", True)}),
            "usage": r.get("response", {}).get("usage"), "error": r.get("error")}
            for n, r in enumerate(requests)]}


def safe_arguments(name, args):
    if name == "create_reply_draft":
        return {"language": args.get("language"), "waiting_for": args.get("waiting_for"),
            "body_present_in_persisted_arguments": "body" in args,
            "body_sha256": digest(args["body"].encode()) if "body" in args else None, "citation_ids": args.get("citation_ids", []),
            "claims": [{"kind": c["kind"], "source_ids": c["source_ids"], "text_sha256": digest(c["text"].encode())}
                for c in args.get("claims", [])]}
    if name == "request_human_review":
        return {"reason": args.get("reason"), "summary_sha256": digest(args.get("summary", "").encode()),
            "gap_count": len(args.get("gaps", [])), "draft_sha256": digest(args.get("draft", "").encode())}
    if name == "update_case_state":
        return {"arguments_sha256": digest(json_bytes(args))}
    if name in {"get_case_context", "get_order_snapshot", "get_shipment_status", "get_after_sales_context",
            "get_operation_status", "get_item_availability", "search_reference"}:
        return args
    # New revision tools may contain source quotes/free text; opt in read-only fields explicitly.
    return {"arguments_sha256": digest(json_bytes(args))}


def summarize(record, requests, before, after, elapsed, case):
    from draft_lineage import draft_lineage
    understanding = record["understanding"] or {}
    body = "\n".join(a["body"] for a in record["artifacts"])
    source = source_scope(requests)
    tools = [{"name": t["name"], "arguments": safe_arguments(t["name"], t["arguments"]), "status": t["status"],
        "reason_code": t["reason_code"]} for t in record["tools"]]
    refs = [{"evidence_id": r["reference"]["evidence_id"], "title": r["reference"]["title"],
        "version_number": r["reference"]["version_number"], "source_sha256": r["reference"]["source_sha256"],
        "content_hash": r["reference"]["content_hash"], "section": r["reference"]["section"],
        "source_kind": r["reference"]["source_kind"], "eligible": r["eligible"], "reason": r["reason"]}
        for r in record["references"]]
    expected = case["expect"]
    status = record["run"]["status"]
    allowed = expected["status"] if isinstance(expected["status"], list) else [expected["status"]]
    checks = {"status": status in allowed, "at_most_one_outbound": after - before <= 1,
        "expected_tools": all(t in [v["name"] for v in tools] for t in expected.get("tools", [])),
        "schema_saved": bool(understanding), "within_original_budget": record["usage"]["model_requests"] <= 6
            and record["usage"]["tool_calls"] <= 12 and record["usage"]["active_ms"] <= 120000,
        "all_references_eligible": all(r["eligible"] for r in refs)}
    if "outbound_delta" in expected:
        checks["outbound_delta"] = after - before == expected["outbound_delta"]
    if expected.get("must_cite_knowledge"):
        checks["knowledge_registered"] = bool(refs)
    if expected.get("must_include_human_input"):
        checks["human_reply_and_note_in_model_input"] = bool(source["human_notes"]) and any(
            m["sender"] == "simulated_human" for m in source["messages"])
    if expected.get("intents"):
        checks["intent_objects_retained"] = set(expected["intents"]) <= {i["business_type"] for i in understanding.get("intents", [])}
    if expected.get("conditional_refund"):
        checks["refund_not_immediate"] = any(i["business_type"] == "refund" and i["consent"] == "conditional"
            and i["condition"] for i in understanding.get("intents", []))
    if expected.get("empty_knowledge"):
        checks["empty_applicable_knowledge"] = not refs and any(t["name"] == "search_reference"
            and t["status"] == "empty" for t in tools)
    if expected.get("product_steps") is False:
        checks["no_declared_product_steps"] = not any(c["kind"] == "product_step"
            for t in tools if t["name"] == "create_reply_draft" for c in t["arguments"].get("claims", []))
    if expected.get("foreign_order_denied"):
        foreign = expected["foreign_order_denied"]
        checks["foreign_order_never_returned"] = all(t["status"] == "denied" and not t["result"].get("data")
            for t in record["tools"] if t["name"] == "get_order_snapshot"
            and t["arguments"]["display_order_number"] == foreign)
    return {"case_id": case["case_id"], "scenario": case.get("scenario", "BASE-OUTON-02"),
        "run_id": str(record["run"]["id"]), "trace_id": record["trace_id"], "status": status,
        "error_code": record["run"]["error_code"], "source_scope": source,
        "tools": tools, "draft_body_lineage": draft_lineage(record, requests), "references": refs, "outbound_before": before, "outbound_after": after,
        "outbound_delta": after - before, "reply_sha256": digest(body.encode()) if body else None,
        "reply_chars": len(body), "understanding_language": understanding.get("language"),
        "intents": [{"business_type": i["business_type"], "order_number": i["order_number"],
            "consent": i["consent"], "conditional": bool(i["condition"]), "target_item": i["target_item"]}
            for i in understanding.get("intents", [])],
        "usage": record["usage"], "seconds": round(elapsed, 3), "structural_checks": checks,
        "business_human_review": {"status": "pending", "scope": "read_materials / business_rules / schema separate; original raw replies in ignored tmp"}}
