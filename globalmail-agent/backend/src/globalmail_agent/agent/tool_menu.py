"""Stage-specific schemas reduce menu pressure without removing any observations."""
import json
from globalmail_agent.agent.tools.after_sales import NAMES


def after_sales_stage(state, context):
    line_known = bool(context.payload.get('verified_business_observations'))
    decision_ready = False
    operations_known = False
    for message in state['messages']:
        if message.get('role') != 'tool':
            continue
        try:
            output = json.loads(message['content'])
        except (TypeError, ValueError):
            continue
        if output.get('status') not in {'ok', 'needs_input'}:
            continue
        data = output.get('data') or {}
        line_known |= bool(data.get('selected_line_id') or data.get('order_line_id'))
        operations_known |= bool(data.get('operations'))
        if 'decision_id' in data:
            decision_ready = output['status'] == 'ok' and data.get('authorized') is True
        if data.get('operation'):
            decision_ready = False
    enabled = set()
    if context.mode == 'simulation' and line_known:
        enabled.add('check_after_sales_eligibility')
        if decision_ready:
            enabled.add('create_after_sales_operation')
        if operations_known:
            enabled.add('cancel_after_sales_operation')
    return enabled, decision_ready


def stage_tools(tools, state, context):
    enabled, ready = after_sales_stage(state, context)
    return [tool for tool in tools if tool['function']['name'] not in NAMES or tool['function']['name'] in enabled], ready
