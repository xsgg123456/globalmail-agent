"""Evaluation-only adapter invokes real scoped services; caller supplies any model runner."""
from uuid import UUID
import sqlalchemy as sa
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import processing_cycles, messages
from globalmail_agent.application.fixture_conversations import FixtureConversations
from globalmail_agent.application.conversations import ConversationService
from globalmail_agent.application.business_queries import BusinessQueries
from globalmail_agent.application.after_sales import AfterSalesService
from globalmail_agent.domain.conversation import Command
from globalmail_agent.evaluation.journey_driver import CommitResult
from globalmail_agent.evaluation.service_gates import verify_business_gate
from globalmail_agent.evaluation.service_delivery import deliver


class ServiceAdapter:
    def __init__(self, engine, store, package, *, runner=None):
        with engine.connect() as conn:
            schema = conn.execute(sa.text("SELECT current_schema()")).scalar_one()
        if not schema.startswith(("test_", "phase10_")):
            raise ValueError("evaluation_requires_private_schema")
        self.engine, self.store, self.package, self.runner = engine, store, package, runner
        self.fixtures = FixtureConversations(engine, store, package)
        self.conversations = ConversationService(engine, store)
        self.business = BusinessQueries(engine)
        self.sales = AfterSalesService(engine, store)

    def create(self, scenario_id, initial, command_id):
        if initial != self.package.scenarios[scenario_id]:
            return CommitResult(False, reason="initial_fixture_mismatch")
        response = self.fixtures.create(scenario_id, Command(expected_version=0), command_id)
        cid = UUID(response["conversation_id"])
        detail = self.conversations.detail(cid)
        resources = {"conversation_id": str(cid), "branch_id": str(detail["conversation"]["branch_id"])}
        customer = [m for m in detail["messages"] if m["sender"] == "customer"]
        if customer:
            resources["message:initial_message"] = str(customer[-1]["id"])
        self.pump()
        return CommitResult(True, ("conversation:" + str(cid),), resources,
            (response["run_id"],) if response.get("run_id") else ())

    def pump(self):
        if self.runner is None:
            return
        job = self.runner.leases.claim(self.runner.owner)
        if job:
            self.runner.execute(job)

    def observe(self, scenario_id, resources):
        cid = UUID(resources["conversation_id"])
        detail = self.conversations.detail(cid)
        business = self.business.detail(cid)["data"]
        ledger = self.sales.listing(cid)["data"]
        runs = []
        with self.engine.connect() as conn:
            for run in detail["runs"]:
                cycle = conn.execute(sa.select(processing_cycles).where(processing_cycles.c.id == run["processing_cycle_id"])).mappings().one()
                context = conn.execute(sa.select(a.agent_run_contexts).where(a.agent_run_contexts.c.run_id == run["id"])).mappings().first()
                steps = [key[8:] for key, value in resources.items() if key.startswith("message:") and value == str(cycle["trigger_message_id"])]
                observed = set(context["observed_event_ids"]) if context else set()
                steps.extend(key[6:] for key, value in resources.items() if key.startswith("event:") and value in observed)
                runs.append({**run, "id": str(run["id"]), "observed_steps": steps})
        scenario = self.package.scenarios[scenario_id]
        return {"branch_id": scenario["branch_id"], "customer_id": scenario["access_scope"]["customer_id"],
            "conversation_id": str(cid), "revision": detail["conversation"]["row_version"],
            "run": runs[-1] if runs else None, "runs": runs, "conversation": detail["conversation"],
            "detail": detail, "ledger": ledger, "business": business,
            "ledger_resource_ids": {row["operation_id"]: row["operation_id"] for row in ledger["operations"]},
            "evidence_refs": ("conversation:" + str(cid), "business_digest:" + self.business.detail(cid)["resource_versions"]["business_digest"])}

    def verify_gate(self, name, event, observation, resources):
        return verify_business_gate(self, name, event, observation, resources)

    def apply(self, delivery, resources, command_id, authorization):
        from globalmail_agent.application.conversation_lock import ServiceError
        from pydantic import ValidationError
        try:
            result = deliver(self, delivery, resources, command_id, authorization)
        except ServiceError as error:
            return CommitResult(False, reason=error.code)
        except ValidationError:
            return CommitResult(False, reason="current_fact_fields_missing_or_invalid")
        if result.committed:
            self.pump()
        return result
