"""Isolated real PG, deterministic HTTP boundaries, no paid model or real traces."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import os
import subprocess
import sys
from threading import Event
from time import time_ns
from uuid import UUID, uuid5, uuid4
import httpx
import sqlalchemy as sa
from agent_fixture import AgentFixture
import test_observability as baseline
from globalmail_agent.adapters import agent_schema as a
from globalmail_agent.adapters.schema import deletion_journal, SCOPE_KEYS
from globalmail_agent.observability.purge import PurgeService
from globalmail_agent.observability.sdk_export import SdkExport


class Remote:
    def __init__(self):
        self.rows, self.requests = [], []
        self.delete_ready, self.offline = True, False
        self.ack_unknown = False
        self.lose_delete_response = False
        self.entered, self.release = Event(), Event()
        self.release.set()

    def send(self, trace_id, value):
        self.entered.set()
        assert self.release.wait(5)
        identities = [uuid5(UUID(value["metadata"]["run_id"]), "run")]
        identities += [identity for identity, _ in SdkExport.ordered(value)]
        self.rows = [{"id": f"{SdkExport._span_id(identity):016x}", "traceId": trace_id,
            "startTime": datetime.now(timezone.utc).isoformat(), "projectId": "isolated", "type": "SPAN"}
            for identity in identities]
        return not self.ack_unknown

    def reconcile(self, trace_id, value):
        return False

    def close(self):
        pass

    def http(self, request):
        self.requests.append((request.method, request.url.path))
        if self.offline:
            raise httpx.ConnectError("isolated offline fixture")
        if request.method == "DELETE":
            if self.delete_ready:
                self.rows.clear()
            if self.lose_delete_response:
                self.lose_delete_response = False
                raise httpx.ReadTimeout("isolated lost delete response")
            return httpx.Response(200, json={"message": "Deletion scheduled"})
        assert request.url.path == "/api/public/v2/observations"
        return httpx.Response(200, json={"data": self.rows, "meta": {}})


class ObservabilityPurgeTests(AgentFixture):
    settings = baseline.ObservabilityTests.settings
    observer = baseline.ObservabilityTests.observer
    run_mail = baseline.ObservabilityTests.run_mail

    def purge(self, observer, remote):
        return PurgeService(self.engine, self.store, observer.records.settings,
            http_transport=httpx.MockTransport(remote.http))

    def trace(self, rid):
        return self.row(a.trace_correlations, a.trace_correlations.c.run_id == rid)

    def test_exported_trace_and_root_deleted_before_success(self):
        remote = Remote()
        observer = self.observer(remote)
        _, rid, job, _, _ = self.run_mail(observer)
        observer.exporter.export_one(rid)
        generation = self.trace(rid)["generation"]
        self.assertTrue(self.purge(observer, remote).purge_runs([rid]))
        self.assertEqual(remote.rows, [])
        self.assertEqual(self.trace(rid)["generation"], generation + 1)
        self.assertEqual(self.trace(rid)["reason_code"], "observability_purged")
        observer.records.persist(job, [], time_ns(), False)
        observer.records.mark(rid, "pending")
        observer.exporter.export_one(rid)
        self.assertEqual(self.trace(rid)["export_status"], "revoked")
        self.assertEqual(sum(method == "DELETE" for method, _ in remote.requests), 1)

    def test_revoked_public_buffer_still_allows_private_cleanup_read(self):
        remote = Remote()
        observer = self.observer(remote)
        _, rid, _, _, _ = self.run_mail(observer)
        observer.exporter.export_one(rid)
        trace = self.trace(rid)
        with self.engine.begin() as conn:
            conn.execute(deletion_journal.insert().values(id=uuid4(),
                **{k: trace[k] for k in SCOPE_KEYS}, target_object_id=trace["export_object_id"],
                generation=1, state="revoked"))
        self.assertTrue(self.purge(observer, remote).purge_runs([rid]))
        self.assertEqual(remote.rows, [])

    def test_unknown_ack_is_deleted_and_offline_retries_keep_fence(self):
        remote = Remote()
        remote.ack_unknown = True
        observer = self.observer(remote)
        _, rid, _, _, _ = self.run_mail(observer)
        observer.exporter.export_one(rid)
        self.assertEqual(self.trace(rid)["reason_code"], "observability_ack_unknown")
        remote.offline = True
        purge = self.purge(observer, remote)
        self.assert_error("observability_purge_unavailable", lambda: purge.purge_runs([rid]))
        self.assertEqual(self.trace(rid)["export_status"], "revoked")
        remote.offline = False
        self.assertTrue(purge.purge_runs([rid]))

    def test_async_delete_acceptance_is_not_completion_and_retry_works(self):
        remote = Remote()
        remote.delete_ready = False
        observer = self.observer(remote)
        _, rid, _, _, _ = self.run_mail(observer)
        observer.exporter.export_one(rid)
        purge = self.purge(observer, remote)
        self.assert_error("observability_purge_unconfirmed", lambda: purge.purge_runs([rid]))
        self.assertEqual(self.trace(rid)["reason_code"], "observability_purge_pending")
        remote.delete_ready = True
        remote.rows.clear()  # The asynchronous server finishes between requests.
        self.assertTrue(purge.purge_runs([rid]))

    def test_lost_delete_response_retries_by_confirming_absence(self):
        remote = Remote()
        remote.lose_delete_response = True
        observer = self.observer(remote)
        _, rid, _, _, _ = self.run_mail(observer)
        observer.exporter.export_one(rid)
        purge = self.purge(observer, remote)
        self.assert_error("observability_purge_unavailable", lambda: purge.purge_runs([rid]))
        self.assertEqual(self.trace(rid)["reason_code"], "observability_purge_pending")
        self.assertTrue(purge.purge_runs([rid]))
        self.assertEqual(sum(method == "DELETE" for method, _ in remote.requests), 1)

    def test_ingestion_not_visible_cannot_be_mistaken_for_deleted(self):
        remote = Remote()
        observer = self.observer(remote)
        _, rid, _, _, _ = self.run_mail(observer)
        observer.exporter.export_one(rid)
        remote.rows.clear()
        self.assert_error("observability_ingestion_unconfirmed",
            lambda: self.purge(observer, remote).purge_runs([rid]))
        self.assertFalse(any(method == "DELETE" for method, _ in remote.requests))

    def test_explicitly_rejected_send_has_no_remote_ingestion_to_wait_for(self):
        remote = Remote()
        observer = self.observer(baseline.FakeTransport((False,)), langfuse_max_attempts=1)
        _, rid, _, _, _ = self.run_mail(observer)
        observer.exporter.export_one(rid)
        self.assertEqual(self.trace(rid)["reason_code"], "observability_http_failed")
        self.assertTrue(self.purge(observer, remote).purge_runs([rid]))
        self.assertEqual(remote.requests, [])

    def test_buffer_corruption_fails_closed_before_http(self):
        remote = Remote()
        observer = self.observer(remote)
        _, rid, _, _, _ = self.run_mail(observer)
        observer.exporter.export_one(rid)
        self.store._path(self.trace(rid)["export_object_id"]).write_bytes(b"corrupted")
        self.assert_error("observability_buffer_integrity_error",
            lambda: self.purge(observer, remote).purge_runs([rid]))
        self.assertEqual(remote.requests, [])
        self.assertEqual(self.trace(rid)["export_status"], "revoked")

    def test_exported_evidence_cannot_be_erased_by_late_failure_or_persist(self):
        remote = Remote()
        observer = self.observer(remote)
        _, rid, job, _, _ = self.run_mail(observer)
        observer.exporter.export_one(rid)
        before = self.trace(rid)
        observer.records.mark(rid, "degraded", "observability_http_failed")
        observer.records.persist(job, [], time_ns(), False)
        self.assertEqual(self.trace(rid)["export_status"], "exported")
        self.assertEqual(self.trace(rid)["generation"], before["generation"])
        self.assertTrue(self.purge(observer, remote).purge_runs([rid]))
        self.assertTrue(any(method == "DELETE" for method, _ in remote.requests))

    def test_purge_drains_send_on_another_connection_before_delete(self):
        remote = Remote()
        observer = self.observer(remote)
        _, rid, _, _, _ = self.run_mail(observer)
        remote.release.clear()
        with ThreadPoolExecutor(2) as pool:
            sending = pool.submit(observer.exporter.export_one, rid)
            self.assertTrue(remote.entered.wait(5))
            cleaning = pool.submit(self.purge(observer, remote).purge_runs, [rid])
            try:
                self.assertFalse(cleaning.done())
                self.assertEqual(remote.requests, [])
                with self.engine.connect() as conn:
                    idle = conn.execute(sa.text("SELECT count(*) FROM pg_stat_activity "
                        "WHERE state = 'idle in transaction' AND query LIKE '%pg_try_advisory_lock%'" )).scalar_one()
                self.assertEqual(idle, 0)
            finally:
                remote.release.set()
            sending.result(timeout=5)
            self.assertTrue(cleaning.result(timeout=5))
        self.assertEqual(remote.rows, [])

    def test_unexported_purge_and_shutdown_late_persist_never_contact_remote(self):
        remote = Remote()
        observer = self.observer(remote)
        _, rid, job, _, _ = self.run_mail(observer)
        before = self.trace(rid)
        observer.close()
        observer.records.persist(job, [], time_ns(), False)
        self.assertEqual(self.trace(rid)["generation"], before["generation"])
        self.assertTrue(self.purge(observer, remote).purge_runs([rid]))
        self.assertEqual(remote.requests, [])

    def test_scope_mismatch_cannot_delete_trace(self):
        remote = Remote()
        observer = self.observer(remote)
        _, rid, _, _, _ = self.run_mail(observer)
        observer.exporter.export_one(rid)
        outsider = PurgeService(self.engine, self.store, observer.records.settings, uuid4(),
            http_transport=httpx.MockTransport(remote.http))
        self.assertTrue(outsider.purge_runs([rid]))
        self.assertEqual(self.trace(rid)["export_status"], "exported")
        self.assertEqual(remote.requests, [])

    def test_process_lock_timeout_does_not_revoke_inflight_export(self):
        observer = self.observer(langfuse_http_timeout=0.1, langfuse_flush_timeout=0)
        _, rid, _, _, _ = self.run_mail(observer)
        script = """
import os, sys, sqlalchemy as sa
from globalmail_agent.observability.records import TraceRecords
from globalmail_agent.settings import Settings
engine = sa.create_engine(os.environ['GLOBALMAIL_TEST_DATABASE_URL'])
with TraceRecords(engine, None, Settings()).export_lock(sys.argv[1]):
    print('locked', flush=True)
    sys.stdin.readline()
engine.dispose()
"""
        environment = dict(os.environ, PYTHONPATH=os.pathsep.join(sys.path))
        child = subprocess.Popen([sys.executable, "-c", script, str(rid)], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=environment)
        try:
            self.assertEqual(child.stdout.readline().strip(), "locked")
            self.assert_error("observability_drain_timeout", lambda: observer.records.revoke(rid))
            self.assertEqual(self.trace(rid)["export_status"], "pending")
        finally:
            child.communicate("release\n", timeout=5)
        self.assertEqual(child.returncode, 0)
        observer.records.revoke(rid)
        self.assertEqual(self.trace(rid)["export_status"], "revoked")
