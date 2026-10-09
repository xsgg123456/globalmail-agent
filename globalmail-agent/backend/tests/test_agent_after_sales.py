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
    def application(self):
        self.publish_policy()
        cid, _, command = self.prepared()
        job, context, _, gateway = self.components(embedding=self.gateway)
        return cid, command, job, context, gateway

    def checked_request(self, gateway, command):
        _, checked = gateway.call(call('check_after_sales_eligibility', command.model_dump(mode='json')))
        self.assertEqual(checked['status'], 'ok', checked)
        self.assertTrue(checked['data']['authorized'], checked)
        return {**command.model_dump(mode='json'), 'decision_id': checked['data']['decision_id']}

    def test_create_and_receipt_are_atomic_and_replay_after_lost_response(self):
        cid, command, job, context, gateway = self.application()
        input_revision = self.conversation(cid)['input_revision']
        request = call('create_after_sales_operation', self.checked_request(gateway, command), 'effect-once')
        original = gateway.save_result
        with patch.object(gateway, 'save_result', side_effect=RuntimeError('crash before receipt commit')):
            with self.assertRaises(RuntimeError):
                gateway.call(request)
        self.assertEqual(self.count(b.operations), 0, 'Receipt failure must roll back the application effect')
        gateway.save_result = original
        first = gateway.call(request)
        self.assertEqual(first[1]['status'], 'ok', first)
        self.assertEqual(gateway.call(request), first, 'Lost HTTP/model response must replay stored receipt')
        self.assertEqual(self.count(b.operations), 1)
        self.assertEqual(self.budget_row(job)['tool_calls'], 3, 'Stored replay must not consume another call')
        self.assertEqual(self.conversation(cid)['input_revision'], input_revision)

    def test_internal_effect_invalidates_prior_credential_without_rewriting_object(self):
        cid, command, job, context, gateway = self.application()
        old_id, _ = gateway.call(call('get_after_sales_context', {'order_line_id': command.order_line_id}))
        old = self.row(a.tool_commands, a.tool_commands.c.id == old_id)
        obj = self.row(objects, objects.c.id == old['result_object_id'])
        with self.engine.connect() as conn:
            before = read_bytes(conn, self.store, self.row(conversations, conversations.c.id == cid), obj['id'])
        new_id, applied = gateway.call(call('create_after_sales_operation', self.checked_request(gateway, command)))
        self.assertIn('command:' + str(old_id), applied['superseded_source_ids'])
        self.assertEqual(self.row(a.tool_commands, a.tool_commands.c.id == old_id)['status'], 'stale')
        self.assertEqual(self.row(objects, objects.c.id == obj['id']), obj)
        with self.engine.connect() as conn:
            self.assertEqual(read_bytes(conn, self.store, self.row(conversations, conversations.c.id == cid), obj['id']), before)
        text = 'Your internal refund application is accepted; payment is awaiting manual execution.'
        value = draft(text, claims=[{'kind': 'order_fact', 'text': text, 'source_ids': ['command:' + str(new_id)]}],
            waiting_for='manual_execution', waiting_operation_id=applied['data']['operation']['operation_id'],
            observed_business_version=applied['data']['operation']['version'])
        self.approve_fixture_draft(context, job, value)
        commit_outcome(self.engine, self.store, context, job, understanding([]), {'kind': 'reply', 'data': value})
        self.assertEqual(len(self.outbound(cid)), 1)

    def test_stop_before_effect_denies(self):
        cid, command, job, context, gateway = self.application()
        request = call('create_after_sales_operation', self.checked_request(gateway, command))
        self.controls.control(job['run_id'], 'stop', Command(expected_version=self.conversation(cid)['row_version']), uuid4().hex)
        with self.assertRaises(ServiceError):
            gateway.call(request)
        self.assertEqual(self.count(b.operations), 0)

    def test_stop_after_committed_effect_preserves_application_and_receipt(self):
        cid, command, job, context, gateway = self.application()
        command_id, accepted = gateway.call(call('create_after_sales_operation', self.checked_request(gateway, command)))
        receipt = self.row(a.tool_commands, a.tool_commands.c.id == command_id)
        self.controls.control(job['run_id'], 'stop', Command(expected_version=self.conversation(cid)['row_version']), uuid4().hex)
        self.assertEqual(self.count(b.operations), 1)
        self.assertEqual(self.row(a.tool_commands, a.tool_commands.c.id == command_id), receipt)
        self.assertEqual(self.sales.listing(cid)['data']['operations'][0]['status'], 'accepted')

    def test_finite_graph_creates_real_application_and_waits_on_actual_version(self):
        self.publish_policy()
        cid, _, command = self.prepared()
        def identify(messages):
            payload = json.loads(messages[1]['content'])
            from globalmail_agent.application.business_queries import BusinessQueries
            order = BusinessQueries(self.engine).detail(cid)['data']['orders'][0]['display_order_number']
            source = next(row for row in payload['messages'] if order in row['body'])
            selected = payload['messages'][-1]
            return understanding([], missing_information=[], order_candidates=[{'value': order, 'sources': [
                {'message_id': source['message_id'], 'quote': order}]}], intents=[{'business_type': 'refund',
                'order_number': order, 'target_item': None, 'condition': None, 'requested_solution': 'refund',
                'consent': 'explicit', 'sources': [{'message_id': source['message_id'], 'quote': order},
                    {'message_id': selected['message_id'], 'quote': selected['body']}]}])
        def submit(messages):
            check = json.loads(next(row['content'] for row in reversed(messages) if row['role'] == 'tool'))
            return {'calls': [call('create_after_sales_operation', {**command.model_dump(mode='json'),
                'decision_id': check['data']['decision_id']})]}
        def reply(messages):
            record = next(row for row in reversed(messages) if row['role'] == 'tool')
            result = json.loads(record['content'])
            operation = result['data']['operation']
            text = 'Your refund application is accepted and awaits manual execution.'
            return {'calls': [call('create_reply_draft', draft(text,
                claims=[{'kind': 'order_fact', 'text': text, 'source_ids': [result['command_source_id']]}],
                waiting_for='manual_execution', waiting_operation_id=operation['operation_id'],
                observed_business_version=operation['version']))]}
        from globalmail_agent.application.business_queries import BusinessQueries
        order = BusinessQueries(self.engine).detail(cid)['data']['orders'][0]['display_order_number']
        model = ScriptedModel(identify, {'calls': [call('get_order_snapshot', {'display_order_number': order})]},
            {'calls': [call('check_after_sales_eligibility', command.model_dump(mode='json'))]}, submit, reply)
        result, job = self.execute(model, embedding=self.gateway)
        from globalmail_agent.agent.budget import input_estimate
        from globalmail_agent.agent.tool_schemas import schemas
        self.assertEqual(result.get('outcome'), 'reply_and_wait', {'result': result, 'requests': [
            [t['function']['name'] for t in r.get('tools') or []] for r in model.requests], 'application_menu':
            input_estimate(model.requests[-1]['messages'], schemas({'create_after_sales_operation', 'get_operation_status', 'get_after_sales_context', 'get_item_availability', 'create_reply_draft', 'request_human_review'}))})
        self.assertEqual(self.count(b.operations), 1)
        self.assertEqual(len(self.outbound(cid)), 1)
        self.assertFalse(any(tool['function']['name'] in {'simulation_event', 'create_execution'}
            for request in model.requests for tool in request.get('tools') or []))
