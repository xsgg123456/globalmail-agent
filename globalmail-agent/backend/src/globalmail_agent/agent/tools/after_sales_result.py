"""Lossless packing of repeated field names and identical plan values for Agent input."""
def compact_result(output):
    data = output.get('data') or {}
    # These are console controls, not business observations or Agent capabilities.
    for key in ('branch_id', 'branch_generation', 'conversation_version'):
        data.pop(key, None)
    conditions = data.get('conditions')
    if isinstance(conditions, list) and conditions and all(isinstance(row, dict) for row in conditions):
        fields = sorted({key for row in conditions for key in row})
        if all(set(row) == set(fields) for row in conditions):
            data['condition_fields'] = fields
            data['conditions'] = [[row[key] for key in fields] for row in conditions]
    operation = data.get('operation')
    if operation and data.get('operations') == [operation]:
        del data['operations']
    if isinstance(operation, dict):
        operation.pop('allowed_events', None)
        plan = operation.get('plan')
        fields = {key: 'kind' if key == 'action' else key for key in plan} if isinstance(plan, dict) else {}
        if fields and all(field in operation and operation[field] == plan[key] for key, field in fields.items()):
            operation['plan_field_map'] = fields
            del operation['plan']
    return output
