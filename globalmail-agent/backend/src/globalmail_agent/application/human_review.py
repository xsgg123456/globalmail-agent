from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import insert, select, update
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.adapters.conversation_schema import human_reviews, messages, replay_cursors, case_issues
from globalmail_agent.application.task_queue import invalidate
from globalmail_agent.application.event_store import append_ui_event
from globalmail_agent.application.conversation_lock import ServiceError


class HumanReviewMixin:
    def open_review(self, conn, conversation):
        return conn.execute(select(human_reviews).where(human_reviews.c.conversation_id == conversation["id"],
            human_reviews.c.status == "open")).mappings().first()

    def dependencies(self, conn, conversation):
        from globalmail_agent.attachments.evidence import context_images
        image_objects = context_images(conn, self.store, conversation)[3]
        return (*tuple(conn.execute(select(messages.c.body_object_id).where(
            messages.c.conversation_id == conversation["id"], messages.c.seq <= conversation["visible_message_seq"])).scalars())
            , *image_objects)

    def takeover(self, conversation_id, command, key):
        def action(conn, writer):
            conversation = self.lock(conn, conversation_id, command.expected_version)
            if conversation["lifecycle"] != "open":
                raise ServiceError("conversation_not_open")
            invalidate(conn, conversation_id)
            self.update(conn, conversation, processing_owner="human_review", auto_run_gate="disabled",
                authority_epoch=conversation["authority_epoch"] + 1, scheduling_state="idle")
            review = self.open_review(conn, conversation)
            review_id = review["id"] if review else uuid4()
            if review is None:
                as_of = conn.execute(select(replay_cursors.c.as_of).where(
                    replay_cursors.c.conversation_id == conversation_id)).scalar()
                conn.execute(insert(human_reviews).values(id=review_id, **{k: conversation[k] for k in SCOPE_KEYS},
                    conversation_id=conversation_id, status="open", input_revision=conversation["input_revision"],
                    reason="人工主动接管", visible_message_seq=conversation["visible_message_seq"], as_of=as_of,
                    note_object_id=writer.put(conn, conversation, command.reason, "human_takeover_note",
                        self.dependencies(conn, conversation))))
            append_ui_event(conn, conversation_id, "human.takeover", {"review_id": str(review_id),
                "row_version": conversation["row_version"]})
            return {"conversation_id": str(conversation_id), "review_id": str(review_id), "version": conversation["row_version"]}
        return self.write(key, "conversation.takeover:" + str(conversation_id), command, action)

    def save_review(self, review_id, command, key):
        def action(conn, writer):
            review = conn.execute(select(human_reviews).where(human_reviews.c.id == review_id,
                human_reviews.c.workspace_id == self.workspace_id)).mappings().first()
            if review is None:
                raise ServiceError("review_not_found", 404)
            conversation = self.lock(conn, review["conversation_id"])
            review = self.open_review(conn, conversation)
            if review is None or review["id"] != review_id or review["version"] != command.expected_version:
                raise ServiceError("stale_review")
            if command.expected_input_revision > conversation["input_revision"]:
                raise ServiceError("invalid_input_revision", 422)
            dependencies = self.dependencies(conn, conversation)
            draft = writer.put(conn, conversation, command.draft, "human_draft", dependencies) if command.draft else None
            note = writer.put(conn, conversation, command.note, "human_note", dependencies) if command.note else None
            conn.execute(update(human_reviews).where(human_reviews.c.id == review_id).values(
                draft_object_id=draft, note_object_id=note, version=review["version"] + 1,
                input_revision=command.expected_input_revision))
            append_ui_event(conn, conversation["id"], "human.saved", {"review_id": str(review_id)})
            return {"review_id": str(review_id), "version": review["version"] + 1}
        return self.write(key, "human_review.save:" + str(review_id), command, action)

    def human_reply(self, conversation_id, command, key):
        def action(conn, writer):
            conversation = self.lock(conn, conversation_id, command.expected_version)
            if conversation["input_revision"] != command.expected_input_revision:
                raise ServiceError("stale_input_revision")
            review = self.open_review(conn, conversation)
            if review is None or conversation["processing_owner"] != "human_review":
                raise ServiceError("human_review_required")
            dependencies = self.dependencies(conn, conversation)
            body_object = writer.put(conn, conversation, command.body, "human_reply", dependencies)
            note_object = (writer.put(conn, conversation, command.note, "human_note", dependencies)
                           if command.note else review["note_object_id"])
            from globalmail_agent.application.risk_records import resolve_risks
            if command.risk_decision != "keep_active" and not command.note.strip():
                raise ServiceError("risk_decision_requires_evidence", 422)
            resolve_risks(conn, conversation, review, command.risk_decision, note_object)
            if conversation["mode"] == "simulation":
                message = self.add_message(conn, writer, conversation, command.body, command.subject,
                    "simulated_human", "human", key, datetime.now(timezone.utc))
                # Formal artificial outbound body is derived from all inputs, same transaction.
                from globalmail_agent.application.content_dependencies import register_dependencies
                register_dependencies(conn, {k: conversation[k] for k in SCOPE_KEYS},
                                      message["body_object_id"], dependencies)
                self.update(conn, conversation, visible_message_seq=message["seq"],
                    received_seq=message["received_seq"], human_reply_after_seq=message["received_seq"],
                    processing_owner="human_wait_customer", scheduling_state="waiting_customer",
                    authority_epoch=conversation["authority_epoch"] + 1)
            else:
                self.update(conn, conversation, processing_owner="human_wait_customer",
                    human_reply_after_seq=conversation["received_seq"], scheduling_state="waiting_customer",
                    authority_epoch=conversation["authority_epoch"] + 1)
            conn.execute(update(human_reviews).where(human_reviews.c.id == review["id"]).values(status="completed",
                reply_object_id=body_object, note_object_id=note_object, version=review["version"] + 1,
                input_revision=conversation["input_revision"]))
            append_ui_event(conn, conversation_id, "human.completed", {"review_id": str(review["id"]),
                "row_version": conversation["row_version"]})
            return {"conversation_id": str(conversation_id), "review_id": str(review["id"]), "version": conversation["row_version"]}
        return self.write(key, "conversation.human_reply:" + str(conversation_id), command, action)

    def close(self, conversation_id, command, key):
        def action(conn, writer):
            conversation = self.lock(conn, conversation_id, command.expected_version)
            invalidate(conn, conversation_id)
            review = self.open_review(conn, conversation)
            if command.note:
                note = writer.put(conn, conversation, command.note, "human_closure_note",
                                  self.dependencies(conn, conversation))
                if review is None:
                    review_id = uuid4()
                    conn.execute(insert(human_reviews).values(id=review_id, **{k: conversation[k] for k in SCOPE_KEYS},
                        conversation_id=conversation_id, status="closed", input_revision=conversation["input_revision"],
                        reason="人工结案", note_object_id=note))
                else:
                    conn.execute(update(human_reviews).where(human_reviews.c.id == review["id"])
                                 .values(note_object_id=note, status="closed", version=review["version"] + 1))
            elif review:
                conn.execute(update(human_reviews).where(human_reviews.c.id == review["id"])
                             .values(status="closed", version=review["version"] + 1))
            self.update(conn, conversation, lifecycle="resolved", auto_run_gate="disabled",
                processing_owner="human_wait_customer", scheduling_state="idle",
                authority_epoch=conversation["authority_epoch"] + 1)
            conn.execute(update(case_issues).where(case_issues.c.conversation_id == conversation_id)
                         .values(status="resolved", version=case_issues.c.version + 1))
            append_ui_event(conn, conversation_id, "conversation.closed", {"row_version": conversation["row_version"]})
            return {"conversation_id": str(conversation_id), "version": conversation["row_version"]}
        return self.write(key, "conversation.close:" + str(conversation_id), command, action)
