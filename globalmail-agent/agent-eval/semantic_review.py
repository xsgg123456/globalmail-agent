"""Local evaluator review gate after a finished cycle; never asks the customer for approval."""
import json
import time
from bootstrap import digest


def await_review(directory):
    path = directory / "semantic-review.json"
    deadline = time.monotonic() + 300
    while not path.exists():
        if time.monotonic() >= deadline:
            raise RuntimeError("local_semantic_review_missing_no_further_model_calls")
        time.sleep(0.25)
    raw = path.read_bytes()
    review = json.loads(raw)
    if review.get("status") not in {"PASS", "FAIL"} or review.get("reviewer") != "coding_agent_semantic_review_not_external_business_owner":
        raise RuntimeError("local_semantic_review_format_invalid")
    return {**review, "review_sha256": digest(raw)}
