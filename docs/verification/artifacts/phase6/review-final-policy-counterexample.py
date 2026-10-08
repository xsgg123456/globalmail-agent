"""Production policy validation/rendering of controlled v1/v2 bytes, no PG/model."""
import json
from globalmail_agent.adapters.fixture_loader import FIXTURE_ROOT
from globalmail_agent.knowledge.policy_bundle import parse_policy
from globalmail_agent.knowledge.base import sha

observations = []
for directory in (FIXTURE_ROOT, FIXTURE_ROOT.parent / 'v2'):
    path = directory / 'policies/policy-profile.json'
    raw = path.read_bytes()
    value = parse_policy(raw)
    description = value['description']
    rules = value['rules']
    observations.append({
        'source': str(path.relative_to(FIXTURE_ROOT.parents[2])).replace('\\', '/'),
        'source_sha256': sha(raw), 'policy_version': rules['version'],
        'generator_version': value['generator_version'],
        'partial_requires_explicit_amount_currency_acceptance': rules['refund']['partial_requires_explicit_amount_currency_acceptance'],
        'description_explicit_consent_present': any(term in description for term in ('明确同意', '明确接受', '明确认可')),
        'description_question_is_not_consent_present': '不算接受' in description or '不视为同意' in description,
        'alternative_sku_rule': rules['replacement']['alternative_sku'],
        'description_sha256': value['description_sha256'],
        'full_production_generated_description': description,
    })
print(json.dumps({'scope': 'read_only_production_validated_policy_evidence',
    'observations': observations}, ensure_ascii=False, indent=2))
