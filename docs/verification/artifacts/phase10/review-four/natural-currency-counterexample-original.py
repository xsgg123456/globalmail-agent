import json
from test_selection_freshness import SelectionFreshnessTests
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.application.conversation_lock import ServiceError

class NaturalCurrencyDetail(SelectionFreshnessTests):
    def test_natural_usdt_has_valid_original_authorization_but_wrong_usd_executes(self):
        self.publish_policy()
        cid, _, command = self.prepared()
        context, current = self.current_selection(cid, command, 'Please give me a full refund.')
        checked = self.check(cid, context, current)
        self.assertTrue(checked['data']['authorized'], checked)
        created, _, _ = self.create_operation(cid, context, current, decision=checked)
        op = created['data']['operation']['operation_id']
        latest, renewed = self.current_selection(cid, command, 'Yes, I confirm a full refund in USDT.')
        try:
            actual = self.push(cid, op, 'create_execution')
        except ServiceError as error:
            self.assertEqual(error.code, 'selection_amount_currency_required')
            self.assertEqual(self.count(b.executions), 0)
            return
        print('ACTUAL_VALID_PREMISE_RESPONSE=' + json.dumps({'authorized': checked['data']['authorized'],
            'original_operation_id': op, 'latest_selection': renewed.selection_ref.model_dump(mode='json'),
            'actual': actual, 'operation_count': self.count(b.operations), 'execution_count': self.count(b.executions)}, default=str))
        self.fail('Explicit USDT must not execute original USD refund')
