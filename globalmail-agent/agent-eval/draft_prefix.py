"""Audited actual under/order/search/draft prefix; new quality covers only later HTTP."""
from copy import deepcopy
import json
from uuid import UUID
from bootstrap import ROOT, digest, json_bytes, write
from prefix_replay import PrefixReplay


def load_draft_prefix(attempt, case):
    if attempt != "20261008-182447-c623f2cd" or case["case_id"] != "P7-02-order-and-evidence":
        raise RuntimeError("draft_prefix_not_authorized_frozen_origin")
    directory = ROOT / "tmp/phase7-agent-eval" / attempt / case["case_id"]
    files = [directory / f"{kind}-{n:02}.json" for n in range(1, 5) for kind in ("request", "response")]
    requests = [json.loads((directory / f"request-{n:02}.json").read_text(encoding="utf-8")) for n in range(1, 5)]
    responses = [json.loads((directory / f"response-{n:02}.json").read_text(encoding="utf-8")) for n in range(1, 5)]
    old = json.loads(requests[0]["messages"][1]["content"])
    record = json.loads((directory / "run-record.json").read_text(encoding="utf-8"))["record"]
    origin = json.loads((directory.parent / "result.json").read_text(encoding="utf-8"))
    names = [[], ["get_order_snapshot"], ["search_reference"], ["create_reply_draft"]]
    if old["messages"][-1]["body"] != case["body"] or record["run"]["error_code"] != "input_budget_exceeded":
        raise RuntimeError("draft_prefix_source_or_failure_changed")
    if [list(c["name"] for c in r["calls"]) for r in responses] != names or record["usage"]["active_ms"] != 37515:
        raise RuntimeError("draft_prefix_actual_sequence_or_time_changed")
    if any(r["finish_reason"] not in {"stop", "tool_calls"} or not r.get("usage") for r in responses):
        raise RuntimeError("draft_prefix_incomplete_or_unknown_response")
    metadata = {"origin_attempt_id": attempt, "origin_run_id": str(record["run"]["id"]),
        "prefix_kind": "actual_under_order_search_draft",
        "origin": "four_paid_actual_responses_replayed_with_live_reads_then_new_validation_only",
        "replayed_requests": 4, "old_responses_are_new_quality_evidence": False,
        "origin_sampling": origin["new_actual_sampling"], "origin_active_ms": 37515,
        "time_accounting": "guarded_original_entire_failed_cycle_time_base_plus_current_elapsed",
        "source_id_mapping": "exact_same_seq_sender_subject_body_scoped_uuid_only",
        "business_reads": "current_gateway_order_and_full_knowledge_reexecuted_and_compared",
        "old_code_snapshot": origin["code_snapshot"],
        "failed_fifth_validation_response_is_reused": False,
        "original_validation_request_05_input_sha256": digest((directory / "request-05.json").read_bytes()),
        "original_four_usage": [r["usage"] for r in responses],
        "trusted_original_file_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p.read_bytes())
            for p in [*files, directory / "request-05.json", directory / "run-record.json", directory.parent / "result.json"]},
        "files_sha256": {p.name: digest(p.read_bytes()) for p in files}}
    return old, requests, responses, metadata


def semantic_context(value):
    value = deepcopy(value)
    for fact in value["case_facts"]:
        if fact["kind"] == "customer_report":
            fact["value"] = json.loads(fact["value"])
    return value


