"""Actual PG correlation, multiple-order waits, barriers and versioned manual facts."""
from copy import deepcopy
from uuid import UUID, uuid4
import sqlalchemy as sa
from agent_fixture import AgentFixture, understanding, draft
from after_sales_fixture import AfterSalesFixture
from globalmail_agent.adapters import agent_schema as a, business_schema as b
from globalmail_agent.adapters.conversation_schema import case_issues, domain_events, messages, jobs
from globalmail_agent.adapters.fixture_loader import FixturePackage
from globalmail_agent.application.branch_facts import BranchFactsService
from globalmail_agent.application.case_issues import sync_intents
from globalmail_agent.application.conversation_lock import lock_conversation
from globalmail_agent.application.commit_outcome import commit_outcome
from globalmail_agent.application.waits import record_wake
from globalmail_agent.application.business_queries import BusinessQueries
from globalmail_agent.domain.conversation import Takeover
from globalmail_agent.domain.business_events import BranchFact
from globalmail_agent.application.waits import register_wait


class BusinessIssueTests(AgentFixture):
    def test_multi_order_intents_bind_two_issues_without_guessing_an_order(self):
        cid, _ = self.scene("SCN-022")
        data = BusinessQueries(self.engine).detail(cid)["data"]
        with self.engine.begin() as conn:
            conv = lock_conversation(conn, cid)
            message = conn.execute(sa.select(messages).where(messages.c.conversation_id == cid)).mappings().first()
            intents = [{"business_type": "refund", "order_number": order["display_order_number"],
                "target_item": order["lines"][0]["sku"], "sources": [{"message_id": str(message["id"])}]} for order in data["orders"]]
            sync_intents(conn, conv, {"intents": intents})
            sync_intents(conn, conv, {"intents": intents})
            sync_intents(conn, conv, {"intents": [{"business_type": "refund", "sources": [{"message_id": str(message["id"])}]}]})
        rows = self.service.detail(cid)["issues"]
        linked = [r for r in rows if r["order_line_id"]]
        self.assertEqual(len(linked), 2)
        self.assertEqual(len({r["order_line_id"] for r in linked}), 2)

    def test_two_order_issues_keep_independent_waits_and_reject_future_issue_version(self):
        cid, rid = self.scene("SCN-022")
        data = BusinessQueries(self.engine).detail(cid)["data"]
        with self.engine.begin() as conn:
            conv = lock_conversation(conn, cid)
            message = conn.execute(sa.select(messages.c.id).where(messages.c.conversation_id == cid)).scalar_one()
            intents = [{"business_type": "replacement", "order_number": order["display_order_number"],
                "target_item": order["lines"][0]["sku"], "sources": [{"message_id": str(message)}]} for order in data["orders"]]
            sync_intents(conn, conv, {"intents": intents})
            issues = conn.execute(sa.select(case_issues).where(case_issues.c.conversation_id == cid,
                case_issues.c.order_line_id.is_not(None))).mappings().all()
            for issue in issues:
                self.assertTrue(register_wait(conn, conv, rid, "inventory", issue_id=str(issue["id"])))
        with self.engine.connect() as conn:
            rows = conn.execute(sa.select(a.wait_conditions).where(a.wait_conditions.c.conversation_id == cid)).mappings().all()
            self.assertEqual(len(rows), 2)
            self.assertEqual(len({r["condition_key"] for r in rows}), 2)
            self.assertEqual({r["issue_id"] for r in rows}, {r["id"] for r in issues})
        with self.engine.begin() as conn:
            self.assert_error("future_business_version", lambda: register_wait(conn, lock_conversation(conn, cid), rid,
                "inventory", observed_version=1, issue_id=str(issues[0]["id"])))

    def test_completed_run_consumes_only_events_in_its_frozen_context(self):
        cid, _ = self.scene("SCN-027")
        op = BusinessQueries(self.engine).detail(cid)["data"]["operations"][0]["operation_id"]
        with self.engine.begin() as conn:
            record_wake(conn, lock_conversation(conn, cid), "manual_execution:" + op, 1)
        job, context, _, _ = self.components()
        with self.engine.begin() as conn:
            conv = lock_conversation(conn, cid)
            from globalmail_agent.application.event_store import record_event
            later = record_event(conn, conv, "business_notification", "unrelated-late-record", "recorded", {}, suppressed=True)
        value = draft()
        self.approve_fixture_draft(context, job, value)
        commit_outcome(self.engine, self.store, context, job, understanding([]), {"kind": "reply", "data": value})
        with self.engine.connect() as conn:
            row = conn.execute(sa.select(domain_events).where(domain_events.c.id == later["id"])).mappings().one()
            self.assertEqual(row["status"], "suppressed_by_human")
            self.assertIsNone(row["observed_run_id"])


