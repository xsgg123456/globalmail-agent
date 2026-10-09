"""Fail before services/Embedding when saved four-field reviews cannot run current Graph."""
import json


def require_compatible_history_review(directory):
    from globalmail_agent.agent.outcome_validation import OutcomeReview
    current = OutcomeReview.model_json_schema()
    reviews = []
    for path in sorted(directory.glob("request-*.json")):
        request = json.loads(path.read_text(encoding="utf-8"))
        schema = request.get("schema") or {}
        if {"supported", "unsupported_claims"}.issubset(schema.get("properties", {})):
            reviews.append(path)
            if schema != current:
                raise RuntimeError("legacy_history_review_incompatible_no_initialization_or_Embedding_HTTP")
            response = json.loads(path.with_name(path.name.replace("request-", "response-")).read_text(encoding="utf-8"))
            try:
                OutcomeReview.model_validate_json(response["content"])
            except ValueError:
                raise RuntimeError("legacy_history_review_incompatible_no_initialization_or_Embedding_HTTP") from None
    if not reviews:
        raise RuntimeError("history_review_schema_missing_no_initialization_or_Embedding_HTTP")


def reject_legacy_scripted_review():
    from globalmail_agent.agent.outcome_validation import OutcomeReview
    if {"request_checks", "source_checks"}.issubset(OutcomeReview.model_json_schema()["required"]):
        raise RuntimeError("legacy_scripted_review_incompatible_no_initialization_or_Embedding_HTTP")
