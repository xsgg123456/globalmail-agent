"""ID-only revocation watermark and hidden review holders for browser read recovery."""
import sqlalchemy as sa
from globalmail_agent.adapters.lifecycle_schema import deletion_requests


def revoked_content(conn, conversation):
    rows = conn.execute(sa.select(deletion_requests.c.journal_seq, deletion_requests.c.manifest).where(
        deletion_requests.c.workspace_id == conversation['workspace_id'],
        deletion_requests.c.manifest['conversation_ids'].contains([str(conversation['id'])]))).mappings().all()
    return (max((row['journal_seq'] for row in rows), default=0),
        {identity for row in rows for identity in row['manifest']['holders'].get('human_reviews', [])})
