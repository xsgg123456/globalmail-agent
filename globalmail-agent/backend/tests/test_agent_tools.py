"""Strict source/scope controls through actual PG services and terminal validation."""
from copy import deepcopy
import json
from uuid import uuid4
import sqlalchemy as sa
from agent_fixture import AgentFixture, ScriptedModel, understanding, terminal, draft, call
from globalmail_agent.adapters import agent_schema as a, business_schema as b
from globalmail_agent.adapters.fixture_loader import FixturePackage
from globalmail_agent.agent.understanding import Understanding, validate_sources
from globalmail_agent.application.commit_outcome import commit_outcome
from globalmail_agent.application.business_queries import BusinessQueries


class AgentToolTests(AgentFixture):
    def test_reused_order_source_repair_points_to_visible_history_without_reasking_customer(self):
        cid, _ = self.create_mail("My order is ORDER-ONE. The remote does not work.")
        self.append_mail(cid, "The earlier advice failed. What should I do next?")
        def value(messages, repaired=False):
            payload = json.loads(messages[1]["content"])
            history, current = payload["messages"][0], payload["messages"][-1]
            order = {"message_id": history["message_id"], "quote": "ORDER-ONE"}
            request = {"message_id": current["message_id"], "quote": current["body"]}
            return understanding(messages, order_candidates=[{"value": "ORDER-ONE", "sources": [order]}],
                intents=[{"business_type": "troubleshooting", "order_number": "ORDER-ONE", "target_item": "remote",
                    "condition": None, "requested_solution": "next supported option", "consent": "none",
                    "sources": [request, order] if repaired else [request]}])
        def repair(messages):
            self.assertIn("intent.sources quote containing that exact number", messages[-1]["content"])
            return value(messages, repaired=True)
        model = ScriptedModel(value, repair, terminal("We will review the failed advice for your existing order."))
        output, _ = self.execute(model)
        self.assertEqual(output.get("outcome"), "reply_and_wait", output)
        self.assertEqual(len(model.requests), 4)
        self.assertEqual(len(self.outbound(cid)), 1)

    def test_identity_mode_asof_sql_and_unknown_fields_are_rejected_before_execution(self):
        self.create_mail()
        _, _, budget, gateway = self.components()
        for forbidden in ("customer_id", "workspace_id", "mode", "as_of", "sql", "path", "release_id"):
            with self.subTest(field=forbidden):
                self.assert_error("tool_parameters_invalid", lambda: gateway.call(
                    call("get_case_context", {forbidden: "forged"})))
        for name in ("create_execution", "simulation_event", "run_shell", "send_email"):
            self.assert_error("tool_not_allowed", lambda: gateway.call(call(name, {})))
        for name in ("check_after_sales_eligibility", "create_after_sales_operation", "cancel_after_sales_operation"):
            self.assert_error("tool_not_allowed", lambda: gateway.call(call(name, {"workspace_id": "forged"})))
        self.assertEqual(self.count(a.tool_commands), 0)
        self.assertEqual(self.budget_row(gateway.job)["tool_calls"], 0)

    def test_order_candidate_needs_visible_source_and_cross_customer_query_is_denied(self):
        cid, _ = self.scene()
        scoped = BusinessQueries(self.engine).detail(cid)["data"]["orders"][0]["display_order_number"]
        self.append_mail(cid, "My order is " + scoped + ". Also mention OTHER-ORDER without granting access.")
        _, _, _, gateway = self.components()
        _, denied = gateway.call(call("get_order_snapshot", {"display_order_number": "UNMENTIONED-ORDER"}))
        self.assertEqual(denied["reason_code"], "order_number_without_source")
        _, foreign = gateway.call(call("get_order_snapshot", {"display_order_number": "OTHER-ORDER"}))
        self.assertEqual(foreign["status"], "denied")
        self.assertIsNone(foreign["data"])
        _, found = gateway.call(call("get_order_snapshot", {"display_order_number": scoped}))
        self.assertEqual(found["status"], "ok")
        self.assertEqual(found["data"]["orders"][0]["display_order_number"], scoped)

    def test_multiline_order_never_implicitly_selects_first_and_foreign_line_is_denied(self):
        package = FixturePackage()
        name = next(key for key, row in package.scenarios.items()
            if row["mode"] == "simulation" and sum(len(o["lines"]) for o in row["initial_state"]["orders"]) > 1)
        cid, _ = self.scene(name, package)
        detail = BusinessQueries(self.engine).detail(cid)
        order = detail["data"]["orders"][0]["display_order_number"]
        self.append_mail(cid, "My order is " + order + ", but I have not specified the affected item.")
        _, _, _, gateway = self.components()
        _, result = gateway.call(call("get_order_snapshot", {"display_order_number": order}))
        self.assertEqual(result["status"], "needs_input")
        self.assertIsNone(result["data"]["selected_line_id"])
        for name, args in (("search_reference", {"order_line_id": "OTHER-LINE", "query": "repair", "types": []}),
                ("get_shipment_status", {"order_line_id": "OTHER-LINE"}),
                ("get_item_availability", {"order_line_id": "OTHER-LINE", "item_id": "H-CTD16-US-BK"}),
                ("get_operation_status", {"operation_id": "OTHER-OPERATION"})):
            with self.subTest(tool=name):
                _, result = gateway.call(call(name, args))
                self.assertEqual(result["status"], "denied")
                if result["data"] is not None:
                    self.assertEqual(result["data"], {"missing_fields": ["order_line_id"]})

    def test_tool_receipt_same_key_replays_once_and_changed_arguments_conflict(self):
        self.create_mail()
        job, _, _, gateway = self.components()
        request = call("get_case_context", {}, "stable-command")
        first = gateway.call(request)
        self.assertEqual(gateway.call(request), first)
        self.assertEqual(self.count(a.tool_commands), 1)
        self.assertEqual(self.count(a.tool_calls), 1)
        self.assertEqual(self.budget_row(job)["tool_calls"], 1)
        self.assert_error("tool_command_conflict", lambda: gateway.call(
            call("get_order_snapshot", {"display_order_number": "ORDER-CHANGED"}, "stable-command")))

    def test_same_tool_args_without_new_information_stops_at_second_receipt(self):
        self.create_mail()
        job, _, _, gateway = self.components()
        gateway.call(call("get_case_context", {}))
        self.assert_error("no_progress", lambda: gateway.call(call("get_case_context", {})))
        self.assertEqual(self.count(a.tool_commands), 2)
        self.assertEqual(self.budget_row(job)["tool_calls"], 2)

    def test_reply_rejects_language_forged_reference_order_fact_and_unsupported_step(self):
        cid, _ = self.create_mail()
        job, context, _, _ = self.components()
        variants = [("reply_language_invalid", draft(language="de")),
            ("reply_citation_invalid", draft(citation_ids=[str(uuid4())])),
            ("reply_source_invalid", draft(claims=[{"kind": "customer_fact", "text": "Please share your order number.",
                "source_ids": ["invisible-message"]}])),
            ("order_fact_without_tool", draft(claims=[{"kind": "order_fact", "text": "Please share your order number.",
                "source_ids": []}])),
            ("product_step_without_evidence", draft(claims=[{"kind": "product_step", "text": "Please share your order number.",
                "source_ids": []}]))]
        for code, data in variants:
            with self.subTest(error=code):
                self.approve_fixture_draft(context, job, data)
                self.assert_error(code, lambda: commit_outcome(self.engine, self.store, context, job,
                    understanding([]), {"kind": "reply", "data": data}))
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.count(a.reply_artifacts), 0)

    def test_understanding_quotes_order_candidates_and_human_decisions_need_real_sources(self):
        self.create_mail("My order is ORDER-ONE. I already tried pairing.")
        _, context, _, _ = self.components()
        mail = context.payload["messages"][0]
        source = {"message_id": mail["message_id"], "quote": "ORDER-ONE"}
        valid = Understanding.model_validate(understanding([], order_candidates=[{"value": "ORDER-ONE", "sources": [source]}]))
        self.assertEqual(validate_sources(valid, context.payload)["order_candidates"][0]["value"], "ORDER-ONE")
        for code, value in (("understanding_source_invalid", understanding([], order_candidates=[
                {"value": "ORDER-ONE", "sources": [{"message_id": "future", "quote": "ORDER-ONE"}]}])),
            ("order_candidate_not_in_source", understanding([], order_candidates=[{"value": "ORDER-TWO", "sources": [source]}])),
            ("human_source_invalid", understanding([], facts=[{"key": "decision", "value": "Refund authorized",
                "kind": "human_decision", "sources": [source]}]))):
            self.assert_error(code, lambda: validate_sources(Understanding.model_validate(value), context.payload))

    def test_conditional_refund_keeps_two_intents_and_writes_no_after_sales_rows(self):
        cid, _ = self.create_mail("Where is my parcel? If it still does not arrive, I want a refund.")
        def conditional(messages):
            payload = json.loads(messages[-1]["content"])
            source = {"message_id": payload["messages"][-1]["message_id"], "quote": payload["messages"][-1]["body"]}
            common = {"order_number": None, "target_item": None, "requested_solution": None, "sources": [source]}
            return understanding(messages, intents=[{**common, "business_type": "shipment", "condition": None, "consent": "none"},
                {**common, "business_type": "refund", "condition": "If it still does not arrive", "consent": "conditional"}])
        from test_human_assistance import handoff
        model = ScriptedModel(conditional, handoff())
        output, job = self.execute(model)
        self.assertEqual(output["outcome"], "handoff", output)
        from globalmail_agent.application.run_records import RunRecords
        value = RunRecords(self.engine, self.store).get(job["run_id"])["understanding"]
        self.assertEqual([i["business_type"] for i in value["intents"]], ["shipment", "refund"])
        self.assertEqual(value["intents"][1]["consent"], "conditional")
        for table in (b.operations, b.executions, b.shipments, b.return_receipts):
            self.assertEqual(self.count(table), 0)
        self.assertEqual(len(self.outbound(cid)), 0)

    def test_historical_future_snapshot_and_simulation_policy_never_enter_model(self):
        package = FixturePackage()
        scenario = deepcopy(package.scenarios["SCN-029"])
        scenario["scenario_id"] = "AGENT-HISTORY-FUTURE"
        order = scenario["initial_state"]["orders"][0]
        order["source_kind"] = "historical_order_snapshot"
        order["snapshot_at"] = "2026-10-09T09:00:00+08:00"
        number = order["display_order_number"]
        scenario["initial_messages"][0]["body"] = "My order is " + number + ". Please check the status."
        package.scenarios[scenario["scenario_id"]] = scenario
        cid, rid = self.scene(scenario["scenario_id"], package)
        def candidate(messages):
            payload = json.loads(messages[-1]["content"])
            source = {"message_id": payload["messages"][-1]["message_id"], "quote": number}
            return understanding([], order_candidates=[{"value": number, "sources": [source]}])
        model = ScriptedModel(candidate, {"calls": [call("get_order_snapshot", {"display_order_number": number})]},
            terminal("The order snapshot is unavailable at this replay time."))
        output, job = self.execute(model)
        self.assertEqual(output.get("outcome"), "historical_comparison", output)
        decisions = [request for request in model.requests if request["tools"]]
        tool_messages = [message for message in decisions[-1]["messages"] if message["role"] == "tool"]
        self.assertEqual(len(tool_messages), 1)
        observed = json.loads(tool_messages[0]["content"])
        self.assertEqual(observed["status"], "unavailable")
        self.assertEqual(observed["reason_code"], "historical_snapshot_unavailable")
        self.assertEqual(observed["data"]["orders"], [])
        self.assertNotIn("H-CTD16", str(model.requests))
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.count(a.agent_run_dependencies), 0)
        self.assertEqual(self.count(b.operations), 0)

    def test_schema_pressure_keeps_scoped_reads_before_last_two_requests(self):
        from globalmail_agent.agent.budget import input_estimate
        from globalmail_agent.agent.tool_schemas import schemas
        cid, _ = self.scene()
        number = BusinessQueries(self.engine).detail(cid)["data"]["orders"][0]["display_order_number"]
        self.append_mail(cid, "My order is " + number + ". " + "Full customer detail. " * 200)
        def candidate(messages):
            payload = json.loads(messages[-1]["content"])
            source = {"message_id": payload["messages"][-1]["message_id"], "quote": number}
            return understanding([], order_candidates=[{"value": number, "sources": [source]}])
        def scoped_reads(messages):
            return {"calls": [call("request_human_review", {"reason": "cannot_decide",
                "summary": "Frozen engineering terminal after verifying legal read menu.",
                "gaps": ["Engineering fixture does not evaluate semantics."], "draft": ""})]}
        model = ScriptedModel(candidate, {"calls": [call("get_order_snapshot", {"display_order_number": number})]}, scoped_reads)
        output, job = self.execute(model)
        self.assertEqual(output.get("outcome"), "handoff", (output, len(model.requests)))
        request = model.requests[-1]
        names = {tool["function"]["name"] for tool in request["tools"]}
        estimates = (input_estimate(request["messages"], schemas()), input_estimate(request["messages"], request["tools"]))
        self.assertGreater(estimates[0], 16000, (estimates, names))
        self.assertLessEqual(estimates[1], 16000, (estimates, names))
        self.assertIn("search_reference", names, (estimates, names))
        self.assertIn("get_shipment_status", names)
        self.assertNotIn("revise_understanding", names)
        self.assertIn("Full customer detail. " * 200, request["messages"][1]["content"])
        self.assertEqual(self.budget_row(job)["model_requests"], 3)
        self.assertEqual(self.outbound(cid), [])

    def test_business_read_digest_allows_stable_ledger_and_rejects_silent_ledger_change(self):
        for change in (False, True):
            with self.subTest(ledger_changed=change):
                cid, _ = self.scene()
                number = BusinessQueries(self.engine).detail(cid)["data"]["orders"][0]["display_order_number"]
                self.append_mail(cid, "The order number is " + number + ".")
                job, context, _, gateway = self.components()
                identity, found = gateway.call(call("get_order_snapshot", {"display_order_number": number}))
                self.assertEqual(found["status"], "ok")
                body = "The order number is " + number + "."
                data = draft(body, claims=[{"kind": "order_fact", "text": body,
                    "source_ids": ["command:" + str(identity)]}])
                self.approve_fixture_draft(context, job, data)
                before = self.conversation(cid)
                if change:
                    with self.engine.begin() as conn:
                        branch = conn.execute(sa.select(b.simulation_branches.c.id).where(
                            b.simulation_branches.c.conversation_id == cid)).scalar_one()
                        stock = conn.execute(sa.select(b.inventory).where(b.inventory.c.branch_id == branch)
                            .order_by(b.inventory.c.id)).mappings().first()
                        conn.execute(b.inventory.update().where(b.inventory.c.id == stock["id"])
                            .values(on_hand=stock["on_hand"] + 1))
                    self.assertEqual(self.conversation(cid)["input_revision"], before["input_revision"])
                    self.assert_error("stale_business_context", lambda: commit_outcome(self.engine, self.store, context, job,
                        understanding([]), {"kind": "reply", "data": data}))
                    self.assertEqual(self.outbound(cid), [])
                else:
                    output = commit_outcome(self.engine, self.store, context, job, understanding([]),
                        {"kind": "reply", "data": data})
                    self.assertEqual(output["outcome"], "reply_and_wait")
                    self.assertEqual(len(self.outbound(cid)), 1)
