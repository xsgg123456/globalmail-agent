"""A case owns derived outputs, never the shared knowledge originals it read."""
from types import SimpleNamespace
from unittest.mock import patch
import sqlalchemy as sa
from test_agent_knowledge import AgentKnowledgeTests
from globalmail_agent.adapters import knowledge_schema as k, agent_schema as a
from globalmail_agent.application.lifecycle import LifecycleService
from globalmail_agent.knowledge.base import KnowledgeFiles


class SourceOwnershipTests(AgentKnowledgeTests):
    # Only these lifecycle scenarios run; shared fixture helpers retain actual retrieval.
    def test_case_delete_keeps_shared_knowledge_original_used_without_citation(self):
        did, build = self.prepare_release('KNOWLEDGE_MUST_SURVIVE_CASE_DELETE')
        self.publish([build])
        cid, rid, line = self.scenario_line()
        _, _, _, gateway = self.components(embedding=self.gateway)
        _, result = gateway.call(self.search_call(line)['calls'][0])
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(self.count(a.agent_run_dependencies), 1)
        with self.engine.connect() as conn:
            source = conn.execute(sa.select(k.document_versions.c.object_id).where(
                k.document_versions.c.document_id == did)).scalar_one()
            before = KnowledgeFiles(self.store).read(conn, source)[0]
        service = LifecycleService(self.engine, self.store, SimpleNamespace(lifecycle_journal_root=None))
        request = service.request('conversation', cid, service.preview('conversation', cid)['expected_version'])
        with patch('globalmail_agent.observability.purge.PurgeService.purge_runs', return_value=True):
            self.assertEqual(service.process(request['id'])['status'], 'completed')
        with self.engine.connect() as conn:
            self.assertEqual(KnowledgeFiles(self.store).read(conn, source)[0], before)

    def test_deleting_read_document_cleans_case_outputs_but_keeps_other_read_document_original(self):
        did, build = self.prepare_release('DELETE_THIS_KNOWLEDGE')
        keep, other_build = self.prepare_release('KEEP_OTHER_READ_KNOWLEDGE')
        self.publish([build, other_build])
        cid, _, line = self.scenario_line()
        _, _, _, gateway = self.components(embedding=self.gateway)
        _, result = gateway.call(self.search_call(line)['calls'][0])
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(self.count(a.agent_run_dependencies), 2)
        with self.engine.connect() as conn:
            source = conn.execute(sa.select(k.document_versions.c.object_id).where(
                k.document_versions.c.document_id == keep)).scalar_one()
            before = KnowledgeFiles(self.store).read(conn, source)[0]
        service = LifecycleService(self.engine, self.store, SimpleNamespace(lifecycle_journal_root=None))
        request = service.request('document', did, service.preview('document', did)['expected_version'])
        with patch('globalmail_agent.observability.purge.PurgeService.purge_runs', return_value=True):
            self.assertEqual(service.process(request['id'])['status'], 'completed')
        with self.engine.connect() as conn:
            self.assertEqual(KnowledgeFiles(self.store).read(conn, source)[0], before)


def load_tests(loader, tests, pattern):
    return __import__('unittest').TestSuite(SourceOwnershipTests(name) for name in (
        'test_case_delete_keeps_shared_knowledge_original_used_without_citation',
        'test_deleting_read_document_cleans_case_outputs_but_keeps_other_read_document_original'))
