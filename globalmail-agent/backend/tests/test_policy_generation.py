"""Policy facts from actual rule files; legacy content never silently rewrites."""
import hashlib
import json
import unittest
from unittest.mock import patch
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.fixture_loader import FIXTURE_ROOT
from globalmail_agent.adapters.knowledge_schema import policy_bundles
from globalmail_agent.adapters.knowledge_index_schema import index_builds, index_parents, index_chunks
from globalmail_agent.knowledge.policy_bundle import parse_policy, GENERATOR_VERSION, LEGACY_GENERATOR_VERSION
from globalmail_agent.knowledge.commands import CreateDocument, VersionCommand, ParseCommand, ReviewCommand
from index_helpers import IndexFixture


class PolicyFactTests(unittest.TestCase):
    def test_actual_v1_v2_rules_require_explicit_acceptance_and_reconciliation(self):
        for root in (FIXTURE_ROOT, FIXTURE_ROOT.parent / 'v2'):
            with self.subTest(root=root.name):
                content = (root / 'policies/policy-profile.json').read_bytes()
                original = hashlib.sha256(content).hexdigest()
                current = parse_policy(content)
                legacy = parse_policy(content, generator_version=LEGACY_GENERATOR_VERSION)
                text = current['description']
                self.assertIn('具体金额和币种，取得明确同意后再提交', text)
                self.assertIn('客户询问金额、表达不满或没有回复，都不算接受', text)
                self.assertIn('客户明确选择并完成适配核验，再交人工确认', text)
                self.assertIn('先查询原申请和已执行记录', text)
                self.assertIn('检查补件能否取消以及是否已经产生补偿', text)
                self.assertEqual(current['rules'], legacy['rules'])
                self.assertEqual(current['rules_sha256'], legacy['rules_sha256'])
                self.assertNotEqual(current['description_sha256'], legacy['description_sha256'])
                self.assertEqual(current['generator_version'], GENERATOR_VERSION)
                self.assertEqual(hashlib.sha256((root / 'policies/policy-profile.json').read_bytes()).hexdigest(), original)

    def test_editable_policy_values_are_rendered_from_the_same_rules(self):
        rules = json.loads((FIXTURE_ROOT / 'policies/policy-profile.json').read_text(encoding='utf-8'))
        rules['return']['window_days_after_delivery'] = 41
        rules['refund']['partial_offer_max_basis_points'] = 1750
        rules['logistics']['stale_tracking_days'] = 9
        text = parse_policy(json.dumps(rules).encode())['description']
        self.assertIn('41 天内（含第 41 天）', text)
        self.assertIn('实付的 17.5%', text)
        self.assertIn('连续 9 天未更新', text)
        self.assertNotIn('含第 30 天', text)


class PolicyLegacyTests(IndexFixture):
    def test_legacy_bundle_is_readable_but_requires_new_revision_before_indexing(self):
        content = (FIXTURE_ROOT / 'policies/policy-profile.json').read_bytes()
        bindings = [{'section_id': 'document', 'sku': 'H-CTD16-US-BK', 'basis': '明确隔离政策范围'}]
        # Explicit legacy bundle fixture; reparsing it with today's parser must not fix its immutable bundle.
        with patch('globalmail_agent.knowledge.documents.parse_policy',
                   side_effect=lambda raw: parse_policy(raw, generator_version=LEGACY_GENERATOR_VERSION)):
            created = self.docs.create(CreateDocument(expected_version=0, title='旧说明模拟政策', document_type='policy_json',
                content=json.loads(content), source_reference='独立兼容夹具', available_at='2026-10-08T00:00:00Z',
                applicabilities=bindings), uuid4().hex)
        did, vid = UUID(created['document_id']), UUID(created['version_id'])
        with self.engine.connect() as conn:
            before = dict(conn.execute(sa.select(policy_bundles).where(policy_bundles.c.version_id == vid)).mappings().one())
        self.runner.jobs.enqueue(vid, ParseCommand(expected_version=1, parser_profile_id='policy'), uuid4().hex)
        self.runner.execute(self.runner.jobs.claim(self.runner.owner))
        self.reviews.review(vid, ReviewCommand.model_validate(self.review_payload(vid)), uuid4().hex)
        version = self.queries.version_detail(vid)['version']
        denied = self.post(f'/knowledge/versions/{vid}/build', {'expected_version': version['row_version'],
            'embedding_profile_key': 'qwen3.7-text-embedding', 'chunking_profile_key': 'structure_v1_500'})
        self.assertEqual(denied.status_code, 409, denied.text)
        self.assertEqual(denied.json()['msg'], 'policy_description_requires_revision')
        self.assertEqual(self.count(index_builds), 0)
        self.assertEqual(self.gateway.calls, [])
        self.assertEqual(self.client.get(f'/api/v1/knowledge/versions/{vid}').status_code, 200)
        revised = self.docs.revise(did, VersionCommand(expected_version=1, applicabilities=bindings), uuid4().hex)
        new_id = UUID(revised['version_id'])
        self.runner.jobs.enqueue(new_id, ParseCommand(expected_version=1, parser_profile_id='policy'), uuid4().hex)
        self.runner.execute(self.runner.jobs.claim(self.runner.owner))
        self.reviews.review(new_id, ReviewCommand.model_validate(self.review_payload(new_id)), uuid4().hex)
        built = self.build(new_id)
        release = self.publish([built])['release']
        current = release['entries'][0]['policy_bundle']
        self.assertEqual(current['generator_version'], GENERATOR_VERSION)
        self.assertIn('询问金额、表达不满或没有回复，都不算接受', current['description'])
        with self.engine.connect() as conn:
            after = dict(conn.execute(sa.select(policy_bundles).where(policy_bundles.c.version_id == vid)).mappings().one())
            parents = '\n'.join(conn.execute(sa.select(index_parents.c.text).where(
                index_parents.c.build_id == UUID(built['build_id']))).scalars())
            inputs = '\n'.join(conn.execute(sa.select(index_chunks.c.input_text).where(
                index_chunks.c.build_id == UUID(built['build_id']))).scalars())
        for text in (parents, inputs):
            self.assertIn('具体金额和币种，取得明确同意后再提交', text)
            self.assertIn('客户明确选择并完成适配核验，再交人工确认', text)
        self.assertEqual(before, after)
        self.assertEqual(version['source_sha256'], self.queries.version_detail(new_id)['version']['source_sha256'])
