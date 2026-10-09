"""Replay four paid P7-02 responses; only the remaining requests reach the provider."""
from copy import deepcopy
import json
import time
from uuid import uuid4
from bootstrap import ROOT, digest


def load_prefix(attempt, case):
    if attempt == "20261008-182447-c623f2cd":
        from draft_prefix import load_draft_prefix
        return load_draft_prefix(attempt, case)
    base = (ROOT / "tmp/phase7-agent-eval").resolve()
    directory = (base / attempt / case["case_id"]).resolve()
    if not directory.is_relative_to(base) or case["case_id"] != "P7-02-order-and-evidence":
        raise RuntimeError("prefix_not_frozen_second_mail")
    requests = [json.loads((directory / f"request-{n:02}.json").read_text(encoding="utf-8")) for n in range(1, 5)]
    responses = [json.loads((directory / f"response-{n:02}.json").read_text(encoding="utf-8")) for n in range(1, 5)]
    old = json.loads(requests[0]["messages"][1]["content"])
    record = json.loads((directory / "run-record.json").read_text(encoding="utf-8"))["record"]
    origin_result = json.loads((directory.parent / "result.json").read_text(encoding="utf-8"))
    if old["messages"][-1]["body"] != case["body"] or record["run"]["error_code"] != "input_budget_exceeded":
        raise RuntimeError("prefix_source_or_failure_changed")
    expected = [("get_order_snapshot", {"display_order_number": "999-7100002-8100000"}),
        ("search_reference", {"query": "remote control not responding troubleshooting batteries",
            "types": ["troubleshooting_md", "manual_pdf"], "order_line_id": "SIM-O-BASE-OUTON-02-L1"})]
    for response, (name, arguments) in zip(responses[2:], expected):
        if len(response["calls"]) != 1 or response["calls"][0]["name"] != name or json.loads(
                response["calls"][0]["arguments"]) != arguments:
            raise RuntimeError("prefix_tool_sequence_changed")
    metadata = {"origin_attempt_id": attempt, "origin_run_id": str(record["run"]["id"]),
        "origin": "four_already_paid_actual_responses_replayed_then_real_remaining_decision_validation",
        "replayed_requests": 4, "old_responses_are_new_quality_evidence": False,
        "origin_sampling": origin_result.get("new_actual_sampling", {"temperature": 0, "enable_thinking": False, "top_p": "server_default"}),
        "origin_active_ms": record["usage"]["active_ms"],
        "time_accounting": "guarded_insert_original_active_ms_before_real_Budget_initialization; replay_requests_counted_normally",
        "source_id_mapping": "same_seq_sender_original_body_only",
        "business_reads": "reexecuted_in_current_isolated_gateway_not_replayed_tool_results",
        "identity_mapping": "order_line_external_id_is_unchanged_not_a_database_uuid",
        "old_code_snapshot": origin_result["code_snapshot"],
        "files_sha256": {p.name: digest(p.read_bytes()) for p in directory.glob("*.json")}}
    return old, requests, responses, metadata


def seed_ledger_time(fixture, job, loaded, private):
    """Explicit isolated eval initialization; never reduces budgets or inserts a business fact."""
    import sqlalchemy as sa
    from uuid import uuid4
    from bootstrap import write
    from globalmail_agent.adapters.agent_schema import cycle_budgets
    from globalmail_agent.adapters.schema import SCOPE_KEYS
    from globalmail_agent.agent.guard import guarded
    from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
    with guarded(fixture.engine, DEFAULT_WORKSPACE_ID, job, check_knowledge=False) as (conn, conv, run, cycle):
        if conn.execute(sa.select(cycle_budgets.c.id).where(cycle_budgets.c.cycle_id == cycle["id"])).first():
            raise RuntimeError("prefix_time_seed_requires_new_cycle")
        conn.execute(sa.insert(cycle_budgets).values(id=uuid4(), **{key: conv[key] for key in SCOPE_KEYS},
            conversation_id=conv["id"], cycle_id=cycle["id"], active_ms=loaded[3]["origin_active_ms"]))
        audit = {"cycle_id": str(cycle["id"]), "run_id": str(run["id"]),
            "origin_attempt_id": loaded[3]["origin_attempt_id"], "seeded_active_ms": loaded[3]["origin_active_ms"],
            "initial_model_requests": 0, "initial_tool_calls": 0,
            "reason": "retain paid prefix active time; actual replay increments request/tool/token counters through unmodified production Budget"}
    write(private / "prefix-budget-seed-before-model.json", audit)
    return audit


