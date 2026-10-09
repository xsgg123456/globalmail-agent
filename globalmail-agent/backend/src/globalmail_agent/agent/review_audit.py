"""Exact audit bindings are necessary; semantic entailment still needs model review."""
import json
import re
from dataclasses import dataclass
from typing import Literal
from pydantic import Field
from globalmail_agent.agent.understanding import StrictModel
from globalmail_agent.knowledge.base import canonical


class RequestCheck(StrictModel):
    unit_index: int = Field(ge=0, strict=True)
    status: Literal["addressed", "context", "omitted", "changed_condition"] = Field(
        description="Omitted if no full request match; context if no request.")
    reply_quote: str = Field(description="Continuous draft text only; omitted/context: empty.")


class EvidenceQuote(StrictModel):
    source_id: str = Field(min_length=1)
    quote: str = Field(min_length=1)


class SourceCheck(StrictModel):
    claim_index: int = Field(ge=0, strict=True)
    evidence: list[EvidenceQuote] = Field(max_length=10)
    supported: bool = Field(strict=True, description="ALL facts need declared sources; false allows none.")


@dataclass(frozen=True)
class AuditFailure:
    code: str
    binding: bool = True


def trigger_units(context):
    body = next((row['body'] for row in context['messages']
        if row['message_id'] == context['trigger_message_id']), '')
    ends = [match.end() for match in re.finditer(r'[.!?。！？](?:\s+|$)|\n+', body)]
    units, start = [], 0
    for end in [*ends, len(body)]:
        if end > start:
            units.append(body[start:end])
        start = end
    assert ''.join(units) == body
    return units


def audit_sources(context, observations):
    sources = {row['message_id']: row['body']
        for row in [*context['messages'], *context['human_notes']]}
    for identity, row in context.get('verified_tool_sources', {}).items():
        sources[identity] = row['body']
    for identity, row in context.get('visual_sources', {}).items():
        sources[identity] = row['body']
    receipts = [json.loads(row['content']) for row in observations]
    receipts += [dict(row['result'], command_source_id=row['command_source_id'])
        for row in context.get('verified_business_observations', [])]
    for receipt in receipts:
        if receipt.get('status') not in {'ok', 'needs_input'}:
            continue
        identity = receipt.get('command_source_id')
        if identity:
            sources[identity] = canonical(receipt).decode()
        for evidence in receipt.get('data', {}).get('evidence', []):
            sources[evidence['evidence_id']] = evidence['text']
    return sources


def audit_failure(review, context, observations, draft):
    semantic_error = None
    units = trigger_units(context)
    indexes = [row.unit_index for row in review.request_checks]
    if sorted(indexes) != list(range(len(units))):
        return AuditFailure('request_indexes_incomplete')
    for row in review.request_checks:
        if row.status in {'omitted', 'changed_condition'}:
            semantic_error = semantic_error or AuditFailure(f'request_unit_{row.unit_index}_{row.status}', False)
        if row.reply_quote and row.reply_quote not in draft.body:
            return AuditFailure(f'request_unit_{row.unit_index}_reply_quote_not_in_draft')
        if row.status == 'addressed' and not row.reply_quote:
            # A no-email business wait still passes the original scoped operation gate.
            if draft.body or not draft.waiting_operation_id:
                return AuditFailure(f'request_unit_{row.unit_index}_reply_quote_missing')
    indexes = [row.claim_index for row in review.source_checks]
    if sorted(indexes) != list(range(len(draft.claims))):
        return AuditFailure('claim_indexes_incomplete')
    sources = audit_sources(context, observations)
    for row in review.source_checks:
        claim = draft.claims[row.claim_index]
        if not row.supported:
            semantic_error = semantic_error or AuditFailure(f'claim_{row.claim_index}_not_supported', False)
        if row.supported and (claim.kind in {'order_fact', 'customer_fact', 'product_step', 'visual_observation'} or claim.source_ids) and not row.evidence:
            return AuditFailure(f'claim_{row.claim_index}_evidence_missing')
        for evidence in row.evidence:
            if evidence.source_id not in claim.source_ids or evidence.source_id not in sources:
                return AuditFailure(f'claim_{row.claim_index}_source_not_owned')
            if not evidence.quote.strip() or evidence.quote not in sources[evidence.source_id]:
                return AuditFailure(f'claim_{row.claim_index}_quote_not_in_source')
    return semantic_error


def audit_accepts(review, context, observations, draft):
    return audit_failure(review, context, observations, draft) is None
