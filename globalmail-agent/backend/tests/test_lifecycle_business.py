"""Deleting a simulation releases its occupancy but retains body-free deduplication."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import sqlalchemy as sa
from agent_fixture import AgentFixture
from globalmail_agent.adapters import business_schema as b, conversation_schema as c
from globalmail_agent.application.lifecycle import LifecycleService


class BusinessDeletionTests(AgentFixture):
    def test_branch_source_snapshots_erased_ledger_ids_and_other_branch_preserved(self):
        cid, _ = self.scene("BASE-OUTON-04")
        other, _ = self.scene("BASE-OUTON-04")
        with self.engine.connect() as conn:
            old = conn.execute(sa.select(c.conversations).where(c.conversations.c.id == cid)).mappings().one()
            sibling = conn.execute(sa.select(c.conversations).where(c.conversations.c.id == other)).mappings().one()
            ledger = list(conn.execute(sa.select(b.operations.c.id, b.operations.c.status, b.operations.c.amount_minor)
                .where(b.operations.c.branch_id == old["branch_id"])))
            before = list(conn.execute(sa.select(b.branch_orders.c.source_snapshot)
                .where(b.branch_orders.c.branch_id == sibling["branch_id"])).scalars())
        service = LifecycleService(self.engine, self.store,
            SimpleNamespace(lifecycle_journal_root=Path(self.temp.name) / "journal"))
        request = service.request("conversation", cid, service.preview("conversation", cid)["expected_version"])
        with patch("globalmail_agent.observability.purge.PurgeService.purge_runs", return_value=True):
            result = service.process(request["id"])
        self.assertEqual(result["status"], "completed", result)
        with self.engine.connect() as conn:
            self.assertEqual(list(conn.execute(sa.select(b.operations.c.id, b.operations.c.status, b.operations.c.amount_minor)
                .where(b.operations.c.branch_id == old["branch_id"]))), ledger)
            self.assertTrue(all(v == {} for v in conn.execute(sa.select(b.branch_orders.c.source_snapshot)
                .where(b.branch_orders.c.branch_id == old["branch_id"])).scalars()))
            self.assertEqual(list(conn.execute(sa.select(b.branch_orders.c.source_snapshot)
                .where(b.branch_orders.c.branch_id == sibling["branch_id"])).scalars()), before)
            self.assertTrue(conn.execute(sa.select(c.identities.c.sender_key)
                .where(c.identities.c.id == old["identity_id"])).scalar_one().startswith("deleted:"))
