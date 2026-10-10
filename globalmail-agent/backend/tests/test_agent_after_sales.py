"""Real graph, gates and effect receipts; frozen responses do not certify model semantics."""
import json
from copy import deepcopy
import unittest
from unittest.mock import patch
from uuid import uuid4
import sqlalchemy as sa
from after_sales_fixture import AfterSalesFixture
from agent_fixture import ScriptedModel, call, understanding, draft
from globalmail_agent.adapters import agent_schema as a, business_schema as b
from globalmail_agent.adapters.body_store import read_bytes
from globalmail_agent.adapters.conversation_schema import conversations
from globalmail_agent.adapters.schema import objects
from globalmail_agent.application.commit_outcome import commit_outcome
from globalmail_agent.domain.conversation import Command
from globalmail_agent.application.conversation_lock import ServiceError


class CompactResultTests(unittest.TestCase):
    def test_packing_preserves_every_condition_and_plan_value(self):
        from globalmail_agent.agent.tools.after_sales_result import compact_result
        original = {'data': {'conditions': [{'code': 'source', 'label': '来源完整', 'status': 'fulfilled', 'fulfilled_by': ['message:1']},
            {'code': 'stock', 'label': '库存待补', 'status': 'wait', 'fulfilled_by': []}],
            'operation': {'quantity': 1, 'amount_minor': 0, 'currency': 'USD',
                'plan': {'quantity': 1, 'amount_minor': 0, 'currency': 'USD'}}}}
        packed = compact_result(deepcopy(original))['data']
        restored = [dict(zip(packed['condition_fields'], row)) for row in packed['conditions']]
        self.assertEqual(restored, original['data']['conditions'])
        op = packed['operation']
        self.assertEqual({key: op[field] for key, field in op['plan_field_map'].items()}, original['data']['operation']['plan'])
        distinct = {'data': {'operation': {'quantity': 1, 'plan': {'quantity': 2}}}}
        self.assertEqual(compact_result(deepcopy(distinct)), distinct, 'Different facts must never be deduplicated')


class AgentAfterSalesTests(AfterSalesFixture):
    def test_legacy_write_tools_are_denied_before_effect_or_budget(self):
        self.publish_policy()
        cid, _, request = self.prepared()
        job, _, _, gateway = self.components(embedding=self.gateway)
        for name in ('check_after_sales_eligibility', 'create_after_sales_operation', 'cancel_after_sales_operation'):
            self.assert_error('tool_not_allowed', lambda: gateway.call(call(name, request.model_dump(mode='json'))))
        self.assertEqual(self.count(b.operations), 0)
        self.assertEqual(self.budget_row(job)['tool_calls'], 0)
        self.assertEqual(self.outbound(cid), [])

    def test_read_receipt_replays_and_stop_preserves_existing_manual_record(self):
        self.publish_policy()
        cid, context, request = self.prepared()
        self.create_operation(cid, context, request)
        job, _, _, gateway = self.components(embedding=self.gateway)
        query = call('get_after_sales_context', {'order_line_id': request.order_line_id}, 'read-once')
        first = gateway.call(query)
        self.assertEqual(gateway.call(query), first)
        receipt = self.row(a.tool_commands, a.tool_commands.c.id == first[0])
        before = self.sales.listing(cid)
        self.controls.control(job['run_id'], 'stop', Command(expected_version=self.conversation(cid)['row_version']), uuid4().hex)
        current = self.sales.listing(cid)
        self.assertEqual(current['data']['operations'], before['data']['operations'])
        self.assertEqual(current['data']['executions'], before['data']['executions'])
        self.assertEqual(self.row(a.tool_commands, a.tool_commands.c.id == first[0]), receipt)
        self.assertEqual(self.budget_row(job)['tool_calls'], 1)
        self.assertEqual(self.outbound(cid), [])

    def test_model_cannot_call_legacy_application_even_with_valid_selection(self):
        self.publish_policy()
        cid, _, request = self.prepared()
        model = ScriptedModel(understanding([]), {'calls':[call('create_after_sales_operation', request.model_dump(mode='json'))]})
        result, job = self.execute(model, embedding=self.gateway)
        self.assertEqual(result.get('error_code'), 'model_tool_not_allowed', result)
        self.assertEqual(self.count(b.operations), 0)
        self.assertEqual(self.outbound(cid), [])
        self.assertEqual(self.budget_row(job)['model_requests'], 2)
