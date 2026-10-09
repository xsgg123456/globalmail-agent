import sys, json, hashlib, time, unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Event
from unittest.mock import patch
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
BACK = ROOT / 'globalmail-agent/backend'
sys.path[:0] = [str(BACK/'src'), str(BACK/'tests'), str(ROOT/'globalmail-agent/agent-eval')]
from bootstrap import isolated_database_environment
isolated_database_environment()
import sqlalchemy as sa
from after_sales_fixture import AfterSalesFixture
from globalmail_agent.application.after_sales_policy import published_policy
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.index_commands import ReleaseCommand
from globalmail_agent.adapters import after_sales_schema as a, business_schema as b

EVIDENCE = []

class IndependentRace(AfterSalesFixture):
    def verify_order(self, action, event, first):
        self.publish_policy()
        cid, ctx, cmd = self.prepared(action)
        created, _, _ = self.create_operation(cid, ctx, cmd)
        op = created['data']['operation']['operation_id']
        if event != 'create_execution':
            self.push(cid, op, 'create_execution')
        if event == 'shipped':
            self.push(cid, op, 'label_created', receipt_ref='review-label', tracking_number='REVIEW-TRACK', carrier='review-carrier')
        def state():
            with self.engine.connect() as conn:
                return {'events': conn.execute(sa.select(sa.func.count()).select_from(a.simulation_events)).scalar_one(),
                    'holds': [dict(r) for r in conn.execute(sa.select(a.inventory_reservations.c.state, a.inventory_reservations.c.quantity)).mappings()],
                    'stocks': [dict(r) for r in conn.execute(sa.select(b.inventory.c.on_hand, b.inventory.c.reserved).where(b.inventory.c.branch_id == ctx.conversation_id)).mappings()],
                    'view': self.sales.listing(cid, op)['data']}
        before = state()
        listing = self.releases.listing()
        build = UUID(listing['items'][0]['entries'][0]['build_id'])
        release_cmd = ReleaseCommand(expected_release_epoch=listing['head']['epoch'], build_ids=[build])
        fields = {} if event == 'create_execution' else {'receipt_ref': 'review-real-' + event}
        record = {'case': action + ':' + event + ':' + first, 'schema': self.schema, 'paid_model_calls': 0}
        if first == 'publication':
            newer = self.releases.publish(release_cmd, uuid4().hex)
            with self.assertRaises(ServiceError) as denied:
                self.push(cid, op, event, **fields)
            self.assertEqual(denied.exception.code, 'published_policy_required')
            after = state()
            self.assertEqual(after, before)
            record.update(new_epoch=newer['head']['epoch'], refused=denied.exception.code, ledger_unchanged=True)
        else:
            validated, resume, started = Event(), Event(), Event()
            def barrier(*args, **kwargs):
                value = published_policy(*args, **kwargs)
                validated.set()
                if not resume.wait(15):
                    raise AssertionError('review policy barrier timeout')
                return value
            def publish():
                started.set()
                return self.releases.publish(release_cmd, uuid4().hex)
            with patch('globalmail_agent.application.after_sales.published_policy', side_effect=barrier):
                with ThreadPoolExecutor(max_workers=2) as pool:
                    effect = pool.submit(self.push, cid, op, event, **fields)
                    try:
                        self.assertTrue(validated.wait(10))
                        publication = pool.submit(publish)
                        self.assertTrue(started.wait(5))
                        with self.assertRaises(TimeoutError):
                            publication.result(timeout=.5)
                    finally:
                        resume.set()
                    result = effect.result(timeout=10)
                    newer = publication.result(timeout=10)
            self.assertEqual(newer['head']['epoch'], listing['head']['epoch']+1)
            after = state()
            self.assertEqual(after['events'], before['events']+1)
            if event == 'succeeded':
                self.assertEqual(result['executions'][0]['status'], 'succeeded')
            elif event == 'shipped':
                self.assertEqual(result['shipments'][0]['status'], 'shipped')
                self.assertEqual(after['holds'][0]['state'], 'consumed')
            else:
                self.assertEqual(len(result['executions']), 1)
            record.update(publication_blocked_until_effect_commit=True, effect_committed=True, new_epoch=newer['head']['epoch'])
        EVIDENCE.append(record)
        print(json.dumps(record))

for _action, _event in [('refund','create_execution'),('refund','succeeded'),('spare_part','shipped')]:
    for _first in ['publication','execution']:
        def test(self, action=_action, event=_event, first=_first):
            self.verify_order(action, event, first)
        setattr(IndependentRace, 'test_' + _action + '_' + _event + '_' + _first, test)

def snapshot():
    result = {}
    for base in [BACK/'src', BACK/'tests', BACK/'migrations', ROOT/'globalmail-agent/frontend/src', ROOT/'globalmail-agent/frontend/scripts']:
        for p in base.rglob('*'):
            if p.is_file() and p.suffix in {'.py','.vue','.ts','.md'}:
                result[p.relative_to(ROOT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
    return result

if __name__ == '__main__':
    before = snapshot()
    suites = unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromTestCase(IndependentRace)])
    for name in ['test_after_sales_operations','test_after_sales_cancellation','test_after_sales_migration',
                 'test_simulation_executions','test_simulation_safety','test_simulation_policy_race',
                 'test_agent_after_sales','test_agent_tools','test_agent_menu_pressure','test_agent_review','test_agent_review_audit']:
        try:
            __import__(name)
        except ModuleNotFoundError:
            continue
        suites.addTests(unittest.defaultTestLoader.loadTestsFromName(name))
    started = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2).run(suites)
    after = snapshot()
    summary = {'tests':result.testsRun, 'failures':len(result.failures), 'errors':len(result.errors), 'skipped':len(result.skipped),
        'duration_seconds':round(time.monotonic()-started,3), 'source_changed':before!=after,
        'source_sha256':before, 'independent_policy_cases':EVIDENCE, 'successful':result.wasSuccessful()}
    (ROOT/'docs/verification/artifacts/phase9/reviewer-final-tests.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='source_sha256'}))
    sys.exit(not result.wasSuccessful() or before!=after)
