"""Explicit fake vectors validate HTTP/PG/worker protocols, never model relevance."""
from pathlib import Path
from uuid import UUID, uuid4
from fastapi.testclient import TestClient
from globalmail_agent.application.conversation_lock import DEFAULT_WORKSPACE_ID, ServiceError
from globalmail_agent.knowledge.builds import BuildService
from globalmail_agent.knowledge.releases import ReleaseService
from globalmail_agent.knowledge.retrieval import KnowledgeSearch
from globalmail_agent.knowledge.references import ReferenceService
from globalmail_agent.knowledge.index_commands import BuildCommand, ReleaseCommand, SearchCommand
from globalmail_agent.knowledge.commands import ReviewCommand
from globalmail_agent.worker.knowledge_runner import KnowledgeRunner
from globalmail_agent.main import create_app
from globalmail_agent.settings import Settings
from knowledge_helpers import KnowledgeFixture


class ExplicitFakeGateway:
    def __init__(self):
        self.calls, self.failure_at, self.hook = [], None, None

    def profiles(self):
        return [{"key": key, "label": "明确合成协议向量", "model": key, "dimensions": 1024,
            "provider": "explicit_protocol_fake", "region": "test", "endpoint_config_id": "isolated_no_network",
            "normalization": "unit_l2_float32_v1", "input_format": "title_path_prerequisite_body_v1",
            "query_format": "plain_query_v1", "tokenizer": "proxy_ascii1_unicode2_v1", "provider_weight_revision": "test/1",
            "probe_id": "test/1", "probe_min_cosine": 0.9995, "available": True}
            for key in ("qwen3.7-text-embedding", "text-embedding-v4")]

    def embed(self, profile, texts, *, current=None, stopped=None):
        self.calls.append((profile["key"], list(texts)))
        if self.hook:
            self.hook()
        if self.failure_at == len(self.calls):
            raise ServiceError("embedding_provider_error", 503)
        if current and not current() or stopped and stopped():
            raise ServiceError("embedding_cancelled")
        vector = [0.0] * 1024
        vector[0 if profile["key"] == "qwen3.7-text-embedding" else 1] = 1.0
        return {"vectors": [vector[:] for _ in texts], "probe_vector": vector,
            "request_id": "explicit_fake_" + str(len(self.calls)), "usage": {"test_only": True}, "seconds": 0}


class IndexFixture(KnowledgeFixture):
    def setUp(self):
        super().setUp()
        self.gateway = ExplicitFakeGateway()
        self.builds = BuildService(self.engine, self.store, self.gateway)
        self.releases = ReleaseService(self.engine, self.store)
        self.search = KnowledgeSearch(self.engine, self.store, self.gateway)
        self.references = ReferenceService(self.engine, self.store)
        self.runner = KnowledgeRunner(self.engine, self.store, DEFAULT_WORKSPACE_ID, self.gateway)
        self.client.close()
        self.client = TestClient(create_app(Settings(object_root=Path(self.temp.name)), engine=self.engine,
            start_worker=False, embedding_gateway=self.gateway), base_url="http://127.0.0.1:18080")
        self.addCleanup(self.client.close)

    def reviewed_markdown(self, content="# 排障\n先断电。\n\n确认型号后按完整步骤操作。"):
        did, vid, payload = self.markdown(content)
        state = self.queries.version_detail(vid)["version"]
        response = self.post(f"/knowledge/versions/{vid}/parse", {"expected_version": state["row_version"], "parser_profile_id": "markdown"})
        self.assertEqual(response.status_code, 202, response.text)
        job = self.runner.jobs.claim(self.runner.owner)
        self.runner.execute(job)  # Actual local parser child, no paid model.
        self.reviews.review(vid, ReviewCommand.model_validate(self.review_payload(vid)), uuid4().hex)
        return did, vid, payload

    def build(self, vid, model="qwen3.7-text-embedding", execute=True, chunker="structure_v1_500"):
        state = self.queries.version_detail(vid)["version"]
        response = self.post(f"/knowledge/versions/{vid}/build", {"expected_version": state["row_version"],
            "embedding_profile_key": model, "chunking_profile_key": chunker})
        self.assertEqual(response.status_code, 202, response.text)
        result = response.json()["data"]
        if execute:
            job = self.runner.jobs.claim(self.runner.owner)
            self.assertIsNotNone(job)
            self.assertEqual(str(job["id"]), result["job_id"])
            self.runner.execute(job)
        return result

    def publish(self, ids, epoch=None, replace_all=False):
        current = self.releases.listing()["head"]
        response = self.post("/knowledge/releases", {"expected_release_epoch": current["epoch"] if epoch is None else epoch,
            "build_ids": [r["build_id"] if isinstance(r, dict) else str(r) for r in ids], "replace_all": replace_all})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]

    def preview(self, **updates):
        response = self.post("/knowledge/search", {"query": "Welche Fernbedienung passt?", "sku": "H-CTD16-US-BK",
            "mode": "simulation", **updates})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()["data"]