class PrefixReplay:
    def __init__(self, real_model, loaded, *, engineering_only=False):
        self.real, self.loaded = real_model, loaded
        self.model, self.configured = real_model.model, real_model.configured
        self.index, self.ids, self.engineering = 0, {}, engineering_only
        self.new_http_calls = 0
        self.started = time.monotonic()

    def map_ids(self, value):
        if isinstance(value, str):
            return self.ids.get(value, value)
        if isinstance(value, list):
            return [self.map_ids(v) for v in value]
        if isinstance(value, dict):
            return {k: self.map_ids(v) for k, v in value.items()}
        return value

    def request(self, messages, *, schema=None, tools=None, timeout=30):
        old, requests, responses, metadata = self.loaded
        index = self.index
        self.index += 1
        if index == 0:
            current = json.loads(messages[1]["content"])
            prior_messages = old["messages"]
            if len(prior_messages) != len(current["messages"]):
                raise RuntimeError("prefix_visible_source_count_changed")
            for prior, fresh in zip(prior_messages, current["messages"]):
                if any(prior[k] != fresh[k] for k in ("body", "sender", "seq")):
                    raise RuntimeError("prefix_visible_source_changed")
                self.ids[prior["message_id"]] = fresh["message_id"]
            if old["human_notes"] or current["human_notes"]:
                raise RuntimeError("prefix_unexpected_human_note")
        if index == 3:
            old_order = json.loads(next(m["content"] for m in requests[3]["messages"] if m["role"] == "tool"))
            fresh_order = json.loads(next(m["content"] for m in messages if m["role"] == "tool"))
            # Random scoped customer ID is the only changing field in the actual order data.
            def stable_data(result):
                value = deepcopy(result["data"])
                for order in value["orders"]:
                    order.pop("customer_id")
                return value
            if fresh_order["status"] != "ok" or stable_data(old_order) != stable_data(fresh_order):
                raise RuntimeError("prefix_current_order_snapshot_changed")
        if index < 4:
            output = deepcopy(responses[index])
            if output.get("content"):
                output["content"] = json.dumps(self.map_ids(json.loads(output["content"])), ensure_ascii=False)
            for call in output["calls"]:
                call["arguments"] = json.dumps(self.map_ids(json.loads(call["arguments"])), ensure_ascii=False)
            output["_eval_provenance"] = {"kind": "replayed_paid_response", "origin_attempt_id": metadata["origin_attempt_id"],
                "origin_request_index": index + 1, "origin_provider_request_id": output.get("request_id"),
                "sampling": metadata["origin_sampling"],
                "new_http_call": False}
            return output
        if self.engineering:
            return self.engineering_output(index, messages)
        from globalmail_agent.application.conversation_lock import ServiceError
        combined_remaining = 120 - metadata["origin_active_ms"] / 1000 - (time.monotonic() - self.started)
        if combined_remaining <= 0:
            raise ServiceError("budget_exhausted")
        self.new_http_calls += 1
        output = self.real.request(messages, schema=schema, tools=tools, timeout=min(timeout, combined_remaining))
        output["_eval_provenance"] = {"kind": "new_actual_http", "new_http_call": True}
        return output

    @staticmethod
    def engineering_output(index, messages):
        if index == 4:
            result = json.loads([m["content"] for m in messages if m["role"] == "tool"][-1])
            refs = result["evidence_refs"]
            identity = refs[0]["evidence_id"]
            body = "Please confirm what the remote indicator and lamp do when you press a remote button."
            args = {"language": "en", "body": body, "waiting_for": "customer_feedback",
                "citation_ids": [identity], "claims": [{"kind": "product_step", "text": body, "source_ids": [identity]}]}
            output = {"content": None, "calls": [{"id": uuid4().hex, "name": "create_reply_draft",
                "arguments": json.dumps(args)}]}
        elif index == 5:
            output = {"content": json.dumps({"supported": True, "language_correct": True,
                "unsupported_claims": [], "reason": "Explicit engineering-only scripted review; not model evidence."}), "calls": []}
        else:
            raise RuntimeError("engineering_requested_unplanned_response")
        return {**output, "request_id": "engineering-only-scripted", "finish_reason": "stop",
            "usage": {"prompt_tokens": 0, "completion_tokens": 0},
            "_eval_provenance": {"kind": "engineering_only_scripted_terminal", "new_http_call": False}}
