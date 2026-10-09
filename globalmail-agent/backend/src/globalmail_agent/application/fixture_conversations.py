"""Creating a dataset is the only business write in Phase 4."""
from uuid import uuid4
from sqlalchemy import insert
from globalmail_agent.adapters.conversation_schema import replay_cursors, human_reviews
from globalmail_agent.adapters.fixture_loader import FixturePackage
from globalmail_agent.adapters.fixture_ledger import load_branch
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.application.conversation_base import ServiceBase
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.domain.orders import timestamp


class FixtureConversations(ServiceBase):
    def __init__(self, engine, store, package=None):
        super().__init__(engine, store)
        self.package = package or FixturePackage()

    def list(self):
        return self.package.list()

    def create(self, scenario_id, command, key):
        if command.expected_version != 0:
            raise ServiceError("initial_version_required", 422)
        scenario = self.package.scenarios.get(scenario_id)
        if scenario is None:
            raise ServiceError("scenario_not_found", 404)

        def action(conn, writer):
            conversation = self.new_conversation(conn, scenario["conversation"]["sender"],
                scenario["mode"], scenario_id, True, scenario["source_ref"], dataset=uuid4())
            load_branch(conn, conversation, scenario, self.package)
            human = scenario["conversation"].get("processing_owner") in {"human", "human_review"}
            if human:
                self.update(conn, conversation, processing_owner="human_review", auto_run_gate="disabled",
                    authority_epoch=conversation["authority_epoch"] + 1)
            added = []
            for item in scenario["initial_messages"]:
                sender = "customer" if item["direction"] == "INBOUND" else "historical_staff"
                message = self.add_message(conn, writer, conversation, item["body"], scenario_id,
                    sender, scenario["source_ref"], item["message_id"], timestamp(item["received_at"]))
                added.append(message)
                from globalmail_agent.attachments.importing import save_metadata
                save_metadata(conn, conversation, message, [*item.get("attachments", []),
                    *item.get("attachment_metadata", [])], writer=writer, package=self.package)
                conversation["received_seq"] = message["received_seq"]
            if scenario["mode"] == "historical_replay":
                current = next(m for m in added if m["sender"] == "customer")
                conn.execute(insert(replay_cursors).values(id=uuid4(), **{k: conversation[k] for k in SCOPE_KEYS},
                    conversation_id=conversation["id"], position=1,
                    total_customer_messages=sum(m["sender"] == "customer" for m in added),
                    as_of=current["sent_at"], finished=len(added) == 1))
            else:
                current = added[-1]
            conversation["received_seq"] = current["received_seq"] - 1
            result = self.accept(conn, writer, conversation, current, historical=scenario["mode"] == "historical_replay")
            if human:
                review_id = uuid4()
                conn.execute(insert(human_reviews).values(id=review_id, **{k: conversation[k] for k in SCOPE_KEYS},
                    conversation_id=conversation["id"], status="open", input_revision=conversation["input_revision"],
                    reason="资料场景初始人工接管", visible_message_seq=conversation["visible_message_seq"],
                    as_of=current["sent_at"]))
                result["review_id"] = str(review_id)
            return result

        try:
            return self.write(key, "business.scenario:" + scenario_id, command, action)
        except (ValueError, KeyError, TypeError):
            raise ServiceError("fixture_unavailable", 503) from None
