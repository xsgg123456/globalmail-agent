"""Explicit fake audit data for protocol tests; never enrich actual provider responses."""
import json
from globalmail_agent.agent.review_audit import audit_sources


def engineering_audit(messages, value):
    if not isinstance(value, dict) or 'supported' not in value or 'request_checks' in value or 'source_checks' in value:
        return value
    data = json.loads(next(row['content'] for row in messages if row['role'] == 'user'))
    sources = audit_sources(data['context'], data['observations'])
    accepted = value['supported']
    requests = [{'unit_index': index, 'status': 'addressed' if accepted else 'omitted',
        'reply_quote': data['draft']['body'] if accepted else ''}
        for index, _ in enumerate(data['trigger_units'])]
    claims = [{'claim_index': index, 'supported': accepted,
        'evidence': [{'source_id': identity, 'quote': sources[identity]}
            for identity in claim['source_ids'] if identity in sources]}
        for index, claim in enumerate(data['draft']['claims'])]
    return {**value, 'request_checks': requests, 'source_checks': claims}
