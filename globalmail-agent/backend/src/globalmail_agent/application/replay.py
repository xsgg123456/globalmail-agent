from uuid import uuid4
from sqlalchemy import insert, select, update
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.adapters.import_loader import validate_case, payload_hash
from globalmail_agent.adapters.conversation_schema import data_imports, messages, replay_cursors, agent_runs
from globalmail_agent.application.conversation_lock import ServiceError


class ReplayMixin:
    def import_case(self, command, key):
        validate_case(command)
        def action(conn, writer):
            # Source duplicate serialization is separate from the request-key receipt.
            from sqlalchemy import text
            conn.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"),
                {"key": str(self.workspace_id) + command.source_ref + ":" + command.source_conversation_id})
            digest = payload_hash(command.model_dump(mode="json"))
            prior = conn.execute(select(data_imports).where(data_imports.c.workspace_id == self.workspace_id,
                data_imports.c.source_ref == command.source_ref,
                data_imports.c.source_conversation_id == command.source_conversation_id)).mappings().first()
            if prior:
                if prior["payload_hash"] != digest:
                    raise ServiceError("source_import_conflict")
                conversation = self.lock(conn, prior["conversation_id"])
                return {"conversation_id": str(conversation["id"]), "version": conversation["row_version"], "duplicate": True}
            conversation = self.new_conversation(conn,
                "独立案例:" + command.source_conversation_id, "historical_replay",
                command.messages[0].subject, False, command.source_ref, dataset=uuid4())
            imported = []
            for item in command.messages:
                message = self.add_message(conn, writer, conversation, item.body, item.subject,
                    item.sender, command.source_ref, item.source_message_id, item.sent_at)
                imported.append(message)
                conversation["received_seq"] = message["received_seq"]
            first = imported[0]
            conversation["received_seq"] = 0
            conn.execute(insert(data_imports).values(id=uuid4(), workspace_id=self.workspace_id,
                source_ref=command.source_ref, source_conversation_id=command.source_conversation_id,
                split=command.split, group_id=command.group_id, payload_hash=digest, conversation_id=conversation["id"]))
            total = sum(m["sender"] == "customer" for m in imported)
            conn.execute(insert(replay_cursors).values(id=uuid4(), **{k: conversation[k] for k in SCOPE_KEYS},
                conversation_id=conversation["id"], position=1, total_customer_messages=total,
                as_of=first["sent_at"], finished=total == 1))
            return self.accept(conn, writer, conversation, first, historical=True)
        return self.write(key, "conversation.import", command, action)

    def next(self, conversation_id, command, key):
        def action(conn, writer):
            conversation = self.lock(conn, conversation_id, command.expected_version)
            if conversation["mode"] != "historical_replay":
                raise ServiceError("historical_mode_required")
            active = conn.execute(select(agent_runs.c.id).where(agent_runs.c.conversation_id == conversation_id,
                agent_runs.c.status.in_(["queued", "running"]))).first()
            if active:
                raise ServiceError("current_run_not_terminal")
            if self.open_review(conn, conversation) is not None:
                raise ServiceError("human_review_not_completed")
            cursor = conn.execute(select(replay_cursors).where(replay_cursors.c.conversation_id == conversation_id))
            cursor = cursor.mappings().one()
            upcoming = conn.execute(select(messages).where(messages.c.conversation_id == conversation_id,
                messages.c.sender == "customer", messages.c.seq > conversation["visible_message_seq"])
                .order_by(messages.c.seq)).mappings().first()
            if upcoming is None:
                return {"conversation_id": str(conversation_id), "version": conversation["row_version"], "finished": True}
            # Historical review remains a comparison; the next actual prefix regains agent ownership.
            conversation["processing_owner"] = "agent"
            conn.execute(update(replay_cursors).where(replay_cursors.c.id == cursor["id"])
                .values(position=cursor["position"] + 1, as_of=upcoming["sent_at"],
                        finished=cursor["position"] + 1 == cursor["total_customer_messages"]))
            return self.accept(conn, writer, conversation, upcoming, historical=True)
        return self.write(key, "conversation.next:" + str(conversation_id), command, action)
