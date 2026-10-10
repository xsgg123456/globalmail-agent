"""Fresh final-review collision probe; no DB, model or external network."""
import sys
from pathlib import Path
from uuid import UUID, uuid4
from unittest.mock import patch

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "globalmail-agent/backend/src"))
from globalmail_agent.observability.sdk_export import SdkExport
from globalmail_agent.settings import Settings

transport = SdkExport(Settings(langfuse_public_key="pk-lf-" + uuid4().hex,
    langfuse_secret_key="final-review-test-only"))
try:
    first = UUID("11111111-1111-1111-abcd-123456789012")
    second = UUID("22222222-2222-2222-abcd-123456789012")
    metadata = dict(run_id=str(uuid4()), workspace_id=str(uuid4()), branch_id=str(uuid4()),
        conversation_id=str(uuid4()), mode="simulation", started_ns=1, ended_ns=3)
    rows = [dict(observation_id=str(identity), node="context", status="completed", started_ns=1, ended_ns=2)
        for identity in (first, second)]
    media = transport.client._resources._media_manager
    with patch.object(media, "_find_and_process_media", wraps=media._find_and_process_media) as traversal:
        try:
            transport.build(uuid4().hex, dict(metadata=metadata, observations=rows))
        except ValueError as error:
            assert str(error) == "sdk_receipt_identity_conflict"
        else:
            raise AssertionError("low64 collision accepted")
        traversal.assert_not_called()
    print("PASS: distinct UUIDs with identical low64 are rejected before SDK media traversal")
finally:
    transport.close()
