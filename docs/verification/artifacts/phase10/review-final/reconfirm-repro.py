from pathlib import Path
import sys
root = next(p for p in Path(__file__).resolve().parents if (p/'Product-Spec.md').is_file())
sys.path[:0] = [str(root/'globalmail-agent/backend/src'), str(root/'globalmail-agent/backend/tests'), str(root/'globalmail-agent/agent-eval')]
from bootstrap import isolated_database_environment
isolated_database_environment()
import unittest
from after_sales_fixture import AfterSalesFixture
from agent_fixture import understanding
from globalmail_agent.agent.understanding import Understanding, validate_sources
from globalmail_agent.observability.local_records import save_understanding

class Reconfirm(AfterSalesFixture):
    def test_current_identical_reconfirmation_is_rejected(self):
        self.publish_policy()
        cid, context, command = self.prepared()
        made, _, _ = self.create_operation(cid, context, command)
        op = made['data']['operation']['operation_id']
        self.append_mail(cid, 'Please proceed with the same full refund of 54.99 USD.')
        job, latest, _, _ = self.components()
        message = latest.payload['messages'][-1]
        source = {'message_id': message['message_id'], 'quote': message['body']}
        value = Understanding.model_validate(understanding([], intents=[{
            'business_type': 'refund', 'order_number': None, 'target_item': None, 'condition': None,
            'requested_solution': 'same full refund 54.99 USD', 'consent': 'explicit', 'sources': [source]}]))
        save_understanding(self.engine, self.store, latest.workspace_id, job, validate_sources(value, latest.payload))
        self.assert_error('selection_superseded', lambda: self.push(cid, op, 'create_execution'))
        current = command.model_copy(update={'selection_ref': command.selection_ref.model_copy(update=source)})
        checked = self.check(cid, latest, current)
        again, _, _ = self.create_operation(cid, latest, current, checked)
        self.assertEqual(again['reason_code'], 'operation_reused')
        self.assertEqual(again['data']['operation']['operation_id'], op)
        self.assert_error('selection_superseded', lambda: self.push(cid, op, 'create_execution'))
        print('RECONFIRM_REUSED_BUT_EXECUTION_DENIED', op, again['reason_code'], 'selection_superseded')

unittest.main(verbosity=2)
