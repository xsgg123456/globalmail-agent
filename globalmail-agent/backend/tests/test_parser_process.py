"""Actual parser child/process boundaries; no database or external provider needed."""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from globalmail_agent.knowledge.parser_process import child_environment, run_child, parse_bytes, ParserStopped, ParserFailure
from globalmail_agent.knowledge.parser_contract import ParserResult
from globalmail_agent.worker.knowledge_runner import KnowledgeRunner


class ParserProcessTests(unittest.TestCase):
    def test_secret_environment_is_not_inherited(self):
        with patch.dict(os.environ, {"GLOBALMAIL_DATABASE_URL": "SECRET_DB", "LLM_API_KEY": "SECRET_LLM", "OPENAI_API_KEY": "SECRET_OPENAI", "VITE_SECRET": "SECRET_VITE"}):
            environment = child_environment()
            for name in ("GLOBALMAIL_DATABASE_URL", "LLM_API_KEY", "OPENAI_API_KEY", "VITE_SECRET"):
                self.assertNotIn(name, environment)
            self.assertEqual(environment["HF_HUB_OFFLINE"], "1")

    def test_actual_markdown_child_preserves_warning_units_and_missing_image_section(self):
        content = "# 安装\n\n先断电，输入 24 V。\n\n![步骤图](https://invalid.example/step.png)\n\n按图连接后再开启。\n\n# 清洁\n\n使用干布。\n\n```text\n# 代码不是章节\n![示例](fake.png)\n```\n".encode()
        with tempfile.TemporaryDirectory() as folder:
            result = parse_bytes(content, "md", "markdown", Path(folder), lambda: True)
            self.assertTrue(result.full_document)
            self.assertEqual(result.source_sha256, hashlib.sha256(content).hexdigest())
            self.assertEqual(result.raw_document["content"], content.decode())
            self.assertEqual(len([b for b in result.blocks if b.type == "heading"]), 2)
            missing = result.diagnostics[0]
            affected = [b for b in result.blocks if b.id in missing.block_ids]
            self.assertTrue(any("按图连接" in b.text for b in affected))
            self.assertFalse(any("使用干布" in b.text for b in affected))
            self.assertEqual(len(result.diagnostics), 1)
            self.assertTrue((Path(folder) / "raw.json").is_file())

    def test_actual_controlled_jsonl_keeps_table_headers_units_and_full_raw(self):
        line = {"schema_version": "globalmail.knowledge/1", "document_type": "case_md", "section_id": "safe", "type": "table", "text": "参数", "table_rows": [["输入 (V)", "功率 (W)"], ["24", "12"]]}
        content = json.dumps(line, ensure_ascii=False).encode()
        with tempfile.TemporaryDirectory() as folder:
            result = parse_bytes(content, "jsonl", "markdown", Path(folder), lambda: True)
            self.assertEqual(result.blocks[0].table_rows, line["table_rows"])
            self.assertEqual(result.raw_document["content"], content.decode())

    def test_timeout_and_fence_loss_stop_only_owned_child(self):
        for timeout, callback, expected in ((0.25, lambda: True, ParserFailure), (10, lambda: False, ParserStopped)):
            with tempfile.TemporaryDirectory() as folder:
                started = time.monotonic()
                with self.assertRaises(expected):
                    run_child([sys.executable, "-c", "import time; time.sleep(30)"], Path(folder), callback, timeout=timeout, heartbeat_interval=0.1)
                self.assertLess(time.monotonic() - started, 8)

    def test_cancel_before_start_and_unsupported_profile(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ParserStopped):
                parse_bytes(b"content", "md", "markdown", Path(folder), lambda: False)
            with self.assertRaises(ParserFailure) as raised:
                parse_bytes(b"content", "md", "other", Path(folder), lambda: True)
            self.assertFalse(raised.exception.retryable)

    def test_configuration_change_never_uses_old_parser_cache(self):
        from unittest.mock import Mock
        runner = KnowledgeRunner(Mock(), Mock(), "workspace")
        runner.jobs = Mock()
        with self.assertRaises(ParserFailure) as error:
            runner.execute({"parser_fingerprint": "obsolete", "parser_profile_id": "markdown"})
        self.assertEqual(error.exception.code, "parser_configuration_changed")
        runner.jobs.cached_result.assert_not_called()

    def test_invalid_contract_ids_pages_and_assets_cannot_pass(self):
        base = {"source_sha256": "a" * 64, "full_document": True, "page_count": 1}
        for blocks in ([{"id": "a", "page": 2}], [{"id": "a"}, {"id": "a"}], [{"id": "a", "asset_ids": ["not-registered"]}]):
            with self.assertRaises(ValueError):
                ParserResult.model_validate({**base, "blocks": blocks})

    def test_runner_keeps_recovery_after_database_failure(self):
        from unittest.mock import Mock
        runner = KnowledgeRunner(Mock(), Mock(), "workspace")
        runner.jobs = Mock()
        runner.jobs.fail.side_effect = RuntimeError("PRIVATE_DATABASE_DETAILS")
        with self.assertLogs("globalmail_agent.worker.knowledge_runner", level="WARNING") as output:
            runner.safe_fail({}, "parser_timeout", True)
        self.assertNotIn("PRIVATE_DATABASE_DETAILS", " ".join(output.output))
