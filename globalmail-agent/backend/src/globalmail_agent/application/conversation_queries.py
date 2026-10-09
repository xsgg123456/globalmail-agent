from uuid import UUID
from sqlalchemy import select, and_, or_
from globalmail_agent.adapters.body_store import read_body
from globalmail_agent.adapters.conversation_schema import (
    conversations, identities, messages, human_reviews, agent_runs, case_issues, case_facts, replay_cursors)
from globalmail_agent.application.conversation_lock import ServiceError


class QueryMixin:
    def present_conversation(self, conn, row):
        result = dict(row)
        identity = conn.execute(select(identities).where(identities.c.id == row["identity_id"])).mappings().one()
        result.update(mode="interactive_simulation" if row["mode"] == "simulation" else row["mode"],
                      sender_key=identity["sender_key"], identity_verified=identity["verified"])
        return result

    def present_review(self, conn, conversation, row):
        result = dict(row)
        for field, column in (("draft", "draft_object_id"), ("note", "note_object_id"), ("reply", "reply_object_id")):
            result[field] = read_body(conn, self.store, conversation, row[column])
        return result

    def list(self, mode=None, limit=50, cursor=None, state=None):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)
        with self.engine.connect() as conn:
            query = select(conversations).where(conversations.c.workspace_id == self.workspace_id,
                conversations.c.lifecycle.not_in(["deleting", "deleted"]))
            if mode:
                query = query.where(conversations.c.mode == ("simulation" if mode == "interactive_simulation" else mode))
            if state:
                field = (conversations.c.processing_owner if state in {"human_review", "human_wait_customer"}
                         else conversations.c.lifecycle if state == "resolved" else conversations.c.scheduling_state)
                query = query.where(field == state)
            if cursor:
                anchor = conn.execute(select(conversations).where(conversations.c.id == cursor,
                    conversations.c.workspace_id == self.workspace_id)).mappings().first()
                if anchor is None:
                    raise ServiceError("invalid_cursor", 422)
                query = query.where(or_(conversations.c.created_at < anchor["created_at"],
                    and_(conversations.c.created_at == anchor["created_at"], conversations.c.id < anchor["id"])))
            rows = list(conn.execute(query.order_by(conversations.c.created_at.desc(), conversations.c.id.desc())
                                     .limit(limit + 1)).mappings())
            return {"items": [self.present_conversation(conn, r) for r in rows[:limit]],
                    "next_cursor": str(rows[limit - 1]["id"]) if len(rows) > limit else None}

    def detail(self, conversation_id):
        if self.engine is None:
            raise ServiceError("database_unavailable", 503)
        # A repeatable snapshot prevents a concurrent advance exposing mixed-cutpoint rows.
        with self.engine.connect().execution_options(isolation_level="REPEATABLE READ") as conn:
            with conn.begin():
                conversation = conn.execute(select(conversations).where(conversations.c.id == conversation_id,
                    conversations.c.workspace_id == self.workspace_id,
                    conversations.c.lifecycle.not_in(["deleting", "deleted"]))).mappings().first()
                if conversation is None:
                    raise ServiceError("conversation_not_found", 404)
                visible = list(conn.execute(select(messages).where(messages.c.conversation_id == conversation_id,
                    messages.c.seq <= conversation["visible_message_seq"]).order_by(messages.c.seq)).mappings())
                mail = [{**dict(m), "body": read_body(conn, self.store, conversation, m["body_object_id"])} for m in visible]
                reviews = list(conn.execute(select(human_reviews).where(human_reviews.c.conversation_id == conversation_id)
                                           .order_by(human_reviews.c.created_at)).mappings())
                current = next((r for r in reversed(reviews) if r["status"] == "open"), None)
                facts = list(conn.execute(select(case_facts).where(case_facts.c.conversation_id == conversation_id,
                    case_facts.c.visible_seq <= conversation["visible_message_seq"])).mappings())
                cursor = conn.execute(select(replay_cursors).where(
                    replay_cursors.c.conversation_id == conversation_id)).mappings().first()
                from globalmail_agent.application.risk_records import active_risks
                return {"conversation": self.present_conversation(conn, conversation), "messages": mail,
                    "active_risks": active_risks(conn, self.store, conversation) if conversation["mode"] == "simulation" else [],
                    "review": self.present_review(conn, conversation, current) if current else None,
                    "human_history": [self.present_review(conn, conversation, r) for r in reviews if r["status"] != "open"],
                    "comparisons": [self.present_review(conn, conversation, r) for r in reviews
                        if r["status"] != "open"] if conversation["mode"] == "historical_replay" else [],
                    "runs": [dict(r) for r in conn.execute(select(agent_runs).where(agent_runs.c.conversation_id == conversation_id)
                        .order_by(agent_runs.c.created_at)).mappings()],
                    "issues": [dict(r) for r in conn.execute(select(case_issues).where(case_issues.c.conversation_id == conversation_id)).mappings()],
                    "facts": [{**dict(f), "value": read_body(conn, self.store, conversation, f["value_object_id"])} for f in facts],
                    "replay": dict(cursor) if cursor else None}
