"""Add durable lifecycle requests without changing existing deletion tombstones."""
from alembic import op
import sqlalchemy as sa
from globalmail_agent.adapters.lifecycle_schema import deletion_requests, journal_receipts

revision = "0012_lifecycle"
down_revision = "0011_observability"
branch_labels = depends_on = None


def upgrade():
    deletion_requests.create(op.get_bind(), checkfirst=True)
    journal_receipts.create(op.get_bind(), checkfirst=True)
    conn = op.get_bind()
    # Permit only body-column erasure in an active, scoped deletion transaction.
    # Ordinary UPDATE retains every pre-existing immutability trigger.
    conn.execute(sa.text("""CREATE OR REPLACE FUNCTION lifecycle_scrub_allowed(before_row jsonb, after_row jsonb)
    RETURNS boolean LANGUAGE plpgsql AS $$
    DECLARE request deletion_requests%ROWTYPE; allowed text[];
    BEGIN
      IF nullif(current_setting('globalmail.deletion_request', true), '') IS NULL THEN RETURN false; END IF;
      SELECT * INTO request FROM deletion_requests
        WHERE id = current_setting('globalmail.deletion_request', true)::uuid AND status IN ('purging','verifying');
      IF NOT FOUND OR before_row->>'workspace_id' <> request.workspace_id::text THEN RETURN false; END IF;
      allowed := ARRAY['source_snapshot','details','decision_data','state','tool_overrides','result',
        'text','structure','basis','note','exclusion_reason','excluded_block_ids','rules','rule_schema',
        'description','asset_map','title','diagnostics','status','reference','manifest','manifest_sha256',
        'source_ref','source_reference','filename','asset_key','lifecycle'];
      IF before_row - allowed <> after_row - allowed THEN RETURN false; END IF;
      IF before_row->>'id' = request.target_id::text
        OR request.manifest->'version_ids' ? (before_row->>'id')
        OR request.manifest->'cache_ids' ? (before_row->>'id')
        OR request.manifest->'cache_ids' ? (before_row->>'cache_id')
        OR request.manifest->'object_ids' ? (before_row->>'object_id')
        OR request.manifest->'version_ids' ? (before_row->>'version_id')
        OR before_row->>'document_id' = request.target_id::text
        OR before_row->>'manifest' LIKE '%' || request.target_id::text || '%'
        OR EXISTS (SELECT 1 FROM conversations c WHERE request.manifest->'conversation_ids' ? c.id::text
          AND c.branch_id::text = before_row->>'branch_id' AND c.workspace_id = request.workspace_id)
      THEN RETURN true; END IF;
      RETURN false;
    END $$"""))
    for name in ("immutable_business_source", "immutable_knowledge", "immutable_knowledge_index"):
        original = conn.execute(sa.text("SELECT pg_get_functiondef(oid) FROM pg_proc "
            "WHERE proname=:name AND pronamespace=current_schema()::regnamespace"), {"name": name}).scalar_one()
        addition = "BEGIN\n IF lifecycle_scrub_allowed(to_jsonb(OLD), to_jsonb(NEW)) THEN RETURN NEW; END IF;"
        conn.execute(sa.text(original.replace("BEGIN", addition, 1)))


def downgrade():
    raise RuntimeError("Deletion tombstones cannot be downgraded safely")
