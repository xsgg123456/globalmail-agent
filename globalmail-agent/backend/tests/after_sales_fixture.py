"""Real PG/HTTP publication and scoped authored transaction inputs, without paid models."""
from copy import deepcopy
from datetime import datetime
from types import SimpleNamespace
from uuid import UUID, uuid4
import sqlalchemy as sa
from agent_fixture import AgentSupport
from index_helpers import IndexFixture
from globalmail_agent.adapters import business_schema as b, agent_schema as a
from globalmail_agent.adapters.fixture_loader import FixturePackage
from globalmail_agent.adapters.conversation_schema import messages, conversations, case_issues
from globalmail_agent.application.business_queries import BusinessQueries
from globalmail_agent.application.after_sales import AfterSalesService
from globalmail_agent.application.simulation_control import SimulationControlService
from globalmail_agent.application.conversation_lock import lock_conversation
from globalmail_agent.domain.operations import CheckOperation, CreateOperation
from globalmail_agent.domain.executions import SimulationEvent
from globalmail_agent.domain.conversation import Command
from globalmail_agent.knowledge.commands import CreateDocument, ParseCommand, ReviewCommand
from globalmail_agent.knowledge.release_queries import head


class AfterSalesFixture(AgentSupport, IndexFixture):
    def setUp(self):
        super().setUp()
        self.sales = AfterSalesService(self.engine, self.store)
        self.simulation = SimulationControlService(self.engine, self.store)
        self.package = FixturePackage()

    def publish_policy(self, **numbers):
        policy = deepcopy(self.package.policy)
        for section, values in numbers.items():
            policy[section].update(values)
        result = self.docs.create(CreateDocument(expected_version=0, title="明确隔离模拟政策", document_type="policy_json",
            content=policy, source_reference="本测试核对的模拟政策", available_at="2026-10-01T00:00:00Z",
            applicabilities=[{"section_id": "document", "sku": "H-CTD16-US-BK", "basis": "精确测试SKU"}]), uuid4().hex)
        self.policy_did, vid = UUID(result["document_id"]), UUID(result["version_id"])
        self.runner.jobs.enqueue(vid, ParseCommand(expected_version=1, parser_profile_id="policy"), uuid4().hex)
        self.runner.execute(self.runner.jobs.claim(self.runner.owner))
        self.reviews.review(vid, ReviewCommand.model_validate(self.review_payload(vid)), uuid4().hex)
        self.publish([self.build(vid)])

    def prepared(self, action="refund", *, amount=5499, quantity=1, warehouse=True, stock=5, address_confirmed=True):
        index = {"refund": "04", "return": "05", "replacement": "06", "spare_part": "07", "logistics": "03"}[action]
        name = "BASE-OUTON-" + index
        package = deepcopy(self.package)
        for product in package.products:
            product["region_spec"] = "US"
        for mapping in package.compatibility:
            mapping["region_spec"] = "US"
        scene = package.scenarios[name]
        state, mail = scene["initial_state"], scene["initial_messages"][-1]
        order = state["orders"][0]
        line = order["lines"][0]
        if "address_confirmation" in state:
            state["address_confirmation"]["confirmed"] = address_confirmed
        line.update(quantity=quantity, paid_minor=5499 * quantity)
        if quantity > 1:
            line["unit_allocations"] = [{"unit_id": "u" + str(i), "paid_minor": 5499} for i in range(quantity)]
        order["paid_minor"] = line["paid_minor"]
        item = "SIM-OUTON-01-REMOTE-01" if action == "spare_part" else line["sku"]
        mail["body"] = f"I explicitly accept {action} for {quantity} unit(s) {item}. " + (
            f"Refund {amount / 100:.2f} USD." if action == "refund" else "My confirmed delivery address is unchanged.") + (
            "\n\nAmazon order number: " + order["display_order_number"])
        state["customer_choices"] = [{"kind": action, "accepted": True, "amount_minor": amount if action == "refund" else None,
            "currency": "USD" if action == "refund" else None, "order_line_id": line["line_id"], "quantity": 1,
            "item_id": item, "address_version": 1, "source_message_id": mail["message_id"],
            **({"affected_unit_ids": ["u0"]} if quantity > 1 else {})}]
        state["operations"] = []
        state["execution_records"] = []
        if not warehouse:
            state["returns"] = []
        elif quantity > 1:
            for row in state["returns"]:
                row.update(quantity=1, affected_unit_ids=["u0"], inspected_unit_ids=["u0"], inspected_quantity=1)
        for row in state["inventory"]:
            row.update(region_spec="US", hardware_revision="SIM-V1", snapshot_at="2026-10-08T09:00:00+08:00", on_hand=stock)
        package.validate(scene)
        cid, rid = self.scene(name, package)
        with self.engine.connect() as conn:
            conv = dict(conn.execute(sa.select(conversations).where(conversations.c.id == cid)).mappings().one())
            current = head(conn, conv["workspace_id"])
            message = conn.execute(sa.select(messages).where(messages.c.conversation_id == cid).order_by(messages.c.seq.desc())).mappings().first()
            issue = conn.execute(sa.select(case_issues.c.id).where(case_issues.c.conversation_id == cid)).scalar_one()
        context = SimpleNamespace(workspace_id=conv["workspace_id"], conversation_id=cid, run_id=rid,
            mode="simulation", as_of=datetime.fromisoformat(scene["clock"]), release_id=current["release_id"],
            release_epoch=current["epoch"], payload={"active_risks": []})
        command = CheckOperation(action=action, order_line_id=line["line_id"], issue_id=str(issue),
            selection_ref={"message_id": str(message["id"]), "quote": mail["body"]},
            quantity=1, amount_minor=amount if action == "refund" else None, currency="USD" if action == "refund" else None,
            item_id=item if action in {"spare_part", "replacement"} else None,
            address_version=1 if action in {"spare_part", "replacement"} else None,
            affected_unit_ids=["u0"] if quantity > 1 else None)
        return cid, context, command

    def check(self, cid, context, command):
        with self.engine.begin() as conn:
            conv = lock_conversation(conn, cid)
            return self.sales.check(conn, conv, context, command)

    def create_operation(self, cid, context, command, decision=None, command_id=None):
        decision = decision or self.check(cid, context, command)
        request = CreateOperation(**command.model_dump(), decision_id=decision["data"]["decision_id"])
        with self.engine.begin() as conn:
            conv = lock_conversation(conn, cid)
            identity = command_id or uuid4()
            if not conn.execute(sa.select(a.tool_commands.c.id).where(a.tool_commands.c.id == identity)).first():
                conn.execute(sa.insert(a.tool_commands).values(id=identity, **{k: conv[k] for k in b.SCOPE_KEYS},
                    conversation_id=cid, run_id=context.run_id, command_key=uuid4().hex, name="create_after_sales_operation",
                    arguments=request.model_dump(), payload_hash="a" * 64, status="prepared"))
            return self.sales.create(conn, conv, context, request, identity), request, identity

    def push(self, cid, operation_id, event, key=None, **fields):
        listing = self.sales.listing(cid, operation_id)["data"]
        operation = listing["operations"][0]
        command = SimulationEvent(conversation_id=cid, expected_version=listing["conversation_version"],
            operation_id=operation_id, expected_operation_version=operation["version"], event=event, **fields)
        return self.simulation.event(UUID(listing["branch_id"]), command, key or uuid4().hex)
