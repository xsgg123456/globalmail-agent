"""No paid calls: replay saved actual understanding + scripted terminal to isolate engineering."""
import argparse
from copy import deepcopy
import json
import time
from uuid import UUID
from bootstrap import ROOT, isolated_database_environment, configured_settings, frozen_inputs, write
from recording import capture_graph_errors


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt", required=True)
    args = parser.parse_args()
    from legacy_review import reject_legacy_scripted_review
    reject_legacy_scripted_review()
    cases, _ = frozen_inputs()
    private_root = (ROOT / "tmp/phase7-agent-eval").resolve()
    saved = (private_root / args.attempt / "P7-01-missing-order").resolve()
    if not saved.is_relative_to(private_root):
        raise RuntimeError("replay_outside_private_directory")
    response = json.loads((saved / "response-01.json").read_text(encoding="utf-8"))
    request = json.loads((saved / "request-01.json").read_text(encoding="utf-8"))
    old_payload = json.loads(request["messages"][1]["content"])
    isolated_database_environment()
    from knowledge_helpers import KnowledgeFixture
    from agent_fixture import ScriptedModel, terminal
    from globalmail_agent.adapters.fixture_loader import FixturePackage
    from globalmail_agent.agent.context import load_context
    from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
    from globalmail_agent.application.run_records import RunRecords
    from globalmail_agent.worker.agent_runner import AgentRunner
    from globalmail_agent.knowledge.embedding import EmbeddingGateway
    from run_eval import scene, outbound
    fixture = KnowledgeFixture("runTest")
    target = saved.parent / ("engineering-replay-" + time.strftime("%H%M%S"))
    summary = {"scope": "engineering_saved_response_plus_scripted_terminal_not_real_business_quality", "paid_calls": 0}
    try:
        fixture.setUp()
        case = cases["closed_loop"]["messages"][0]
        created = scene(fixture, FixturePackage(), {**case, "scenario": cases["closed_loop"]["scenario"]})
        job = fixture.leases.claim("phase7_engineering_replay")
        context = load_context(fixture.engine, fixture.store, DEFAULT_WORKSPACE_ID, job)
        ids = {old["message_id"]: new["message_id"] for old, new in zip(old_payload["messages"], context.payload["messages"])
            if old["body"] == new["body"] and old["sender"] == new["sender"]}
        value = json.loads(response["content"])
        for collection in ("intents", "order_candidates", "facts", "risk_flags"):
            for item in value[collection]:
                for source in item["sources"]:
                    source["message_id"] = ids[source["message_id"]]
        replay = deepcopy(response)
        replay["content"] = json.dumps(value, ensure_ascii=False)
        model = ScriptedModel(replay, terminal(), {"supported": True, "language_correct": True,
            "unsupported_claims": [], "reason": "Scripted engineering receipt only, not semantic-quality evidence."})
        restore = capture_graph_errors(target)
        try:
            output = AgentRunner(fixture.engine, fixture.store, DEFAULT_WORKSPACE_ID, model,
                EmbeddingGateway(configured_settings())).execute(job)
        finally:
            restore()
        record = RunRecords(fixture.engine, fixture.store).get(UUID(created["run_id"]))
        write(target / "record.json", {"output": output, "record": record})
        summary.update(status=record["run"]["status"], error_code=record["run"]["error_code"],
            understanding_saved=bool(record["understanding"]), outbound=outbound(fixture, UUID(created["conversation_id"])),
            graph_requests=len(model.requests))
    finally:
        fixture.doCleanups()
        summary["cleanup"] = "owned_schema_and_objects_removed"
        write(target / "summary.json", summary)
    print(json.dumps(summary))
    if summary.get("status") != "completed" or summary.get("outbound") != 1:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
