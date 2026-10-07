"""Failure and invalidation regressions; DB cases run inside probe_lifecycle's disposable DB."""
import copy
import secrets
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tech-spike'))
import psycopg
from lifecycle_store import ContractError, Store, validate_vectors


class VectorContractTests(unittest.TestCase):
    def test_invalid_batch_never_becomes_indexable(self):
        for vectors in ([], [[1, 2]], [[float('nan'), 0, 0]], [[0, 0, 0]]):
            with self.subTest(vectors=vectors), self.assertRaises(ContractError):
                validate_vectors(vectors, 1, 3)

    def test_cleanup_removes_credentials_when_daemon_fails(self):
        from probe_support import cleanup_database
        with tempfile.TemporaryDirectory() as folder:
            env = Path(folder)/'test.env'
            env.write_text('test-placeholder', encoding='utf-8')
            def unavailable(*args):
                raise RuntimeError('injected_daemon_failure')
            result = {'passed':True}
            self.assertFalse(cleanup_database(unavailable, 'owned-id', 'nonce', env, result))
            self.assertFalse(env.exists())
            self.assertFalse(result['passed'])
            self.assertTrue(result['temporary_credentials_removed'])
            self.assertFalse(result['temporary_container_removed'])

    def test_cleanup_never_stops_an_unowned_container(self):
        from probe_support import cleanup_database
        calls = []
        with tempfile.TemporaryDirectory() as folder:
            def other_owner(*args):
                calls.append(args[0])
                return 'another-probe'
            self.assertFalse(cleanup_database(other_owner, 'id', 'nonce', Path(folder)/'x', {}))
        self.assertEqual(calls, ['inspect'])


class DatabaseContractTests(unittest.TestCase):
    dsn = None

    def setUp(self):
        if not self.dsn:
            self.skipTest('Run probe_lifecycle.py for disposable PostgreSQL contract tests')
        self.store = Store(self.dsn)
        self.key = 'synthetic-'+secrets.token_hex(5)
        self.epoch = self.store.epoch()
        self.profile = {'model':'synthetic-contract-only', 'dimensions':3,
                        'parser':'synthetic-v1', 'splitter':'one-chunk-v1'}
        self.chunks = [{'document_id':self.key, 'chunk_id':self.key+':0', 'text':'Synthetic fixture',
                        'brands':['SYNTHETIC'], 'skus':[self.key], 'allowed_modes':['simulation'],
                        'usage_split':'rag', 'available_at':'2026-10-07T00:00:00+08:00'}]
        self.vectors = [[1.0, 0.0, 0.0]]
        self.store.register_products({self.key:'SYNTHETIC'})

    def prepare(self, **kwargs):
        return self.store.prepare(self.key, 'synthetic-v1', self.profile,
                                  self.chunks, self.vectors, self.epoch, **kwargs)

    def test_partial_database_write_rolls_back_all_rows(self):
        self.chunks *= 2  # Deliberately duplicate chunk PK after the first successful INSERT.
        self.vectors *= 2
        self.prepare()
        with self.assertRaises(psycopg.errors.UniqueViolation):
            self.store.finish(self.key, self.chunks, self.vectors, self.epoch)
        with self.store.connect() as conn:
            self.assertEqual(conn.execute('SELECT count(*) AS n FROM chunks WHERE build=%s',
                                          (self.key,)).fetchone()['n'], 0)
        with self.assertRaisesRegex(ContractError, 'build_not_ready'):
            self.store.publish(self.key, self.epoch)
        self.assertEqual(self.store.epoch(), self.epoch)

    def test_unreviewed_complete_build_cannot_publish(self):
        self.prepare(reviewed=False)
        self.store.finish(self.key, self.chunks, self.vectors, self.epoch)
        with self.assertRaisesRegex(ContractError, 'build_not_ready_or_reviewed'):
            self.store.publish(self.key, self.epoch)

    def test_same_idempotency_key_cannot_hide_changed_text(self):
        self.prepare()
        changed = copy.deepcopy(self.chunks)
        changed[0]['text'] = 'Different synthetic content'
        with self.assertRaisesRegex(ContractError, 'idempotency_payload_conflict'):
            self.store.prepare(self.key, 'synthetic-v1', self.profile,
                               changed, self.vectors, self.epoch)

    def test_expiry_invalidates_reference_even_without_an_epoch_change(self):
        from lifecycle_store import digest
        self.chunks[0]['until_at'] = '2026-10-08T00:00:00+08:00'
        self.prepare()
        self.store.finish(self.key,self.chunks,self.vectors,self.epoch)
        epoch = self.store.publish(self.key,self.epoch)
        query = {'sku':self.key,'brand':'SYNTHETIC','mode':'simulation',
                 'knowledge_split':'rag','as_of':'2026-10-07T01:00:00+08:00'}
        with self.store.connect() as conn:
            refs = self.store.search(conn,digest(self.profile),query,self.vectors[0])
        self.assertTrue(self.store.guard(refs,query))
        query['as_of'] = self.chunks[0]['until_at']
        self.assertFalse(self.store.guard(refs,query))
        self.assertEqual(self.store.epoch(),epoch)

    def test_waiting_completion_rechecks_epoch_after_revocation_commit(self):
        self.prepare()
        started, outcome = threading.Event(), []
        def late_worker():
            started.set()
            try:
                self.store.finish(self.key, self.chunks, self.vectors, self.epoch)
                outcome.append('unexpected_completion')
            except ContractError as exc:
                outcome.append(str(exc))
            except BaseException as exc:
                outcome.append(type(exc).__name__)
        worker = threading.Thread(target=late_worker, daemon=True)
        try:
            with self.store.connect() as writer, writer.transaction():
                writer.execute('SELECT epoch FROM head FOR UPDATE')
                writer.execute('UPDATE documents SET active=false WHERE id=%s', (self.key,))
                writer.execute('UPDATE head SET epoch=epoch+1')
                worker.start()
                self.assertTrue(started.wait(2))
                deadline, blocked = time.monotonic()+5, False
                with self.store.connect() as observer:
                    while time.monotonic() < deadline:
                        blocked = observer.execute("SELECT count(*) AS n FROM pg_stat_activity "
                            "WHERE datname=current_database() AND wait_event_type='Lock'").fetchone()['n'] > 0
                        if blocked:
                            break
                        time.sleep(0.02)
                self.assertTrue(blocked, 'completion must actually wait on a PostgreSQL lock')
            worker.join(5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(outcome, ['stale_epoch'])
            with self.store.connect() as conn:
                self.assertEqual(conn.execute('SELECT count(*) AS n FROM chunks WHERE build=%s',
                                              (self.key,)).fetchone()['n'], 0)
        finally:
            if worker.ident is not None:
                worker.join(5)


def run_suite(dsn):
    DatabaseContractTests.dsn = dsn  # Kept in memory; never a command argument or report field.
    suite = unittest.TestSuite(unittest.defaultTestLoader.loadTestsFromTestCase(cls)
                               for cls in (VectorContractTests, DatabaseContractTests))
    result = unittest.TestResult()
    suite.run(result)
    DatabaseContractTests.dsn = None
    return {'tests_run':result.testsRun, 'passed':result.wasSuccessful(),
            'failures':[test.id() for test, _ in result.failures],
            'errors':[test.id() for test, _ in result.errors],
            'skipped':[test.id() for test, _ in result.skipped]}


if __name__ == '__main__':
    unittest.main()
