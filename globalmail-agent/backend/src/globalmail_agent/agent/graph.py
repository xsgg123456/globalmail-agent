"""A single LangGraph dynamically chooses tools. Effects remain in CommitService."""
import json
import time
from typing import TypedDict
from pydantic import ValidationError
from langgraph.graph import StateGraph, START, END
from globalmail_agent.adapters.model_provider import prompt
from globalmail_agent.agent.understanding import Understanding, validate_sources
from globalmail_agent.agent.tool_schemas import Draft, schemas
from globalmail_agent.agent.budget import input_estimate, network_timeout
from globalmail_agent.agent.transcript import repair_history
from globalmail_agent.agent.outcome_validation import OutcomeReview, check_coverage, draft_hash
from globalmail_agent.agent.review_audit import trigger_units, audit_failure
from globalmail_agent.application.draft_validation import check_draft_sources
from globalmail_agent.agent.guard import guarded
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.base import canonical
from globalmail_agent.observability.local_records import save_understanding


class GraphState(TypedDict, total=False):
    messages: list[dict]
    understanding: dict | None
    calls: list[dict]
    proposal: dict | None
    repairs: int


class AgentGraph:
    def __init__(self, context, job, model, gateway, budget, checkpointer):
        self.context, self.job, self.model, self.gateway, self.budget = context, job, model, gateway, budget
        builder = StateGraph(GraphState)
        builder.add_node("understand", self.understand)
        builder.add_node("decide", self.decide)
        builder.add_node("tools", self.tools)
        builder.add_node("validate", self.validate)
        builder.add_edge(START, "understand")
        builder.add_conditional_edges("understand", lambda state: END if state.get("proposal") else "decide")
        builder.add_edge("decide", "tools")
        builder.add_conditional_edges("tools", lambda state: (END if state["proposal"]["kind"] == "handoff" else "validate")
            if state.get("proposal") else "decide")
        builder.add_conditional_edges("validate", lambda state: END if state.get("proposal") else "decide")
        self.graph = builder.compile(checkpointer=checkpointer)

    def request(self, messages, stage, *, schema=None, tools=None, image_views=()):
        for attempt in range(2):
            schema_budget = tools or ([schema] if schema else [])
            key = self.budget.reserve(messages, stage, self.model.model, schema_budget, image_views)
            output = None
            try:
                remaining = (120000 - self.budget.active_ms()) / 1000
                if remaining <= 0:
                    raise ServiceError("budget_exhausted")
                options = {}
                if image_views:
                    from globalmail_agent.attachments.views import load_authorized_view
                    options = {"image_views": image_views, "image_loader": lambda ref: load_authorized_view(
                        self.gateway.engine, self.gateway.store, self.context, self.job, ref)}
                output = self.model.request(messages, schema=schema, tools=tools,
                    timeout=min(network_timeout(stage), remaining), **options)
            except ServiceError as error:
                if attempt == 0 and error.code in {"model_timeout", "model_rate_limited", "model_unavailable"}:
                    time.sleep(0.25)
                    continue
                raise
            finally:
                self.budget.settle(key, output.get("usage") if output else None,
                    output.get("request_id") if output else None)
            if output["finish_reason"] in {"length", "content_filter"}:
                raise ServiceError("model_output_incomplete", 503)
            return output

    def understand(self, state):
        payload = self.context.payload
        from globalmail_agent.attachments.views import prepare_authorized_image_views
        from globalmail_agent.attachments.understanding import VisualUnderstanding, visual_sources, authorized_order_numbers, vision_schema, apply_manual_corrections
        refs = prepare_authorized_image_views(self.gateway.engine, self.gateway.store, self.context, self.job) if payload.get("attachments") else []
        definition = VisualUnderstanding if refs else Understanding
        if refs:
            payload["image_views"] = [{"attachment_id": r["attachment_id"], "location": r["location"]} for r in refs]
            payload["unread_attachments"] = [r for r in payload["attachments"] if r["attachment_id"] not in {v["attachment_id"] for v in refs}]
        messages = [{"role": "system", "content": prompt("understanding")},
            {"role": "user", "content": canonical(payload).decode()}]
        if refs:
            messages.append({"role": "system", "content": prompt("visual-understanding")})
        last_code = "understanding_schema_invalid"
        for attempt in range(2):
            reused = payload.get("reused_understanding")
            output = {"content": canonical(reused).decode()} if reused else self.request(
                messages, "understanding", schema=vision_schema() if refs else definition.model_json_schema(), image_views=refs)
            try:
                value = definition.model_validate_json(output["content"])
                raw_images = []
                if refs:
                    payload["visual_sources"].update(visual_sources(value, refs))
                    from globalmail_agent.agent.understanding import Risk, SourceRef
                    for image in value.images:
                        for kind in image.risk_flags:
                            value.risk_flags.append(Risk(kind=kind, sources=[SourceRef(
                                message_id="image:" + image.attachment_id, quote=kind)]))
                    payload["visual_order_numbers"] = authorized_order_numbers(value, payload)
                    raw_images = [i.model_dump(mode="json") for i in value.images]
                    value = apply_manual_corrections(value, payload)
                    payload["visual_sources"].update(visual_sources(value, refs))
                business_sources = None
                if reused:
                    from globalmail_agent.agent.guard import guarded
                    from globalmail_agent.application.understanding_revisions import tool_sources
                    with guarded(self.gateway.engine, self.context.workspace_id, self.job) as (conn, conv, run, cycle):
                        business_sources = tool_sources(conn, self.gateway.store, conv, run["id"])
                value = validate_sources(value, payload, tool_sources=business_sources)
                if refs:
                    from globalmail_agent.knowledge.base import sha
                    value.update(image_views=refs, visual_context_hash=sha(canonical(payload)))
                    value["_visual_raw_images"] = raw_images
                if value["risk_flags"]:
                    from globalmail_agent.application.risk_handoff import risk_handoff
                    risk_handoff(self.gateway.engine, self.gateway.store, self.context, self.job, value)
                elif not reused:
                    save_understanding(self.gateway.engine, self.gateway.store, self.context.workspace_id, self.job, value)
                decision = [{"role": "system", "content": prompt("decision")},
                    {"role": "user", "content": canonical({"context": payload, "understanding": value}).decode()}]
                risk = value["risk_flags"]
                return {"understanding": value, "messages": decision, "calls": [], "repairs": 0,
                    "proposal": {"kind": "handoff", "data": {"reason": "safety_risk",
                        "summary": "客户报告危险迹象，暂停自动处理：" + ", ".join(r["kind"] for r in risk),
                        "gaps": ["需要人工核查安全风险及后续处置"], "draft": ""}} if risk else None}
            except (ValidationError, json.JSONDecodeError, ServiceError) as error:
                if isinstance(error, ServiceError) and error.code not in {
                        "understanding_source_invalid", "order_candidate_not_in_source", "human_source_invalid",
                        "visual_coverage_invalid", "visual_unreadable_has_facts", "visual_order_ambiguous", "visual_source_kind_invalid"}:
                    raise
                last_code = error.code if isinstance(error, ServiceError) else "understanding_schema_invalid"
                # Do not put unvalidated response text back into model history.
                hint = (" Each non-null intent.order_number needs an intent.sources quote containing that exact number "
                    "from visible mail (current or historical), even when order_candidates already cites it. Add that source "
                    "alongside the current request; do not ask the customer again or invent a number."
                    if last_code == "order_candidate_not_in_source" else "")
                messages.append({"role": "user", "content": "Fix JSON and exact source quotes. Error: " + last_code + hint})
        raise ServiceError(last_code, 503)

    def decide(self, state):
        allowed = None
        candidates = [*state["understanding"]["order_candidates"],
            *[intent["order_number"] for intent in state["understanding"]["intents"] if intent["order_number"]]]
        if not candidates and not self.context.payload.get("verified_business_observations"):
            allowed = {"get_case_context", "create_reply_draft", "request_human_review", "update_case_state", "revise_understanding"}
        messages = [*state["messages"], {"role": "system", "content": prompt("grounding")}]
        tools = schemas(allowed)
        from globalmail_agent.agent.tool_menu import stage_tools
        tools, application_ready = stage_tools(tools, state, self.context)
        if self.context.mode != "simulation":
            from globalmail_agent.agent.tools.after_sales import NAMES as after_sales_tools
            tools = [tool for tool in tools if tool["function"]["name"] not in after_sales_tools]
        remaining = self.budget.remaining_requests()
        if remaining <= 1:
            tools = schemas({"request_human_review"})
        elif remaining <= 2:
            # Keep every observation; reserve the last request for independent reply validation.
            tools = schemas({"create_reply_draft", "request_human_review"})
        elif input_estimate(messages, tools) > 16000:
            # Candidate writes may wait; keep scoped reads available while their requests fit.
            read_and_terminal = set(schema["function"]["name"] for schema in tools) - {
                "get_case_context", "update_case_state", "revise_understanding"}
            if not application_ready:
                from globalmail_agent.agent.tools.after_sales import NAMES
                read_and_terminal -= NAMES
            tools = schemas(read_and_terminal)
            if application_ready and input_estimate(messages, tools) > 16000:
                tools = schemas({'create_after_sales_operation', 'get_operation_status', 'create_reply_draft', 'request_human_review'})
                if input_estimate(messages, tools) > 16000:
                    tools = schemas({'create_after_sales_operation', 'request_human_review'})
            if input_estimate(messages, tools) > 16000:
                tools = schemas({"create_reply_draft", "request_human_review"})
        if input_estimate(messages, tools) > 16000:
            # A sourced handoff can still fit when the larger reply schema cannot.
            tools = schemas({"request_human_review"})
        output = self.request(messages, "decision", tools=tools)
        if not output["calls"]:
            raise ServiceError("model_tool_response_invalid", 503)
        declared = {tool["function"]["name"] for tool in tools}
        if any(call["name"] not in declared for call in output["calls"]):
            raise ServiceError("model_tool_not_allowed", 503)
        message = {"role": "assistant", "content": None, "tool_calls": [{"id": call["id"], "type": "function",
            "function": {"name": call["name"], "arguments": call["arguments"]}} for call in output["calls"]]}
        return {"messages": [*state["messages"], message], "calls": output["calls"]}

    def tools(self, state):
        messages, proposal, repairs = list(state["messages"]), None, state["repairs"]
        understanding = state["understanding"]
        for call in state["calls"]:
            if proposal:
                raise ServiceError("tool_after_terminal_proposal", 422)
            try:
                identity, output = self.gateway.call(call)
            except ServiceError as error:
                if error.code != "tool_parameters_invalid" or repairs >= 1:
                    raise
                repairs += 1
                messages.append({"role": "tool", "tool_call_id": call["id"],
                    "content": canonical({"status": "error", "reason_code": error.code}).decode()})
                continue
            data = {**output, "command_source_id": "command:" + str(identity)}
            messages.append({"role": "tool", "tool_call_id": call["id"], "content": canonical(data).decode()})
            if call["name"] == "revise_understanding" and output["status"] == "ok":
                from globalmail_agent.agent.guard import guarded
                from globalmail_agent.application.understanding_revisions import current_understanding
                with guarded(self.gateway.engine, self.context.workspace_id, self.job) as (conn, conv, run, cycle):
                    understanding = current_understanding(conn, self.gateway.store, conv, run["id"])
                    self.context.payload["case_revision"] = conv["case_revision"]
                messages[1] = {"role": "user", "content": canonical({
                    "context": self.context.payload, "understanding": understanding}).decode()}
            if call["name"] in {"create_reply_draft", "request_human_review"}:
                proposal = {"kind": "reply" if call["name"] == "create_reply_draft" else "handoff", "data": output["data"]}
        return {"messages": messages, "understanding": understanding, "proposal": proposal, "repairs": repairs, "calls": []}

    def invoke(self):
        return self.graph.invoke({"messages": [], "understanding": None, "calls": [], "proposal": None, "repairs": 0},
            {"configurable": {"thread_id": str(self.context.run_id)}, "recursion_limit": 32}, durability="sync")

    def validate(self, state):
        code, audit_error = None, None
        try:
            check_coverage(state["proposal"]["data"])
            with guarded(self.gateway.engine, self.context.workspace_id, self.job) as (conn, conv, run, cycle):
                check_draft_sources(conn, self.gateway.store, self.context, state["understanding"],
                    Draft.model_validate(state["proposal"]["data"]))
        except ServiceError as error:
            if error.code not in {"reply_body_required", "reply_claims_incomplete", "reply_source_invalid",
                    "reply_language_invalid", "reply_citation_invalid", "product_step_without_evidence",
                    "order_fact_without_tool", "customer_fact_without_message", "visual_fact_without_evidence"}:
                raise
            code = error.code
        if code is None:
            review_messages = [{"role": "system", "content": prompt("validation")}, {"role": "user", "content": canonical({
                "context": self.context.payload, "understanding": state["understanding"],
                "observations": self.observations(state),
                "trigger_units": trigger_units(self.context.payload),
                "draft": state["proposal"]["data"]}).decode()},
                {"role": "system", "content": prompt("validation-grounding")}]
            review_schema = OutcomeReview.model_json_schema()
            observations = self.observations(state)
            decoded = [json.loads(row['content']) for row in observations]
            if any(isinstance(value.get('data'), dict) and
                    ('condition_fields' in value['data'] or 'operation' in value['data']) for value in decoded):
                from globalmail_agent.agent.tool_schemas import compact_schema
                payload = json.loads(review_messages[1]['content'])
                payload['observations'] = [{**row, 'content': value} for row, value in zip(observations, decoded)]
                review_messages[1]['content'] = canonical(payload).decode()
                review_schema = compact_schema(review_schema)
            output = self.request(review_messages, "validation", schema=review_schema)
            try:
                review = OutcomeReview.model_validate_json(output["content"])
            except (ValidationError, ValueError):
                raise ServiceError("outcome_validation_invalid", 503) from None
            audit_error = audit_failure(review, self.context.payload, self.observations(state),
                Draft.model_validate(state["proposal"]["data"]))
            if audit_error or not review.supported or not review.language_correct or review.unsupported_claims:
                code = "reply_grounding_invalid"
        if code:
            if state["repairs"] >= 1:
                raise ServiceError(code, 422)
            reason = ('Deterministic audit rejected: ' + audit_error.code +
                '. Recheck every original request and quote only exact scoped source text.'
                if audit_error and audit_error.binding else review.reason if "review" in locals() else code)
            repair = (" Copy every complete draft paragraph into claims.text exactly from body, including greeting/sign-off. "
                "Do not put customer/source quotes in claims.text; supporting IDs belong in source_ids."
                if code in {"reply_claims_incomplete", "reply_source_invalid"} else "")
            if code in {"customer_fact_without_message", "order_fact_without_tool"}:
                repair += (" Courtesy is clarification with []; case/human facts cite actual message or human_note IDs "
                    "as customer_fact. Ledger order_fact needs an actual business command:<id>, never invented sources.")
            return {"proposal": None, "repairs": state["repairs"] + 1,
                "messages": [*repair_history(state["messages"]), {"role": "user", "content":
                    "Draft rejected: " + code + ". Rebuild a fully sourced draft or request human review. " + reason + repair}]}
        import sqlalchemy as sa
        from globalmail_agent.adapters.agent_schema import agent_run_contexts
        with guarded(self.gateway.engine, self.context.workspace_id, self.job) as (conn, conv, run, cycle):
            conn.execute(agent_run_contexts.update().where(agent_run_contexts.c.run_id == run["id"])
                .values(validated_draft_hash=draft_hash(state["proposal"]["data"])))
        return {}

    @staticmethod
    def observations(state):
        terminal_ids = {call["id"] for message in state["messages"] if message["role"] == "assistant"
            for call in message.get("tool_calls", []) if call["function"]["name"] in
            {"create_reply_draft", "request_human_review"}}
        return [message for message in state["messages"] if message["role"] == "tool"
            and message["tool_call_id"] not in terminal_ids]
