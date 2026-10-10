"""Independent Stage 1 probes. Synthetic fixtures, isolated PG schemas only."""
import json
from uuid import uuid4
from pathlib import Path
from datetime import datetime, timedelta, timezone
import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from alembic import command as migrations
from alembic.config import Config
from agent_fixture import AgentFixture, ScriptedModel, call, understanding
from test_human_assistance import handoff
from globalmail_agent.domain.conversation import HumanReply, ReviewDraft, Close, Command
from globalmail_agent.application.run_records import RunRecords
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.application.business_queries import BusinessQueries
from globalmail_agent.application.branch_facts import BranchFactsService
from globalmail_agent.application.conversation_advice import ConversationAdvice
from globalmail_agent.domain.business_events import BranchFact
from vision_fixture import VisionFixture, VisionModel, image_output, handoff as image_handoff
from globalmail_agent.attachments.corrections import EvidenceService, EvidenceCommand
from globalmail_agent.adapters.body_store import BodyWriter
from globalmail_agent.adapters.schema import SCOPE_KEYS
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID


class FormalMigrationProbes(AgentFixture):
    def test_old_commercial_run_objects_and_image_preserved_on_0010(self):
        self.preserve_upgrade()

    def test_previously_claimed_commercial_conversation_is_consistent_with_review(self):
        self.preserve_upgrade(prior_owner="human_wait_customer")

    def preserve_upgrade(self, prior_owner="agent"):
        namespace = "test_formal_0010_" + uuid4().hex
        with self.admin.begin() as conn:
            conn.execute(sa.text(f'CREATE SCHEMA "{namespace}"'))
        def cleanup():
            with self.admin.begin() as conn:
                conn.execute(sa.text(f'DROP SCHEMA "{namespace}" CASCADE'))
        self.addCleanup(cleanup)
        engine = sa.create_engine(self.admin.url, hide_parameters=True,
            connect_args={"options": f"-csearch_path={namespace}"})
        self.addCleanup(engine.dispose)
        config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
        with engine.begin() as conn:
            config.attributes["connection"] = conn
            migrations.upgrade(config, "0009_business_waits")
        with BodyWriter(self.store) as writer, engine.begin() as conn:
            old = sa.MetaData()
            old.reflect(conn, schema=namespace)
            table = lambda name: old.tables[namespace + "." + name]
            cid, identity, dataset, branch, message, cycle, run, job, aid = [uuid4() for _ in range(9)]
            scope = dict(workspace_id=DEFAULT_WORKSPACE_ID, mode="simulation", branch_id=branch,
                customer_id=identity, purpose="conversation")
            conv = dict(id=cid, **scope)
            now = datetime.now(timezone.utc)
            active = prior_owner == "agent"
            conn.execute(table("identities").insert().values(id=identity, workspace_id=DEFAULT_WORKSPACE_ID,
                mode="simulation", dataset_id=dataset, sender_key="legacy-review@example.test",
                verified=True, source_ref="isolated-legacy"))
            conn.execute(table("conversations").insert().values(**conv, dataset_id=dataset, identity_id=identity,
                subject="Legacy refund", input_revision=1, visible_message_seq=1, received_seq=1,
                processing_owner=prior_owner, auto_run_gate="open" if active else "disabled",
                scheduling_state="running" if active else "waiting_customer"))
            body = writer.put(conn, conv, "I request a refund.", "message_body")
            source = writer.put_bytes(conn, conv, b"legacy-image-source", "customer_attachment")
            conn.execute(table("messages").insert().values(id=message, **scope, conversation_id=cid,
                seq=1, received_seq=1, source_ref="isolated-legacy", source_message_id="legacy-first",
                sender="customer", subject="Legacy refund", body_object_id=body, sent_at=now))
            if not active:
                staff_body = writer.put(conn, conv, "Staff is checking your request.", "human_reply", (body,))
                conn.execute(table("messages").insert().values(id=uuid4(), **scope, conversation_id=cid,
                    seq=2, received_seq=2, source_ref="human", source_message_id=uuid4().hex,
                    sender="simulated_human", subject="Legacy refund", body_object_id=staff_body, sent_at=now))
                conn.execute(table("conversations").update().where(table("conversations").c.id == cid).values(
                    visible_message_seq=2, received_seq=2, human_reply_after_seq=2))
                conn.execute(table("human_reviews").insert().values(id=uuid4(), **scope,
                    conversation_id=cid, status="completed", input_revision=1, reason="Previous staff reply",
                    visible_message_seq=1, reply_object_id=staff_body))
            conn.execute(table("case_issues").insert().values(id=uuid4(), **scope, conversation_id=cid,
                issue_key="legacy-refund", business_type="refund", source_message_id=message, status="open", version=1))
            versions = dict(input_revision=1, authority_epoch=0, branch_generation=1)
            trigger = uuid4()
            conn.execute(table("processing_cycles").insert().values(id=cycle, **scope, **versions,
                conversation_id=cid, trigger_id=trigger, trigger_message_id=message, state="running" if active else "completed"))
            conn.execute(table("agent_runs").insert().values(id=run, **scope, **versions,
                conversation_id=cid, processing_cycle_id=cycle, trigger_id=trigger, attempt_no=1,
                status="running" if active else "handed_off", checkpoint_writable=active))
            conn.execute(table("jobs").insert().values(id=job, **scope, conversation_id=cid, run_id=run,
                cycle_id=cycle, kind="agent", status="running" if active else "completed", attempt_no=1, slot_fence=7,
                lease_owner="legacy-worker", lease_expires_at=now + timedelta(seconds=60) if active else None))
            conn.execute(table("agent_slots").update().where(table("agent_slots").c.slot_key == "agent").values(
                job_id=job if active else None, lease_owner="legacy-worker" if active else None,
                lease_expires_at=now + timedelta(seconds=60) if active else None, fence=7))
            conn.execute(table("message_attachments").insert().values(id=aid, **scope, conversation_id=cid,
                message_id=message, position=0, filename="legacy.png", mime_type="image/png", size_bytes=19,
                source_object_id=source, source_sha256=__import__("hashlib").sha256(b"legacy-image-source").hexdigest(),
                status="processing" if active else "understood", processing_run_id=run, expires_at=now + timedelta(days=1)))
            conn.execute(table("usage_records").insert().values(id=uuid4(), **scope, conversation_id=cid,
                run_id=run, request_key="legacy-call", stage="understanding", status="known",
                estimated_input=20, reserved_tokens=2020, input_tokens=20, output_tokens=10, model="qwen3.7-plus"))
            preserved = {name: [dict(r) for r in conn.execute(sa.select(table(name))).mappings()]
                for name in ("objects", "messages", "identities", "case_issues", "usage_records")}
            config.attributes["connection"] = conn
            migrations.upgrade(config, "0010_human_assistance")
            current = sa.MetaData()
            current.reflect(conn, schema=namespace)
            new = lambda name: current.tables[namespace + "." + name]
            for name, rows in preserved.items():
                latest = {row["id"]: row for row in conn.execute(sa.select(new(name))).mappings()}
                for before in rows:
                    self.assertEqual({key: latest[before["id"]][key] for key in before}, before, name)
            conv = conn.execute(sa.select(new("conversations"))).mappings().one()
            run_row = conn.execute(sa.select(new("agent_runs"))).mappings().one()
            image = conn.execute(sa.select(new("message_attachments"))).mappings().one()
            slot = conn.execute(sa.select(new("agent_slots")).where(new("agent_slots").c.slot_key == "agent")).mappings().one()
            self.assertTrue(conv["persistent_human"])
            self.assertEqual(run_row["status"], "interrupted" if active else "handed_off")
            self.assertFalse(run_row["checkpoint_writable"])
            self.assertIsNone(slot["job_id"])
            self.assertGreater(slot["fence"], 7)
            self.assertEqual(conn.execute(sa.select(new("usage_records").c.request_state)).scalar_one(), "not_recorded")
            self.assertEqual(self.store._path(source).read_bytes(), b"legacy-image-source")
            print("PROBE migration_0010", {"persistent_human": conv["persistent_human"],
                "run_status": run_row["status"], "slot_fence": slot["fence"],
                "image_status": image["status"], "conversation_state": conv["scheduling_state"],
                "objects_preserved": len(preserved["objects"])})
            self.assertEqual(image["status"], "failed" if active else "understood")
            if active:
                self.assertIsNone(image["processing_run_id"])
            self.assertNotEqual(conv["scheduling_state"], "running")
            if prior_owner == "human_wait_customer":
                self.assertTrue(conv["human_claimed"])
                open_review = conn.execute(sa.select(new("human_reviews").c.id).where(
                    new("human_reviews").c.conversation_id == cid,
                    new("human_reviews").c.status == "open")).scalar_one_or_none()
                print("PROBE migrated_staff", {"processing_owner": conv["processing_owner"],
                    "human_claimed": conv["human_claimed"], "open_review": bool(open_review)})
                self.assertTrue(conv["processing_owner"] != "human_review" or open_review,
                    "Migration claims active human-review authority without a usable review")
