import sqlalchemy as sa
from after_sales_fixture import AfterSalesFixture
from agent_fixture import understanding
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.agent.understanding import Understanding, validate_sources
from globalmail_agent.observability.local_records import save_understanding
from globalmail_agent.application.conversation_lock import ServiceError

class ExplicitTargetReview(AfterSalesFixture):
    def test_latest_explicit_changed_target_cannot_execute_old_replacement(self):
        self.publish_policy()
        cid, context, command = self.prepared(action='replacement')
        checked = self.check(cid, context, command)
        self.assertTrue(checked['data']['authorized'], checked)
        result, _, _ = self.create_operation(cid, context, command, decision=checked)
        op = result['data']['operation']['operation_id']
        body = 'For the same order, please send replacement H-CTD16-US-BK-NEW instead of the old item.'
        self.append_mail(cid, body)
        job, latest, _, _ = self.components()
        message = latest.payload['messages'][-1]
        value = Understanding.model_validate(understanding([], intents=[{
            'business_type': 'replacement', 'order_number': None,
            'target_item': 'H-CTD16-US-BK-NEW', 'condition': None,
            'requested_solution': body, 'consent': 'explicit',
            'sources': [{'message_id': message['message_id'], 'quote': body}]}]))
        save_understanding(self.engine, self.store, latest.workspace_id, job, validate_sources(value, latest.payload))
        with self.assertRaises(ServiceError):
            actual = self.push(cid, op, 'create_execution')
            print('ACTUAL_RESPONSE', actual, flush=True)
        self.assertEqual(self.count(b.executions), 0)
        self.assertEqual(self.count(b.operations), 1)
