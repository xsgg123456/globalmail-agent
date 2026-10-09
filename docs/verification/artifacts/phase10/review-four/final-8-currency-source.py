import sqlalchemy as sa
from test_selection_freshness import SelectionFreshnessTests
from globalmail_agent.adapters import business_schema as b

class NaturalCurrencyFinal(SelectionFreshnessTests):
    def test_original_natural_usdt_counterexample_now_rejected(self):
        self.reject_changed_refund('Yes, I confirm a full refund in USDT.')

    def test_explicit_natural_usd_reconfirmation_uses_original_and_records_latest(self):
        self.publish_policy()
        cid, _, command = self.prepared()
        context, current = self.current_selection(cid, command, 'Please give me a full refund.')
        checked = self.check(cid, context, current)
        self.assertTrue(checked['data']['authorized'], checked)
        created, _, _ = self.create_operation(cid, context, current, decision=checked)
        op = created['data']['operation']['operation_id']
        latest, renewed = self.current_selection(cid, command, 'Yes, I confirm a full refund in USD.')
        actual = self.push(cid, op, 'create_execution')
        self.assertEqual(actual['operation_id'], op)
        self.assertEqual(actual['executions'][0]['currency'], 'USD')
        self.assertEqual(actual['executions'][0]['amount_minor'], 5499)
        self.assertEqual(self.count(b.operations), 1)
        self.assertEqual(self.count(b.executions), 1)
        with self.engine.connect() as conn:
            saved = conn.execute(sa.select(b.executions.c.source_snapshot)).scalar_one()
            self.assertEqual(saved['execution_selection_ref']['message_id'], renewed.selection_ref.message_id)
