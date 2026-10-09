"""Policy publication cannot overtake an already authorized console transaction."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from threading import Event
from unittest.mock import patch
from uuid import UUID, uuid4
from after_sales_fixture import AfterSalesFixture
from globalmail_agent.application.after_sales_policy import published_policy
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.index_commands import ReleaseCommand


class SimulationPolicyRaceTests(AfterSalesFixture):
    def test_publication_waits_until_console_execution_transaction_commits(self):
        self.publish_policy()
        cid, context, request = self.prepared('refund')
        result, _, _ = self.create_operation(cid, context, request)
        operation = result['data']['operation']['operation_id']
        validated, resume, publishing = Event(), Event(), Event()

        def barrier(*args, **kwargs):
            policy = published_policy(*args, **kwargs)
            validated.set()
            if not resume.wait(15):
                raise AssertionError('console validation barrier timeout')
            return policy

        listing = self.releases.listing()
        build = UUID(listing['items'][0]['entries'][0]['build_id'])
        command = ReleaseCommand(expected_release_epoch=listing['head']['epoch'], build_ids=[build])

        def publish():
            publishing.set()
            return self.releases.publish(command, uuid4().hex)

        with patch('globalmail_agent.application.after_sales.published_policy', side_effect=barrier):
            with ThreadPoolExecutor(max_workers=2) as pool:
                execution = pool.submit(self.push, cid, operation, 'create_execution')
                try:
                    self.assertTrue(validated.wait(10))
                    publication = pool.submit(publish)
                    self.assertTrue(publishing.wait(5))
                    with self.assertRaises(TimeoutError):
                        publication.result(timeout=.5)
                finally:
                    resume.set()
                accepted = execution.result(timeout=10)
                updated = publication.result(timeout=10)
        self.assertEqual(len(accepted['executions']), 1)
        self.assertEqual(accepted['executions'][0]['status'], 'accepted')
        self.assertEqual(updated['head']['epoch'], listing['head']['epoch'] + 1)
        # Subsequent payment cannot rely on the old decision after publication.
        with self.assertRaises(ServiceError) as refused:
            self.push(cid, operation, 'succeeded', receipt_ref='stale-payment-attempt')
        self.assertEqual(refused.exception.code, 'published_policy_required')
        current = self.sales.listing(cid, operation)['data']
        self.assertEqual(current['executions'][0]['status'], 'accepted')
        self.assertIsNone(current['executions'][0]['receipt_ref'])
