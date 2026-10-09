"""Interrupted analysis is not a completed visual result."""
from globalmail_agent.adapters.attachment_schema import message_attachments


def interrupt_images(conn, run_ids):
    conn.execute(message_attachments.update().where(message_attachments.c.processing_run_id.in_(run_ids),
        message_attachments.c.status == "processing").values(status="failed", processing_run_id=None,
            failure_reason="analysis_interrupted"))
