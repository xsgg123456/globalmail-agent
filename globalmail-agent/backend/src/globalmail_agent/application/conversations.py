from datetime import datetime, timezone
from sqlalchemy import select
from globalmail_agent.adapters.conversation_schema import identities, conversations, messages
from globalmail_agent.application.conversation_lock import DEFAULT_DATASET_ID, ServiceError
from globalmail_agent.application.conversation_base import ServiceBase
from globalmail_agent.application.conversation_queries import QueryMixin
from globalmail_agent.application.replay import ReplayMixin
from globalmail_agent.application.human_review import HumanReviewMixin


class ConversationService(ServiceBase, QueryMixin, ReplayMixin, HumanReviewMixin):
    def create(self, command, key):
        if command.expected_version != 0:
            raise ServiceError("initial_version_required", 422)
        def action(conn, writer):
            # Lock the instance slot before identity selection so concurrent first mails converge.
            from globalmail_agent.adapters.conversation_schema import agent_slots
            conn.execute(select(agent_slots).where(agent_slots.c.workspace_id == self.workspace_id,
                agent_slots.c.slot_key == "agent").with_for_update()).first()
            existing = conn.execute(select(conversations).join(identities, conversations.c.identity_id == identities.c.id)
                .where(identities.c.workspace_id == self.workspace_id, identities.c.dataset_id == DEFAULT_DATASET_ID,
                       identities.c.mode == "simulation", identities.c.sender_key == command.sender_email)).mappings().first()
            conversation = (self.lock(conn, existing["id"]) if existing else
                self.new_conversation(conn, command.sender_email, "simulation", command.subject, True, "manual"))
            message = self.add_message(conn, writer, conversation, command.body, command.subject,
                "customer", "manual", key, datetime.now(timezone.utc))
            from globalmail_agent.attachments.binding import bind_attachments
            bind_attachments(conn, conversation, message, command.attachments)
            from globalmail_agent.attachments.importing import save_metadata
            save_metadata(conn, conversation, message, command.attachment_metadata)
            return self.accept(conn, writer, conversation, message)
        return self.write(key, "conversation.create", command, action)

    def append(self, conversation_id, command, key):
        def action(conn, writer):
            conversation = self.lock(conn, conversation_id, command.expected_version)
            if conversation["mode"] != "simulation":
                raise ServiceError("historical_messages_read_only")
            source_id = command.source_message_id or key
            existing = conn.execute(select(messages).where(messages.c.conversation_id == conversation_id,
                messages.c.source_ref == "manual", messages.c.source_message_id == source_id)).mappings().first()
            if existing:
                from globalmail_agent.adapters.body_store import read_body
                if read_body(conn, self.store, conversation, existing["body_object_id"]) != command.body or existing["subject"] != command.subject:
                    raise ServiceError("source_message_conflict")
                from globalmail_agent.attachments.binding import assert_same_manifest
                assert_same_manifest(conn, conversation, existing, command.attachments)
                from globalmail_agent.attachments.importing import assert_metadata
                assert_metadata(conn, conversation, existing, command.attachment_metadata)
                return {"conversation_id": str(conversation_id), "message_id": str(existing["id"]),
                        "version": conversation["row_version"]}
            message = self.add_message(conn, writer, conversation, command.body, command.subject,
                "customer", "manual", source_id, datetime.now(timezone.utc))
            from globalmail_agent.attachments.binding import bind_attachments
            bind_attachments(conn, conversation, message, command.attachments)
            from globalmail_agent.attachments.importing import save_metadata
            save_metadata(conn, conversation, message, command.attachment_metadata)
            return self.accept(conn, writer, conversation, message)
        return self.write(key, "conversation.append:" + str(conversation_id), command, action)
