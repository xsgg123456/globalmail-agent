from uuid import uuid4
from sqlalchemy import insert, select, update, func
from globalmail_agent.adapters.body_store import BodyWriter
from globalmail_agent.adapters.conversation_schema import conversations, identities, messages
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.application.conversation_lock import (
    DEFAULT_WORKSPACE_ID, DEFAULT_DATASET_ID, ServiceError, lock_conversation)
from globalmail_agent.application.idempotency import prior, remember
from globalmail_agent.application.event_store import append_ui_event, record_event
from globalmail_agent.application.task_queue import enqueue, invalidate
from globalmail_agent.application.case_memory import rebuild


class ServiceBase:
    def __init__(self, engine, store, workspace_id=DEFAULT_WORKSPACE_ID):
        self.engine, self.store, self.workspace_id = engine, store, workspace_id

    def write(self, key, operation, command, action):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)
        payload = command.model_dump(mode="json")
        with BodyWriter(self.store) as writer:
            with self.engine.begin() as conn:
                result, digest = prior(conn, self.workspace_id, key, operation, payload)
                if result is not None:
                    return result
                result = action(conn, writer)
                remember(conn, self.workspace_id, key, operation, digest, result)
                return result

    def lock(self, conn, conversation_id, expected_version=None):
        return lock_conversation(conn, conversation_id, self.workspace_id, expected_version)

    def new_conversation(self, conn, sender_key, mode, subject, verified, source_ref, dataset=None):
        identity, conversation = uuid4(), uuid4()
        dataset = dataset or DEFAULT_DATASET_ID
        conn.execute(insert(identities).values(id=identity, workspace_id=self.workspace_id,
            dataset_id=dataset, mode=mode, sender_key=sender_key, verified=verified, source_ref=source_ref))
        values = dict(id=conversation, workspace_id=self.workspace_id, dataset_id=dataset,
            branch_id=uuid4(), customer_id=identity, purpose="conversation", identity_id=identity,
            mode=mode, subject=subject)
        conn.execute(insert(conversations).values(**values))
        return self.lock(conn, conversation)

    def update(self, conn, conversation, **values):
        values.setdefault("row_version", conversation["row_version"] + 1)
        conn.execute(update(conversations).where(conversations.c.id == conversation["id"])
                     .values(**values, updated_at=func.now()))
        conversation.update(values)
        return conversation

    def add_message(self, conn, writer, conversation, body, subject, sender,
                    source_ref, source_message_id, sent_at):
        seq = conn.execute(select(func.coalesce(func.max(messages.c.seq), 0)).where(
            messages.c.conversation_id == conversation["id"])).scalar_one() + 1
        object_id = writer.put(conn, conversation, body, "message_body")
        value = dict(id=uuid4(), **{k: conversation[k] for k in SCOPE_KEYS},
            conversation_id=conversation["id"], seq=seq, received_seq=conversation["received_seq"] + 1,
            source_ref=source_ref, source_message_id=source_message_id, sender=sender,
            subject=subject, body_object_id=object_id, sent_at=sent_at)
        conn.execute(insert(messages).values(**value))
        return value

    def accept(self, conn, writer, conversation, message, *, historical=False):
        invalidate(conn, conversation["id"])
        owner = conversation["processing_owner"]
        closed = conversation["lifecycle"] == "resolved"
        internal = conversation.get("persistent_human", False) and not closed
        if internal:
            owner = "human_review"
        elif owner == "human_wait_customer" and not closed:
            owner = "agent"
        gate = "disabled" if closed or internal else "open" if owner == "agent" else conversation["auto_run_gate"]
        self.update(conn, conversation, visible_message_seq=message["seq"],
            received_seq=message["received_seq"], input_revision=conversation["input_revision"] + 1,
            lifecycle="resolved" if closed else "open", processing_owner=owner, auto_run_gate=gate,
            human_reply_after_seq=None if owner == "agent" else conversation["human_reply_after_seq"],
            scheduling_state="idle")
        visible = list(conn.execute(select(messages).where(messages.c.conversation_id == conversation["id"],
            messages.c.seq <= conversation["visible_message_seq"]).order_by(messages.c.seq)).mappings())
        if not closed:
            rebuild(conn, writer, self.store, conversation, visible, message["sent_at"])
        if internal:
            from globalmail_agent.application.human_assistance import ensure_review
            ensure_review(conn, conversation, as_of=message["sent_at"])
        event = record_event(conn, conversation, "message", str(message["id"]),
            "customer_message.accepted", {"message_id": str(message["id"])}, suppressed=owner != "agent")
        task = enqueue(conn, conversation, event) if not closed and (owner == "agent" or internal) else {}
        append_ui_event(conn, conversation["id"], "replay.advanced" if historical else "message.accepted",
            {"conversation_id": str(conversation["id"]), "message_id": str(message["id"]),
             "row_version": conversation["row_version"], "input_revision": conversation["input_revision"], **task})
        return {"conversation_id": str(conversation["id"]), "message_id": str(message["id"]),
                "version": conversation["row_version"], **task}