class DraftPrefixReplay(PrefixReplay):
    def __init__(self, real_model, loaded, private):
        super().__init__(real_model, loaded)
        self.private, self.differences, self.current_observations = private, [], []

    def audit(self):
        write(self.private / "draft-prefix-field-audit.json", {
            "metadata": self.loaded[3], "identity_mapping": self.ids,
            "allowed_field_changes": self.differences,
            "replayed_paid_responses": self.index, "new_model_http_calls": self.new_http_calls,
            "compared_actual_gateway_observations": len(self.current_observations),
            "current_observation_provenance": "current AgentGraph.tools normalized real ToolGateway.call outputs; no replayed tool results",
            "current_observation_raw_path": (self.private / "request-04.json").resolve().as_posix() + ":messages[role=tool]",
            "complete_knowledge_text_sha256": [digest(e["text"].encode())
                for observation in self.current_observations
                for e in json.loads(observation["content"])["data"].get("evidence", [])],
            "strict_comparisons": "all_non_identity_business_data_full_SOP_and_draft_non_ID_fields_equal"})

    def identity(self, old, fresh, path, kind="scoped_uuid"):
        prefix = "command:" if kind == "command_uuid" else "branch:" if kind == "branch_uuid" else ""
        UUID(old.removeprefix(prefix)), UUID(fresh.removeprefix(prefix))
        prior = self.ids.get(old)
        if prior is not None and prior != fresh:
            raise RuntimeError("draft_prefix_inconsistent_identity_mapping")
        self.ids[old] = fresh
        if old != fresh:
            self.differences.append({"path": path, "kind": kind, "old": old, "current": fresh})

    def compare_context(self, current):
        old = self.loaded[0]
        if len(old["messages"]) != len(current["messages"]):
            raise RuntimeError("draft_prefix_visible_message_count_changed")
        for index, (prior, fresh) in enumerate(zip(old["messages"], current["messages"])):
            if {k: v for k, v in prior.items() if k != "message_id"} != {
                    k: v for k, v in fresh.items() if k != "message_id"}:
                raise RuntimeError("draft_prefix_complete_mail_changed")
            self.identity(prior["message_id"], fresh["message_id"], f"context.messages[{index}].message_id")
        if self.map_ids(semantic_context(old)) != semantic_context(current):
            raise RuntimeError("draft_prefix_context_non_identity_fields_changed")

    def compare_observations(self, messages):
        old_messages = [m for m in self.loaded[1][3]["messages"] if m["role"] == "tool"]
        fresh_messages = [m for m in messages if m["role"] == "tool"]
        for index in range(len(self.current_observations), len(fresh_messages)):
            prior_message, fresh_message = old_messages[index], fresh_messages[index]
            if prior_message["tool_call_id"] != fresh_message["tool_call_id"]:
                raise RuntimeError("draft_prefix_tool_call_link_changed")
            old, fresh = json.loads(prior_message["content"]), json.loads(fresh_message["content"])
            self.identity(old["command_source_id"], fresh["command_source_id"],
                f"observations[{index}].command_source_id", "command_uuid")
            if index == 0:
                for n, (prior_order, current_order) in enumerate(zip(old["data"]["orders"], fresh["data"]["orders"])):
                    self.identity(prior_order["customer_id"], current_order["customer_id"],
                        f"observations[0].data.orders[{n}].customer_id")
                self.identity(old["evidence_refs"][0]["evidence_id"], fresh["evidence_refs"][0]["evidence_id"],
                    "observations[0].evidence_refs[0].evidence_id", "branch_uuid")
            else:
                for n, (prior_ref, current_ref) in enumerate(zip(old["data"]["evidence"], fresh["data"]["evidence"])):
                    self.identity(prior_ref["evidence_id"], current_ref["evidence_id"],
                        f"observations[1].data.evidence[{n}].evidence_id")
            normalized = self.map_ids(old)
            for path, kind in (("observed_at", "current_actual_observation_timestamp"),
                    ("resource_versions.business_digest", "derived_digest_of_current_scoped_ledger")):
                old_value = old["observed_at"] if path == "observed_at" else old["resource_versions"]["business_digest"]
                new_value = fresh["observed_at"] if path == "observed_at" else fresh["resource_versions"]["business_digest"]
                self.differences.append({"path": f"observations[{index}].{path}", "kind": kind,
                    "old": old_value, "current": new_value})
                if path == "observed_at":
                    normalized["observed_at"] = new_value
                else:
                    normalized["resource_versions"]["business_digest"] = new_value
            if normalized != fresh:
                raise RuntimeError("draft_prefix_business_or_full_knowledge_changed")
            self.current_observations.append(deepcopy(fresh_message))
        self.audit()

    def verify_validation(self, messages, *, current_prompts=True):
        from globalmail_agent.adapters.model_provider import prompt
        source = ROOT / "tmp/phase7-agent-eval" / self.loaded[3]["origin_attempt_id"] / "P7-02-order-and-evidence/request-05.json"
        if digest(source.read_bytes()) != self.loaded[3]["original_validation_request_05_input_sha256"]:
            raise RuntimeError("draft_prefix_trusted_validation_input_changed_after_freeze")
        prior = json.loads(source.read_text(encoding="utf-8"))
        prior_payload = json.loads(prior["messages"][1]["content"])
        fresh_payload = json.loads(messages[1]["content"])
        expected = self.map_ids(prior_payload)
        expected["context"] = self.map_ids(semantic_context(prior_payload["context"]))
        current = deepcopy(fresh_payload)
        current["context"] = semantic_context(current["context"])
        expected["observations"] = self.current_observations
        if current != expected:
            raise RuntimeError("draft_prefix_validation_data_or_draft_non_identity_fields_changed")
        if [m["role"] for m in messages] != ["system", "user", "system"] or (current_prompts and (
                messages[0]["content"] != prompt("validation") or messages[-1]["content"] != prompt("validation-grounding"))):
            raise RuntimeError("draft_prefix_validation_messages_not_current_graph")
        self.audit()
        return {"complete_data_equal_after_listed_identity_observation_metadata_changes": True,
            "draft_body_and_all_non_id_fields_unchanged": True,
            "origin_draft_body_sha256": digest(prior_payload["draft"]["body"].encode()),
            "current_draft_body_sha256": digest(fresh_payload["draft"]["body"].encode()),
            "current_full_user_sha256": digest(messages[1]["content"].encode()),
            "system_prompt_provenance": "current_graph" if current_prompts else "trusted_historical_accepted_request_not_new_quality",
            "first_and_tail_system_sha256": [digest(messages[i]["content"].encode()) for i in (0, -1)]}

    def request(self, messages, *, schema=None, tools=None, timeout=30):
        if self.index == 0:
            self.compare_context(json.loads(messages[1]["content"]))
        elif self.index in (2, 3):
            self.compare_observations(messages)
        if self.index < 4:
            output = deepcopy(self.loaded[2][self.index])
            if output.get("content") and schema is not None:
                output["content"] = json.dumps(self.map_ids(json.loads(output["content"])), ensure_ascii=False)
            for call in output["calls"]:
                call["arguments"] = json.dumps(self.map_ids(json.loads(call["arguments"])), ensure_ascii=False)
            output["_eval_provenance"] = {"kind": "replayed_paid_response", "new_http_call": False,
                "origin_attempt_id": self.loaded[3]["origin_attempt_id"], "origin_request_index": self.index + 1,
                "origin_provider_request_id": output["request_id"], "sampling": self.loaded[3]["origin_sampling"]}
            self.index += 1
            self.audit()
            return output
        if self.index == 4:
            write(self.private / "validation-data-audit-before-new-http.json", self.verify_validation(messages))
        return super().request(messages, schema=schema, tools=tools, timeout=timeout)
