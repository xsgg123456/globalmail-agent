"""Explicit model sequences; all scope, persistence and effect gates remain real."""
from copy import deepcopy
import json
from uuid import UUID, uuid4
import sqlalchemy as sa
from test_protocol import ProtocolFixture
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.conversation_schema import messages
from globalmail_agent.agent.budget import Budget
from globalmail_agent.agent.context import load_context
from globalmail_agent.agent.tool_gateway import ToolGateway
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.domain.conversation import CreateConversation, AppendMessage, Command


def understanding(messages, **changes):
    # No semantic-quality claim: source binding is taken from actual database context.
    value = {"language": "en", "intents": [], "order_candidates": [], "facts": [],
        "risk_flags": [], "missing_information": ["order_number"]}
    value.update(changes)
    return value


def draft(body="Please share your order number.", **changes):
    value = {"language": "en", "body": body, "claims": [{"kind": "clarification", "text": body,
        "source_ids": []}], "citation_ids": [], "waiting_for": "customer_information"}
    value.update(changes)
    return value


def call(name, args, key=None):
    return {"id": key or uuid4().hex, "name": name, "arguments": json.dumps(args, ensure_ascii=False)}


def terminal(body="Please share your order number.", **changes):
    return {"calls": [call("create_reply_draft", draft(body, **changes))]}


class ScriptedModel:
    model, configured = "qwen3.7-plus", True

    def __init__(self, *steps, usage="known", reviews=None, audit_fixture=True):
        self.steps, self.requests, self.usage = list(steps), [], usage
        self.audit_fixture = audit_fixture
        # One frozen engineering approval is available by default. This is not
        # semantic-quality evidence and cannot extend an unlimited model loop.
        self.reviews = list(reviews) if reviews is not None else [{"supported": True,
            "language_correct": True, "unsupported_claims": [], "reason": "Explicit protocol fixture approval"}]

    def request(self, messages, *, schema=None, tools=None, timeout=30):
        self.requests.append({"messages": deepcopy(messages), "schema": schema, "tools": tools, "timeout": timeout})
        if schema and "supported" in schema.get("properties", {}):
            if not self.reviews:
                raise AssertionError("Unexpected validation beyond the frozen approvals")
            step = self.reviews.pop(0)
        else:
            if not self.steps:
                raise AssertionError("Unexpected model request beyond the frozen sequence")
            step = self.steps.pop(0)
        if isinstance(step, Exception):
            raise step
        value = step(messages) if callable(step) else step
        if schema and 'request_checks' in schema.get('properties', {}) and self.audit_fixture:
            from agent_review_fixture import engineering_audit
            value = engineering_audit(messages, value)
        if schema and isinstance(value, dict) and "content" not in value:
            value = {"content": json.dumps(value, ensure_ascii=False)}
        output = {"content": "", "calls": [], "usage": {"prompt_tokens": 20, "completion_tokens": 10}
            if self.usage == "known" else None, "request_id": "explicit_fake_" + str(len(self.requests)),
            "finish_reason": "stop"}
        output.update(value)
        return output


class AgentSupport:
    def create_mail(self, body="My lamp has stopped working.", email="agent@example.test"):
        row = self.service.create(CreateConversation(expected_version=0, sender_email=email, body=body), uuid4().hex)
        return UUID(row["conversation_id"]), UUID(row["run_id"])

    def append_mail(self, cid, body):
        conv = self.conversation(cid)
        return self.service.append(cid, AppendMessage(expected_version=conv["row_version"], body=body), uuid4().hex)

    def scene(self, name="BASE-OUTON-01", package=None):
        from globalmail_agent.application.fixture_conversations import FixtureConversations
        row = FixtureConversations(self.engine, self.store, package).create(name, Command(expected_version=0), uuid4().hex)
        return UUID(row["conversation_id"]), UUID(row["run_id"]) if row.get("run_id") else None

    def claimed(self, owner="agent_protocol_worker"):
        job = self.leases.claim(owner)
        self.assertIsNotNone(job)
        return job

    def components(self, job=None, embedding=None):
        job = job or self.claimed()
        budget = Budget(self.engine, DEFAULT_WORKSPACE_ID, job)
        context = load_context(self.engine, self.store, DEFAULT_WORKSPACE_ID, job)
        gateway = ToolGateway(self.engine, self.store, embedding, context, job, budget)
        return job, context, budget, gateway

    def execute(self, model, job=None, embedding=None):
        from globalmail_agent.worker.agent_runner import AgentRunner
        job = job or self.claimed()
        runner = AgentRunner(self.engine, self.store, DEFAULT_WORKSPACE_ID, model, embedding)
        return runner.execute(job), job

    def row(self, table, predicate):
        with self.engine.connect() as conn:
            return dict(conn.execute(sa.select(table).where(predicate)).mappings().one())

    def outbound(self, cid):
        with self.engine.connect() as conn:
            return list(conn.execute(sa.select(messages).where(messages.c.conversation_id == cid,
                messages.c.sender == "simulated_agent")).mappings())

    def budget_row(self, job):
        return self.row(a.cycle_budgets, a.cycle_budgets.c.cycle_id == job["cycle_id"])

    def assert_error(self, code, action):
        with self.assertRaises(ServiceError) as raised:
            action()
        self.assertEqual(raised.exception.code, code)

    def approve_fixture_draft(self, context, job, value):
        """Explicit engineering approval prerequisite for testing the commit gate.

        Full-run tests use the actual validation graph and bounded model response;
        direct transaction tests seed its exact normalized hash through real guards.
        This fixture never establishes natural-language grounding quality.
        """
        from globalmail_agent.agent.guard import guarded
        from globalmail_agent.agent.outcome_validation import draft_hash
        with guarded(self.engine, context.workspace_id, job) as (conn, conv, run, cycle):
            conn.execute(a.agent_run_contexts.update().where(a.agent_run_contexts.c.run_id == run["id"])
                .values(validated_draft_hash=draft_hash(value)))


class AgentFixture(AgentSupport, ProtocolFixture):
    def setUp(self):
        super().setUp()
        self.store = self.service.store
