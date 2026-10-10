"""Persistent send claims fence retries, process recovery and concurrent exporters."""
from threading import Event, Thread
from agent_fixture import AgentFixture
import test_observability as helpers
from globalmail_agent.observability.exporter import TraceExporter
from globalmail_agent.observability.records import TraceRecords
from globalmail_agent.adapters import agent_schema as a


class RecoveryTransport(helpers.FakeTransport):
    ack_unknown, retryable = True, False

    def __init__(self, confirmed=False):
        super().__init__((False,))
        self.confirmed, self.reads = confirmed, 0

    def reconcile(self, trace_id, value):
        self.reads += 1
        return self.confirmed


class ObservabilityRecoveryTests(AgentFixture):
    settings = helpers.ObservabilityTests.settings
    observer = helpers.ObservabilityTests.observer
    run_mail = helpers.ObservabilityTests.run_mail

    def test_pre_send_crash_sentinel_recovers_by_read_without_post(self):
        transport = RecoveryTransport(True)
        observer = self.observer(transport)
        _, rid, _, _, model = self.run_mail(observer)
        trace, value = observer.records.payload(rid)
        self.assertTrue(observer.records.claim(rid, trace["generation"], 0))
        self.assertFalse(observer.records.claim(rid, trace["generation"], 0))
        observer.exporter.export_one(rid)
        self.assertEqual((transport.payloads, transport.reads), ([], 0))
        observer.exporter.export_one(rid, recovering=True)
        self.assertEqual(observer.records.get(rid)["export_status"], "exported")
        self.assertEqual((transport.payloads, transport.reads), ([], 1))
        self.assertEqual(self.count(a.usage_records), len(model.requests))

    def test_unknown_acknowledgement_never_resends_unconfirmed_receipt(self):
        transport = RecoveryTransport()
        observer = self.observer(transport)
        cid, rid, _, _, model = self.run_mail(observer)
        observer.exporter.export_one(rid)
        observer.exporter.export_one(rid, recovering=True)
        summary = observer.records.get(rid)
        self.assertEqual((summary["export_status"], summary["reason_code"]),
            ("degraded", "observability_ack_unknown"))
        self.assertEqual((len(transport.payloads), transport.reads), (1, 1))
        self.assertEqual(self.count(a.usage_records), len(model.requests))
        self.assertEqual(len(self.outbound(cid)), 1)

    def test_two_exporters_cannot_send_the_same_persistent_buffer(self):
        transport = helpers.FakeTransport()
        entered, release = Event(), Event()
        original = transport.send
        def blocked(*args):
            entered.set()
            release.wait(2)
            return original(*args)
        transport.send = blocked
        observer = self.observer(transport)
        _, rid, _, _, _ = self.run_mail(observer)
        other_transport = helpers.FakeTransport()
        other = TraceExporter(TraceRecords(self.engine, self.store, observer.records.settings), other_transport)
        thread = Thread(target=observer.exporter.export_one, args=(rid,))
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            other.export_one(rid)
            self.assertEqual(other_transport.payloads, [])
        finally:
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(len(transport.payloads), 1)
        self.assertEqual(observer.records.get(rid)["export_status"], "exported")
        observer.exporter.export_one(rid)
        self.assertEqual(len(transport.payloads), 1)

    def test_revocation_during_http_wins_over_acknowledgement(self):
        transport = helpers.FakeTransport()
        observer = self.observer(transport)
        _, rid, _, _, _ = self.run_mail(observer)
        original = transport.send
        def revoked(*args):
            observer.records.revoke(rid)
            return original(*args)
        transport.send = revoked
        observer.exporter.export_one(rid)
        self.assertEqual(observer.records.get(rid)["export_status"], "revoked")
        self.assertEqual(len(transport.payloads), 1)