class BranchFactTests(AfterSalesFixture):
    def fact(self, cid, event="inventory_snapshot", **changes):
        with self.engine.connect() as conn:
            conv = self.conversation(cid)
            line = conn.execute(sa.select(b.branch_order_lines).where(b.branch_order_lines.c.branch_id == conv["branch_id"])).mappings().first()
            branch = conn.execute(sa.select(b.simulation_branches).where(b.simulation_branches.c.id == conv["branch_id"])).mappings().one()
        value = dict(conversation_id=cid, expected_version=conv["row_version"], source_event_id=uuid4().hex,
            order_line_id=line["external_id"], event=event, expected_business_version=0, business_version=1,
            staff_id="isolated-staff", receipt_ref="isolated-stock-proof", reason="Operator verified exact inventory",
            item_id=line["sku"], region_spec="US", hardware_revision=line["hardware_revision"],
            snapshot_at=branch["clock"], on_hand=7)
        value.update(changes)
        command = BranchFact(**value)
        return UUID(str(conv["branch_id"])), command

    def test_address_cannot_reconfirm_old_source_after_customer_changes_address(self):
        cid, _, request = self.prepared("replacement")
        self.append_mail(cid, "My address changed. Do not use the old delivery address.")
        bid, command = self.fact(cid, "address_confirmation", item_id=None, confirmed=True,
            selection_ref=request.selection_ref)
        self.assert_error("address_source_superseded", lambda: BranchFactsService(self.engine, self.store).event(bid, command, uuid4().hex))
        self.assertEqual(self.count(domain_events), 2)

    def test_inventory_before_request_is_recorded_not_polled_and_source_is_not_invented(self):
        cid, _, _ = self.prepared("replacement")
        service = BranchFactsService(self.engine, self.store)
        bid, command = self.fact(cid)
        self.assert_error("inventory_specification_and_snapshot_required", lambda: service.event(
            bid, command.model_copy(update={"hardware_revision": None}), uuid4().hex))
        before = self.count(jobs)
        output = service.event(bid, command, uuid4().hex)
        self.assertEqual(output["status"], "record_only")
        self.assertEqual(self.count(jobs), before)
        replay = service.event(bid, command, uuid4().hex)
        self.assertTrue(replay["duplicate"])
        self.assertEqual(self.count(jobs), before)
        self.assert_error("business_event_id_conflict", lambda: service.event(bid,
            command.model_copy(update={"on_hand": 8}), uuid4().hex))

    def test_managed_result_changes_version_and_early_wait_wake_is_pending(self):
        self.publish_policy()
        cid, context, request = self.prepared()
        output, _, _ = self.create_operation(cid, context, request)
        op = output["data"]["operation"]["operation_id"]
        result = self.push(cid, op, "create_execution")
        self.assertEqual(result["wake_status"], "pending")
        with self.engine.connect() as conn:
            wake = conn.execute(sa.select(a.wake_pending)).mappings().one()
            self.assertEqual(wake["business_version"], 2)
            self.assertIsNone(wake["observed_run_id"])
            issue = conn.execute(sa.select(case_issues).where(case_issues.c.id == wake["issue_id"])).mappings().one()
            self.assertEqual(issue["current_operation_id"], op)

    def test_human_barrier_records_real_inventory_without_queueing(self):
        self.publish_policy()
        cid, context, request = self.prepared("replacement")
        self.create_operation(cid, context, request)
        conv = self.conversation(cid)
        self.service.takeover(cid, Takeover(expected_version=conv["row_version"]), uuid4().hex)
        bid, command = self.fact(cid)
        before = self.count(jobs)
        output = BranchFactsService(self.engine, self.store).event(bid, command, uuid4().hex)
        self.assertEqual(output["status"], "suppressed_by_human")
        self.assertEqual(self.count(jobs), before)
        self.assertIsNone(self.leases.claim("business_cannot_cross_human"))
