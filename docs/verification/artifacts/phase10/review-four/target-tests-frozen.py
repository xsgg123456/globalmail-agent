from copy import deepcopy
import sqlalchemy as sa
from after_sales_fixture import AfterSalesFixture
from agent_fixture import understanding
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.agent.understanding import Understanding, validate_sources
from globalmail_agent.observability.local_records import save_understanding
from globalmail_agent.application.conversation_lock import ServiceError

class ExplicitTargetReviewFinal(AfterSalesFixture):
    def latest(self, cid, target, body):
        self.append_mail(cid, body)
        job, context, _, _ = self.components()
        message = context.payload['messages'][-1]
        value = Understanding.model_validate(understanding([], intents=[{
            'business_type': 'replacement', 'order_number': None,
            'target_item': target, 'condition': None, 'requested_solution': body,
            'consent': 'explicit', 'sources': [{'message_id': message['message_id'], 'quote': body}]}]))
        save_understanding(self.engine, self.store, context.workspace_id, job, validate_sources(value, context.payload))
        return message

    def original(self, action='replacement'):
        self.publish_policy()
        cid, context, command = self.prepared(action=action)
        checked = self.check(cid, context, command)
        self.assertTrue(checked['data']['authorized'], checked)
        result, _, _ = self.create_operation(cid, context, command, decision=checked)
        return cid, result['data']['operation']['operation_id']

    def test_unknown_new_explicit_target_rejected_with_original_choices_retained(self):
        cid, op = self.original()
        self.latest(cid, 'H-CTD16-US-BK-NEW', 'For the same order, please send replacement H-CTD16-US-BK-NEW instead of the old item.')
        with self.assertRaises(ServiceError) as caught:
            self.push(cid, op, 'create_execution')
        self.assertEqual(caught.exception.code, 'selection_target_mismatch')
        self.assertEqual(self.count(b.executions), 0)
        self.assertEqual(self.count(b.operations), 1)

    def test_verified_different_actual_line_does_not_block_original_plan(self):
        scene = self.package.scenarios['BASE-OUTON-04']
        second = deepcopy(scene['initial_state']['orders'][0]['lines'][0])
        second.update(line_id='SIM-O-BASE-OUTON-04-L2', paid_minor=0)
        scene['initial_state']['orders'][0]['lines'].append(second)
        cid, op = self.original(action='refund')
        self.latest(cid, second['line_id'], 'For the other actual line SIM-O-BASE-OUTON-04-L2, please arrange one replacement.')
        actual = self.push(cid, op, 'create_execution')
        self.assertEqual(actual['executions'][0]['order_line_id'], 'SIM-O-BASE-OUTON-04-L1')
        self.assertEqual(actual['executions'][0]['kind'], 'refund')
        self.assertEqual(actual['executions'][0]['amount_minor'], 5499)
        self.assertEqual(self.count(b.operations), 1)
        self.assertEqual(self.count(b.executions), 1)
