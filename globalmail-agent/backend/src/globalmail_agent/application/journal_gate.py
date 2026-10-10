"""An external tombstone without its transaction receipt closes access after a crash."""
import sqlalchemy as sa
from globalmail_agent.adapters.deletion_journal import DeletionJournal
from globalmail_agent.adapters.lifecycle_schema import journal_receipts


def assert_journal_current(engine, store):
    if engine is None:
        return
    root = getattr(store, "lifecycle_journal_root", None) or store.root.parent / (store.root.name + "-lifecycle")
    with engine.connect() as conn:
        receipts = {str(row.request_id): row.seq for row in conn.execute(sa.select(journal_receipts))}
    if not root.exists() and not receipts:
        return
    try:
        records, _ = DeletionJournal(root).read_verified()
        expected = {record["request_id"]: record["seq"] for record in records}
        if receipts != expected:
            raise RuntimeError("journal_replay_required")
    except (OSError, ValueError, KeyError):
        raise RuntimeError("journal_replay_required") from None
