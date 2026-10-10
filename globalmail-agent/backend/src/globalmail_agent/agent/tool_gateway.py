"""Inject trusted scope, preserve receipts and expose only the already delivered services."""
import json
from uuid import UUID, uuid4, uuid5
import sqlalchemy as sa
from pydantic import ValidationError
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.adapters.body_store import BodyWriter, read_bytes
from globalmail_agent.adapters.knowledge_index_schema import evidence_refs
from globalmail_agent.adapters.knowledge_schema import document_versions
from globalmail_agent.application.business_queries import BusinessQueries
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.application.event_store import append_ui_event
from globalmail_agent.domain.orders import result
from globalmail_agent.agent.guard import guarded
from globalmail_agent.agent.tool_schemas import TOOLS, Draft, ReplyParts
from globalmail_agent.knowledge.base import canonical, sha
from globalmail_agent.knowledge.retrieval import KnowledgeSearch
from globalmail_agent.knowledge.index_commands import SearchCommand
from globalmail_agent.observability.tracing import observation


class ToolGateway:
    def __init__(self, engine, store, gateway, context, job, budget):
        self.engine, self.store, self.embedding = engine, store, gateway
        self.context, self.job, self.budget = context, job, budget
        self.business = BusinessQueries(engine, context.workspace_id)
        self.last_signature = None

    def call(self, call):
        metadata = {"tool_name": call["name"]} if call["name"] in TOOLS else {}
        with observation("tool", **metadata):
            return self._call(call)

    def _call(self, call):
        name = call["name"]
        if name == "create_reply_draft" and self.context.payload.get("execution_mode") == "human_assist":
            raise ServiceError("autonomous_reply_forbidden", 422)
        if name not in TOOLS:
            raise ServiceError("tool_not_allowed", 422)
        try:
            raw = json.loads(call["arguments"])
            if name == "create_reply_draft" and isinstance(raw, dict) and "body" not in raw:
                parts = ReplyParts.model_validate(raw)
                args = Draft.model_validate({**parts.model_dump(mode="json"),
                    "body": "\n\n".join(claim.text for claim in parts.claims)})
            else:
                # Explicit legacy bodies retain their original strict coverage gate.
                args = TOOLS[name].model_validate(raw)
        except (ValidationError, ValueError, TypeError):
            raise ServiceError("tool_parameters_invalid", 422) from None
        key = call["id"]
        payload = args.model_dump(mode="json")
        digest, identity = sha(canonical(payload)), uuid5(self.context.run_id, key)
        with guarded(self.engine, self.context.workspace_id, self.job) as (conn, conv, run, cycle):
            old = conn.execute(sa.select(a.tool_commands).where(a.tool_commands.c.id == identity)).mappings().first()
            if old and (old["name"] != name or old["payload_hash"] != digest):
                raise ServiceError("tool_command_conflict")
            if old and old["result_object_id"]:
                return identity, json.loads(read_bytes(conn, self.store, conv, old["result_object_id"]))
        self.budget.tool()
        with guarded(self.engine, self.context.workspace_id, self.job) as (conn, conv, run, cycle):
            if old is None:
                position = conn.execute(sa.select(sa.func.count()).select_from(a.tool_calls).where(a.tool_calls.c.run_id == run["id"])).scalar_one() + 1
                scope = {k: conv[k] for k in SCOPE_KEYS}
                conn.execute(sa.insert(a.tool_commands).values(id=identity, **scope, conversation_id=conv["id"],
                    run_id=run["id"], command_key=key, name=name, payload_hash=digest, arguments=payload, status="pending"))
                conn.execute(sa.insert(a.tool_calls).values(id=uuid4(), **scope, conversation_id=conv["id"], run_id=run["id"],
                    command_id=identity, provider_call_id=key, position=position))
        output = self.execute(name, args, identity)
        if name == "revise_understanding" and output["status"] == "ok":
            return identity, output  # Revision and receipt were committed in the same guarded transaction.
        with BodyWriter(self.store) as writer, guarded(self.engine, self.context.workspace_id, self.job) as (conn, conv, run, cycle):
            self.save_result(conn, writer, conv, run, name, identity, output)
        signature = (name, digest, sha(canonical({"status": output["status"], "data": output["data"],
            "reason_code": output["reason_code"], "resource_versions": output["resource_versions"]})))
        if name not in {"create_reply_draft", "request_human_review"} and signature == self.last_signature:
            raise ServiceError("no_progress")
        self.last_signature = signature
        if output["status"] == "error":
            raise ServiceError(output["reason_code"], 503)
        return identity, output

    def save_result(self, conn, writer, conv, run, name, identity, output):
        source = conn.execute(sa.select(a.agent_run_contexts.c.context_object_id).where(a.agent_run_contexts.c.run_id == run["id"])).scalar_one()
        object_id = writer.put(conn, conv, canonical(output).decode(), "agent_tool_result", (source,))
        conn.execute(a.tool_commands.update().where(a.tool_commands.c.id == identity)
            .values(status=output["status"], result_object_id=object_id))
        append_ui_event(conn, conv["id"], "agent.tool", {"run_id": str(run["id"]), "tool_name": name,
            "status": output["status"], "reason_code": output["reason_code"]})

    def _detail(self, **kwargs):
        return self.business.detail(self.context.conversation_id, **kwargs)

    def _line(self, line_id):
        output = self._detail(order_line_id=line_id)
        data = output.get("data") or {}
        if output["status"] not in {"ok", "needs_input"} or data.get("selected_line_id") != line_id:
            return output, None
        line = next((line for order in data["orders"] for line in order["lines"] if line["line_id"] == line_id), None)
        return output, line

    def execute(self, name, args, command_id=None):
        simulation = self.context.mode == "simulation"
        if name == "get_case_context":
            return result(data=self.context.payload, simulation=simulation, source_kind="visible_messages")
        if name == "get_order_snapshot":
            # Even a correct guessed order number is insufficient: require a visible source candidate.
            sources = [row["body"] for row in [*self.context.payload["messages"], *self.context.payload["human_notes"]]]
            if not any(args.display_order_number in body for body in sources) and args.display_order_number not in self.context.payload.get("visual_order_numbers", []):
                return result("denied", "order_number_without_source", simulation=simulation)
            output = self._detail(order_number=args.display_order_number)
            if output["data"]:
                output["data"] = {k: output["data"][k] for k in ("orders", "selected_line_id", "missing_fields")}
            return output
        if name in {"get_shipment_status", "get_after_sales_context"}:
            output, line = self._line(args.order_line_id)
            if line is None:
                return output
            data = output["data"]
            keys = ("shipments",) if name == "get_shipment_status" else ("operations", "executions", "returns", "customer_choices", "attempted_steps")
            output["data"] = {k: [r for r in data.get(k, []) if not r.get("order_line_id") or r["order_line_id"] == args.order_line_id] for k in keys}
            output["data"].update(order_line_id=args.order_line_id, policy_authorized=False,
                limitation="Read-only existing records. Customer support decides and operates in the business system; no application or execution authority.")
            return output
        if name == "get_operation_status":
            output = self._detail()
            data = output.get("data") or {}
            operations = [r for r in data.get("operations", []) if r["operation_id"] == args.operation_id]
            if not operations:
                return result("denied", "operation_out_of_scope", simulation=simulation)
            output["status"] = "ok"
            output["data"] = {"operations": operations, **{k: [r for r in data[k] if r.get("operation_id") == args.operation_id]
                for k in ("executions", "shipments", "returns")}}
            return output
        if name == "get_item_availability":
            return self.business.availability(self.context.conversation_id, args.order_line_id, args.item_id)
        if name == "search_reference":
            output, line = self._line(args.order_line_id)
            if line is None:
                return output
            if not simulation:
                return result("unavailable", "historical_manifest_unavailable")
            command = SearchCommand(query=args.query, sku=line["sku"], types=args.types,
                as_of=self.context.as_of, release_id=self.context.release_id, expected_release_epoch=self.context.release_epoch)
            with observation("retrieval"):
                found = KnowledgeSearch(self.engine, self.store, self.embedding, self.context.workspace_id).search(command)
            if found["reason"] == "stale_release":
                raise ServiceError("stale_release")
            if found["reason"] in {"provider_error", "incomplete_source"}:
                raise ServiceError("knowledge_" + found["reason"], 503)
            self.register(found["evidence"], line["sku"])
            return result("ok" if found["evidence"] else "empty", found["reason"],
                {"evidence": [{k: ref[k] for k in ("evidence_id", "title", "text", "source_kind", "completeness", "version_number")}
                    for ref in found["evidence"]]}, simulation=simulation,
                source_kind="published_knowledge", resource_versions={"release_epoch": self.context.release_epoch,
                    "business_digest": output["resource_versions"]["business_digest"]},
                evidence_refs=[{"evidence_id": r["evidence_id"]} for r in found["evidence"]])
        if name == "update_case_state":
            from globalmail_agent.agent.memory import update_candidates
            return update_candidates(self.engine, self.store, self.context, self.job, args)
        if name == "revise_understanding":
            from globalmail_agent.application.understanding_revisions import revise_understanding
            return revise_understanding(self.engine, self.store, self.context, self.job, args, command_id)
        if name in {"create_reply_draft", "request_human_review"}:
            with observation("response", tool_name=name):
                return result(data=args.model_dump(mode="json"), simulation=simulation, source_kind="model_proposal")
        raise ServiceError("tool_not_allowed", 422)

    def register(self, references, sku):
        with guarded(self.engine, self.context.workspace_id, self.job) as (conn, conv, run, cycle):
            for ref in references:
                identity = UUID(ref["evidence_id"])
                prior = conn.execute(sa.select(a.agent_run_dependencies.c.id).where(
                    a.agent_run_dependencies.c.run_id == run["id"], a.agent_run_dependencies.c.reference_id == identity)).scalar_one_or_none()
                if prior:
                    conn.execute(a.agent_run_dependencies.update().where(a.agent_run_dependencies.c.id == prior).values(active=True))
                    continue
                version = conn.execute(sa.select(document_versions).where(document_versions.c.id == UUID(ref["version_id"]))).mappings().one()
                conn.execute(sa.insert(a.agent_run_dependencies).values(id=uuid4(), **{k: conv[k] for k in SCOPE_KEYS},
                    conversation_id=conv["id"], run_id=run["id"], reference_id=identity, sku=sku,
                    document_id=UUID(ref["document_id"]), source_object_id=version["object_id"],
                    content_hash=ref["content_hash"], revocation_epoch=ref["revocation_epoch"]))
