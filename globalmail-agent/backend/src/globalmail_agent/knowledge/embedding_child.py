"""SDK-only execution; emits safe structured data, never raw provider exceptions."""
import json
import math
import os
from pathlib import Path
import sys
import time


def execute(payload):
    from openai import OpenAI
    started = time.monotonic()
    with OpenAI(api_key=os.environ["GLOBALMAIL_EMBEDDING_API_KEY"],
                base_url=os.environ["GLOBALMAIL_EMBEDDING_BASE_URL"], timeout=30, max_retries=0) as api:
        response = api.embeddings.create(model=payload["model"], input=payload["texts"],
                                         dimensions=1024, encoding_format="float")
    rows = sorted(response.data, key=lambda item: item.index)
    if ([item.index for item in rows] != list(range(len(payload["texts"]))) or any(
            isinstance(item.index, bool) for item in rows)):
        raise ValueError("invalid_output")
    vectors = [item.embedding for item in rows]
    for vector in vectors:
        if (len(vector) != 1024 or not any(vector) or any(
                isinstance(x, bool) or not isinstance(x, (int, float)) or not math.isfinite(x) for x in vector)):
            raise ValueError("invalid_output")
    if response.model and response.model != payload["model"]:
        raise ValueError("invalid_output")
    usage = response.usage.model_dump() if response.usage is not None else None
    if usage is not None:
        usage = {key: value for key, value in usage.items() if key in {"prompt_tokens", "total_tokens"}
                 and isinstance(value, int) and not isinstance(value, bool) and value >= 0}
    request_id = getattr(response, "_request_id", None)
    return {"vectors": vectors, "usage": usage, "request_id": request_id if isinstance(request_id, str) else None,
            "seconds": round(time.monotonic() - started, 4)}


def main():
    request_path = Path(sys.argv[1])
    result_path = request_path.parent / "result.json"
    try:
        payload = json.loads(request_path.read_text(encoding="utf-8"))
        result = execute(payload)
    except ImportError:
        result = {"error": "embedding_unavailable"}
    except (ValueError, TypeError, KeyError):
        result = {"error": "embedding_output_invalid"}
    except Exception:
        result = {"error": "embedding_provider_error"}
    result_path.write_text(json.dumps(result, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    return 1 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
