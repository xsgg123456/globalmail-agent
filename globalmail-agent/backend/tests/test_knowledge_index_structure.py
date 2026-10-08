"""Actual local parser -> PG chunks: short SOPs, long scoped safety, table units and policy."""
import json
from uuid import UUID, uuid4
import sqlalchemy as sa
from globalmail_agent.adapters.knowledge_index_schema import index_parents, index_chunks, index_builds, embedding_profiles
from globalmail_agent.adapters.knowledge_schema import policy_bundles
from globalmail_agent.adapters.fixture_loader import FIXTURE_ROOT
from globalmail_agent.knowledge.commands import CreateDocument, ParseCommand, ReviewCommand
from globalmail_agent.knowledge.index_commands import BuildCommand
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.base import scope
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID
from sqlalchemy.exc import DBAPIError, IntegrityError
from index_helpers import IndexFixture


class IndexStructureTests(IndexFixture):
    def test_stop_conditions_after_long_steps_reach_all_operation_parents_and_inputs(self):
        warning = '出现焦味时立即停止操作，断电并交人工。此停止条件适用于上述所有检查步骤。'
        values = [{"section_id": "operation", "type": "heading", "text": "完整检查步骤"},
            *[{"section_id": "operation", "type": "paragraph",
               "text": f"步骤{i}：" + 'x' * 350} for i in range(9)],
            {"section_id": "stop", "type": "heading", "text": "停止条件"},
            {"section_id": "stop", "type": "paragraph", "text": warning}]
        did, vid = self.structured(values, [
            {"section_id": "operation", "sku": "H-CTD16-US-BK", "basis": "明确完整操作"},
            {"section_id": "stop", "sku": "H-CTD16-US-BK", "basis": "末段明确适用于上述步骤"}])
        result = self.build(vid)
        parents = [p for p in self.parents(result['build_id']) if p['section_id'] == 'operation']
        self.assertGreater(len(parents), 1)
        for parent in parents:
            self.assertIn(warning, parent['text'])
            self.assertTrue(any(p['section'] == 'stop' for p in parent['locations']))
        with self.engine.connect() as conn:
            inputs = conn.execute(sa.select(index_chunks.c.input_text).where(
                index_chunks.c.build_id == UUID(result['build_id']),
                index_chunks.c.parent_id.in_([p['id'] for p in parents]))).scalars().all()
        self.assertTrue(inputs)
        self.assertTrue(all(warning in text for text in inputs))
        self.publish([result])
        output = self.preview(query='这些完整步骤何时要停止？')
        self.assertEqual(output['reason'], 'ok')
        self.assertTrue(output['evidence'])
        for evidence in output['evidence']:
            self.assertIn(warning, evidence['text'])

    def structured(self, content_blocks, bindings):
        raw = json.dumps({"schema_version": "globalmail.knowledge/1", "document_type": "troubleshooting_md", "blocks": content_blocks}, ensure_ascii=False).encode()
        upload = self.docs.upload("structure.json", raw, uuid4().hex)
        created = self.docs.create(CreateDocument(expected_version=0, title="明确范围的结构化排障", document_type="troubleshooting_md",
            brand="OUTON", object_id=upload["object_id"], source_reference="隔离结构测试", available_at="2026-10-08T00:00:00Z",
            applicabilities=bindings), uuid4().hex)
        vid = UUID(created["version_id"])
        self.runner.jobs.enqueue(vid, ParseCommand(expected_version=1, parser_profile_id="markdown"), uuid4().hex)
        self.runner.execute(self.runner.jobs.claim(self.runner.owner))
        self.reviews.review(vid, ReviewCommand.model_validate(self.review_payload(vid)), uuid4().hex)
        return UUID(created["document_id"]), vid

    def parents(self, build_id):
        with self.engine.connect() as conn:
            return [dict(r) for r in conn.execute(sa.select(index_parents).where(index_parents.c.build_id == UUID(build_id))) .mappings()]

    def test_short_multiheading_sop_and_case_keep_all_prerequisites_and_stops_in_one_parent(self):
        text = "# 遥控器排障\n## 前提\nWarning: disconnect power before inspection.\n\n## 操作\n先核对电池极性，再检查配对。\n\n## 停止条件\nStop if damaged; escalate to human review."
        _, vid, _ = self.reviewed_markdown(text)
        build = self.build(vid)
        parents = self.parents(build["build_id"])
        self.assertEqual(len(parents), 1)
        self.publish([build])
        body = self.preview()["evidence"][0]["text"]
        for phrase in ("disconnect power", "电池极性", "Stop if damaged"):
            self.assertIn(phrase, body)
        self.assertGreater(len({p["section"] for p in parents[0]["locations"]}), 1)

    def test_long_operation_carries_only_same_scope_english_safety_from_prior_section(self):
        content = [{"section_id": "safety", "type": "paragraph", "text": "Warning: unplug power. Stop if damaged."},
            *[{"section_id": "operation", "type": "paragraph", "text": f"Step {i}: " + "a" * 350} for i in range(9)],
            {"section_id": "other", "type": "paragraph", "text": "Warning: OTHER SKU ONLY; do not apply to first SKU."}]
        bindings = [{"section_id": "safety", "sku": "H-CTD16-US-BK", "basis": "仅A前提"},
            {"section_id": "operation", "sku": "H-CTD16-US-BK", "basis": "仅A操作"},
            {"section_id": "other", "sku": "H-CTD16-US-SGY", "basis": "仅B操作"}]
        _, vid = self.structured(content, bindings)
        build = self.build(vid)
        parents = self.parents(build["build_id"])
        operations = [p for p in parents if p["section_id"] == "operation"]
        self.assertGreater(len(operations), 1)
        for parent in operations:
            self.assertIn("Warning: unplug power", parent["text"])
            self.assertIn("Stop if damaged", parent["text"])
            self.assertNotIn("OTHER SKU", parent["text"])
            self.assertLessEqual(parent["proxy_tokens"], 2000)
            self.assertEqual({a["section_id"] for a in parent["applicability"]}, {"safety", "operation"})
        self.publish([build])
        hits = self.preview()
        self.assertEqual(hits["reason"], "ok")
        self.assertNotIn("OTHER SKU", hits["evidence"][0]["text"])

    def test_table_header_units_survive_children_and_wrong_sku_parent_cannot_expand(self):
        rows = [["型号", "电压 (V)", "重量 (kg)"], *[[f"A-{i}", "120", "1.5"] for i in range(80)]]
        content = [{"section_id": "A", "type": "table", "text": "参数表，单位以表头为准。", "table_rows": rows},
            {"section_id": "B", "type": "paragraph", "text": "B专属：禁止使用A操作。"}]
        _, vid = self.structured(content, [{"section_id": "A", "sku": "H-CTD16-US-BK", "basis": "明确A"},
            {"section_id": "B", "sku": "H-CTD16-US-SGY", "basis": "明确B"}])
        build = self.build(vid)
        with self.engine.connect() as conn:
            child_rows = conn.execute(sa.select(index_chunks).join(index_parents, index_parents.c.id == index_chunks.c.parent_id)
                .where(index_chunks.c.build_id == UUID(build["build_id"]), index_parents.c.section_id == "A")).mappings().all()
        self.assertGreater(len(child_rows), 1)
        self.assertTrue(all("电压 (V)" in r["input_text"] and "重量 (kg)" in r["input_text"] for r in child_rows))
        self.publish([build])
        first, second = self.preview(), self.preview(sku="H-CTD16-US-SGY")
        self.assertNotIn("B专属", first["evidence"][0]["text"])
        self.assertIn("B专属", second["evidence"][0]["text"])
        self.assertNotIn("电压 (V)", second["evidence"][0]["text"])

    def test_shared_operation_separates_sku_prerequisites_and_preserves_full_warning(self):
        warning = "Warning:\nKeep hands dry.\nDisconnect the supply before these steps."
        content = [{"section_id": "safety", "type": "paragraph", "text": warning},
            *[{"section_id": "operation", "type": "paragraph", "text": f"Step {i}: " + "b" * 350} for i in range(8)]]
        a, b = "H-CTD16-US-BK", "H-CTD16-US-SGY"
        _, vid = self.structured(content, [{"section_id": "safety", "sku": a, "basis": "A独立前提"},
            {"section_id": "operation", "sku": a, "basis": "A操作"},
            {"section_id": "operation", "sku": b, "basis": "B共用正文但无A前提资格"}])
        build = self.build(vid)
        operations = [p for p in self.parents(build["build_id"]) if p["section_id"] == "operation"]
        for parent in operations:
            skus = {v["sku"] for v in parent["applicability"]}
            self.assertEqual(len(skus), 1)
            self.assertEqual(warning in parent["text"], a in skus)
        self.publish([build])
        self.assertNotIn("Keep hands dry", self.preview(sku=b)["evidence"][0]["text"])

    def test_policy_manifest_rules_description_and_hashes_are_one_version(self):
        rules = json.loads((FIXTURE_ROOT.parent / "v2/policies/policy-profile.json").read_text(encoding="utf-8"))
        created = self.docs.create(CreateDocument(expected_version=0, title="同版模拟政策", document_type="policy_json", brand=None,
            content=rules, source_reference="隔离政策副本", available_at="2026-10-08T00:00:00Z",
            applicabilities=[{"section_id": "document", "sku": "H-CTD16-US-BK", "basis": "隔离政策适用"}]), uuid4().hex)
        vid = UUID(created["version_id"])
        self.runner.jobs.enqueue(vid, ParseCommand(expected_version=1, parser_profile_id="policy"), uuid4().hex)
        self.runner.execute(self.runner.jobs.claim(self.runner.owner))
        self.reviews.review(vid, ReviewCommand.model_validate(self.review_payload(vid)), uuid4().hex)
        build = self.build(vid)
        release = self.publish([build])["release"]
        entry = release["entries"][0]
        self.assertEqual(entry["version_id"], str(vid))
        with self.engine.connect() as conn:
            policy = conn.execute(sa.select(policy_bundles).where(policy_bundles.c.version_id == vid)).mappings().one()
        self.assertEqual(entry["policy_bundle"]["description"], policy["description"])
        self.assertEqual(entry["policy_bundle"]["rules"], policy["rules"])
        self.assertEqual(entry["policy_bundle"]["description_sha256"], policy["description_sha256"])

    def test_immutable_input_and_scope_foreign_keys_reject_direct_corruption(self):
        _, vid, _ = self.reviewed_markdown()
        result = self.build(vid)
        with self.assertRaises(DBAPIError):
            with self.engine.begin() as conn:
                conn.execute(index_builds.update().where(index_builds.c.id == UUID(result["build_id"])).values(input_sha256="f" * 64))
        with self.assertRaises(DBAPIError):
            with self.engine.begin() as conn:
                conn.execute(index_chunks.update().where(index_chunks.c.build_id == UUID(result["build_id"])).values(input_text="corrupt"))
        with self.assertRaises(IntegrityError):
            with self.engine.begin() as conn:
                conn.execute(index_parents.insert().values(id=uuid4(), **{**scope(DEFAULT_WORKSPACE_ID), "branch_id": uuid4()},
                    build_id=UUID(result["build_id"]), position=99, section_id="document", text="合法正文但越界的scope",
                    content_sha256="a" * 64, applicability=[], locations=[], proxy_tokens=1))
