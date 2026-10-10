"""External revocations survive restoration of an older database snapshot."""
from uuid import uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.lifecycle_schema import journal_receipts
from globalmail_agent.adapters.deletion_journal import DeletionJournal


def record_revocation(conn, store, workspace, kind, identity):
    root = getattr(store, "lifecycle_journal_root", None) or store.root.parent / (store.root.name + "-lifecycle")
    journal = DeletionJournal(root)
    if conn.execute(sa.select(journal_receipts.c.request_id).limit(1)).first():
        journal.read_verified()
    else:
        journal.initialize()
    saved = journal.append({"action": "withdraw" if kind == "document" else "revoke",
        "target_type": kind, "target_id": str(identity), "workspace_id": str(workspace),
        "request_id": str(uuid4())})
    from uuid import UUID
    conn.execute(journal_receipts.insert().values(request_id=UUID(saved["request_id"]),
        workspace_id=workspace, seq=saved["seq"]))
    return saved
