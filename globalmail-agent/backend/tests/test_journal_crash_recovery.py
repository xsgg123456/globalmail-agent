"""Crashed workers must not permanently block replay of an uncommitted intent."""
import unittest
from uuid import UUID, uuid4
from unittest.mock import patch
import sqlalchemy as sa
from test_backup_restore import BackupRestoreTests
from globalmail_agent.application.conversations import ConversationService
from globalmail_agent.application.lifecycle import LifecycleService
from globalmail_agent.application.replay_journal import JournalRecovery
from globalmail_agent.application.journal_gate import assert_journal_current
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
from globalmail_agent.adapters.conversation_schema import jobs, agent_slots
from globalmail_agent.domain.conversation import CreateConversation
from globalmail_agent.settings import Settings
from globalmail_agent.worker.leases import LeaseService


class CrashRecoveryTests(BackupRestoreTests):
    def test_expired_claim_after_process_crash_is_fenced_and_replayed(self):
        settings = Settings(lifecycle_journal_root=self.journal.root)
        row = ConversationService(self.source, self.store).create(CreateConversation(
            expected_version=0, sender_email='crashed-worker@example.test', body='PRIVATE_CRASH'), uuid4().hex)
        cid = UUID(row['conversation_id'])
        self.assertIsNotNone(LeaseService(self.source, DEFAULT_WORKSPACE_ID).claim('departed-worker'))
        with self.source.begin() as conn:
            for table in (jobs, agent_slots):
                conn.execute(table.update().values(lease_expires_at=sa.func.now() - sa.text("interval '1 day'")))
        service = LifecycleService(self.source, self.store, settings)
        with patch.object(service, '_revoke', side_effect=RuntimeError('transaction_crash')):
            with self.assertRaisesRegex(RuntimeError, 'transaction_crash'):
                service.request('conversation', cid, service.preview('conversation', cid)['expected_version'])
        with self.assertRaisesRegex(RuntimeError, 'journal_replay_required'):
            assert_journal_current(self.source, self.store)
        result = JournalRecovery(self.source, self.store.root, self.journal, settings).run()
        self.assertEqual(result['status'], 'verified')
        assert_journal_current(self.source, self.store)
        with self.source.connect() as conn:
            self.assertFalse(conn.execute(sa.select(jobs.c.id).where(jobs.c.status == 'running')).first())
            self.assertFalse(conn.execute(sa.select(agent_slots.c.id).where(agent_slots.c.lease_owner.is_not(None))).first())
        self.assertFalse(any(b'PRIVATE_CRASH' in path.read_bytes() for path in self.store.root.iterdir()))


def load_tests(loader, tests, pattern):
    return unittest.TestSuite([CrashRecoveryTests('test_expired_claim_after_process_crash_is_fenced_and_replayed')])
