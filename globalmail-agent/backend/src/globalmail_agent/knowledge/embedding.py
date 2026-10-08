"""Configured provider space and validated, isolated Embedding calls."""
import hashlib
import math
import struct
from urllib.parse import urlsplit

from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.embedding_process import embed_child

PROBE_TEXT = "知识空间固定探针：先断电；德国遥控器配对。 Disconnect power before pairing the remote."
PROBE_MIN_COSINE = 0.9995
MODELS = {"qwen3.7-text-embedding": "Qwen3.7 · 1024维", "text-embedding-v4": "V4 · 1024维"}


def normalize_vector(vector):
    if (not isinstance(vector, list) or len(vector) != 1024 or any(
            isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in vector)):
        raise ServiceError("embedding_output_invalid", 503)
    norm = math.hypot(*vector)
    if not norm or not math.isfinite(norm):
        raise ServiceError("embedding_output_invalid", 503)
    return [struct.unpack("<f", struct.pack("<f", float(x / norm)))[0] for x in vector]


def probe_matches(current, baseline):
    left, right = normalize_vector(current), normalize_vector(baseline)
    return math.fsum(a * b for a, b in zip(left, right)) >= PROBE_MIN_COSINE


class EmbeddingGateway:
    def __init__(self, settings):
        self.base_url = settings.embedding_base_url or settings.model_base_url
        self.api_key = (settings.embedding_api_key.get_secret_value()
                        or settings.model_api_key.get_secret_value())
        try:
            parsed = urlsplit(self.base_url)
            host = parsed.hostname or ""
            self.allowed = (parsed.scheme == "https" and not parsed.username and not parsed.password
                and not parsed.query and not parsed.fragment and parsed.port in (None, 443)
                and (host == "dashscope.aliyuncs.com" or host.endswith(".cn-beijing.maas.aliyuncs.com"))
                and parsed.path.rstrip("/") == "/compatible-mode/v1")
        except ValueError:
            self.allowed = False
        self.endpoint_id = "dashscope_beijing_" + hashlib.sha256(self.base_url.rstrip("/").encode()).hexdigest()[:16]

    def profiles(self):
        return [{"key": key, "label": label, "model": key, "dimensions": 1024,
            "provider": "dashscope", "region": "cn-beijing", "endpoint_config_id": self.endpoint_id,
            "normalization": "unit_l2_float32_v1", "input_format": "title_path_prerequisite_body_v1",
            "query_format": "plain_query_v1", "tokenizer": "proxy_ascii1_unicode2_v1",
            "provider_weight_revision": None, "probe_id": "power_remote_multilingual_v1",
            "probe_min_cosine": PROBE_MIN_COSINE, "available": bool(self.allowed and self.api_key)}
            for key, label in MODELS.items()]

    def embed(self, profile, texts, *, current=None, stopped=None):
        if not self.allowed or not self.api_key:
            raise ServiceError("embedding_unavailable", 503)
        model = profile.get("model") or profile.get("key")
        if (model not in MODELS or profile.get("dimensions") != 1024
                or profile.get("endpoint_config_id") != self.endpoint_id):
            raise ServiceError("embedding_profile_mismatch", 409)
        if (not isinstance(texts, list) or not 1 <= len(texts) <= 9 or any(
                not isinstance(t, str) or not t.strip()
                or sum(1 if ord(c) < 128 else 2 for c in t) > 8000 for t in texts)):
            raise ServiceError("embedding_input_invalid", 422)
        result = embed_child(self.base_url, self.api_key, model, [PROBE_TEXT, *texts],
            current or (lambda: True), stopped or (lambda: False))
        vectors = result.get("vectors")
        if not isinstance(vectors, list) or len(vectors) != len(texts) + 1:
            raise ServiceError("embedding_output_invalid", 503)
        normalized = [normalize_vector(v) for v in vectors]
        baseline = profile.get("probe_vector")
        if baseline is not None and not probe_matches(normalized[0], list(baseline)):
            raise ServiceError("embedding_model_drift", 503)
        return {"vectors": normalized[1:], "probe_vector": normalized[0],
            **{k: result.get(k) for k in ("usage", "request_id", "seconds")}}
