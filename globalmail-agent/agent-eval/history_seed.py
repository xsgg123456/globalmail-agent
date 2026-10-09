"""Authorized reuse of an already paid and accepted reply; never new model-quality evidence."""
from copy import deepcopy
import json
from uuid import UUID
from bootstrap import ROOT, digest, write


def load_seed(attempt, first_case):
    base = (ROOT / "tmp/phase7-agent-eval").resolve()
    directory = (base / attempt / first_case["case_id"]).resolve()
    if not directory.is_relative_to(base):
        raise RuntimeError("seed_outside_private_directory")
    from legacy_review import require_compatible_history_review
    require_compatible_history_review(directory)
    request = json.loads((directory / "request-01.json").read_text(encoding="utf-8"))
    payload = json.loads(request["messages"][1]["content"])
    if len(payload["messages"]) != 1 or payload["messages"][0]["body"] != first_case["body"]:
        raise RuntimeError("seed_does_not_match_frozen_first_input")
    record = json.loads((directory / "run-record.json").read_text(encoding="utf-8"))["record"]
    if record["run"]["status"] != "completed" or len(record["artifacts"]) != 1:
        raise RuntimeError("seed_not_a_completed_actual_reply")
    response_files = sorted(directory.glob("response-*.json"))
    if len(response_files) != 3:
        raise RuntimeError("seed_response_sequence_unexpected")
    responses = [json.loads(p.read_text(encoding="utf-8")) for p in response_files]
    origin_result = json.loads((directory.parent / "result.json").read_text(encoding="utf-8"))
    metadata = {"origin": "already_paid_actual_qwen_reply_replayed_only_for_history_initialization",
        "origin_attempt_id": attempt, "origin_run_id": str(record["run"]["id"]),
        "accepted_reply_sha256": digest(record["artifacts"][0]["body"].encode()),
        "origin_sampling": origin_result.get("new_actual_sampling", {"temperature": 0, "enable_thinking": False, "top_p": "server_default"}),
        "responses_sha256": {p.name: digest(p.read_bytes()) for p in response_files},
        "trusted_original_file_sha256": {str(p.relative_to(ROOT)).replace("\\", "/"): digest(p.read_bytes())
            for p in [directory / "request-01.json", directory / "run-record.json", directory.parent / "result.json", *response_files]},
        "new_model_http_calls": 0, "new_business_quality_claim": False}
    return payload, responses, metadata


def initialize(fixture, package, cases, loaded, embedding, private):
    from globalmail_agent.agent.context import load_context
    from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
    from globalmail_agent.application.run_records import RunRecords
    from globalmail_agent.worker.agent_runner import AgentRunner
    from run_eval import scene, outbound
    first = cases["closed_loop"]["messages"][0]
    created = scene(fixture, package, {**first, "scenario": cases["closed_loop"]["scenario"]})
    cid = UUID(created["conversation_id"])
    job = fixture.leases.claim("phase7_authorized_history_seed")
    context = load_context(fixture.engine, fixture.store, DEFAULT_WORKSPACE_ID, job)
    old_payload, responses, metadata = loaded
    identities = {old["message_id"]: new["message_id"] for old, new in zip(old_payload["messages"], context.payload["messages"])
        if old["body"] == new["body"] and old["sender"] == new["sender"]}

    def map_ids(value):
        if isinstance(value, str):
            return identities.get(value, value)
        if isinstance(value, list):
            return [map_ids(v) for v in value]
        if isinstance(value, dict):
            return {k: map_ids(v) for k, v in value.items()}
        return value

    mapped = deepcopy(responses)
    for response in mapped:
        if response["content"]:
            response["content"] = json.dumps(map_ids(json.loads(response["content"])), ensure_ascii=False)
        for call in response["calls"]:
            call["arguments"] = json.dumps(map_ids(json.loads(call["arguments"])), ensure_ascii=False)
    class RecordedHistoryReplay:
        model, configured = "qwen3.7-plus", True
        def __init__(self, steps):
            self.steps, self.requests = list(steps), []
        def request(self, messages, *, schema=None, tools=None, timeout=30):
            self.requests.append({"schema": schema, "tools": tools})
            if not self.steps:
                raise RuntimeError("history_seed_requested_unpaid_response")
            return self.steps.pop(0)
    model = RecordedHistoryReplay(mapped)
    output = AgentRunner(fixture.engine, fixture.store, DEFAULT_WORKSPACE_ID, model, embedding).execute(job)
    record = RunRecords(fixture.engine, fixture.store).get(UUID(created["run_id"]))
    write(private / "history-seed-record.json", {"output": output, "record": record})
    if record["run"]["status"] != "completed" or outbound(fixture, cid) != 1:
        raise RuntimeError("authorized_history_seed_engineering_failed")
    body = record["artifacts"][0]["body"]
    if digest(body.encode()) != metadata["accepted_reply_sha256"] or model.steps:
        raise RuntimeError("authorized_history_seed_reply_changed")
    return cid, {**metadata, "seed_run_id": str(record["run"]["id"]), "seed_trace_id": record["trace_id"],
        "status": "completed", "source_id_mapping": "same_original_body_only"}
