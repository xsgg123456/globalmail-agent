"""Use the product audit unchanged; keep complete excerpts only in private evidence."""
from bootstrap import digest, json_bytes
from review_observations import original_observations


def evaluate_item_audit(review, payload):
    from globalmail_agent.agent.review_audit import audit_accepts, audit_sources, trigger_units
    from globalmail_agent.agent.tool_schemas import Draft
    context = payload["context"]
    observations = original_observations(payload["observations"])
    draft = Draft.model_validate(payload["draft"])
    units = trigger_units(context)
    if payload.get("trigger_units") != units:
        raise RuntimeError("actual_review_trigger_units_not_product_exact")
    sources = audit_sources(context, observations)
    accepted = audit_accepts(review, context, observations, draft)
    effective = accepted and review.supported and review.language_correct and not review.unsupported_claims
    requests = [{**row.model_dump(mode="json"), "original_unit": units[row.unit_index]
        if row.unit_index < len(units) else None,
        "reply_quote_exact_match": bool(row.reply_quote) and row.reply_quote in draft.body}
        for row in review.request_checks]
    claims = []
    for row in review.source_checks:
        claim = draft.claims[row.claim_index] if row.claim_index < len(draft.claims) else None
        claims.append({**row.model_dump(mode="json"), "claim": claim.model_dump(mode="json") if claim else None,
            "evidence_checks": [{"source_id": evidence.source_id, "quote": evidence.quote,
                "source_exists": evidence.source_id in sources,
                "is_claim_source": bool(claim and evidence.source_id in claim.source_ids),
                "source_sha256": digest(sources[evidence.source_id].encode()) if evidence.source_id in sources else None,
                "exact_quote_match": bool(evidence.quote.strip()) and evidence.quote in sources.get(evidence.source_id, "")}
                for evidence in row.evidence]})
    complete = {"input_DATA_sha256": digest(json_bytes(payload)), "request_checks": requests, "source_checks": claims,
        "trigger_unit_count": len(units), "draft_claim_count": len(draft.claims),
        "model_supported": review.supported, "language_correct": review.language_correct,
        "unsupported_claims": review.unsupported_claims, "reason": review.reason,
        "audit_accepts": accepted, "effective_supported_AND": bool(effective),
        "exact_quotes_do_not_alone_prove_entailment": True}
    safe = {"audit_accepts": accepted, "effective_supported_AND": bool(effective),
        "request_check_count": len(requests), "trigger_unit_count": len(units),
        "source_check_count": len(claims), "draft_claim_count": len(draft.claims),
        "complete_audit_sha256": digest(json_bytes(complete))}
    return complete, safe
