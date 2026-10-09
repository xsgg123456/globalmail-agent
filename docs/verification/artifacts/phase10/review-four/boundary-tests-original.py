from test_selection_freshness import SelectionFreshnessTests
from globalmail_agent.adapters import business_schema as b
from globalmail_agent.application.conversation_lock import ServiceError

class ReviewFourBoundaryTests(SelectionFreshnessTests):
    def reject_execution(self,cid,op):
        with self.assertRaises(ServiceError) as result:
            self.push(cid,op,'create_execution')
        self.assertTrue(result.exception.code.startswith('selection_') or result.exception.code == 'customer_selection_required')
        self.assertEqual(self.count(b.executions),0)
        self.assertEqual(self.count(b.operations),1)

    def test_original_refund_amount_boundary_counterexample_now_rejected(self):
        self.reject_changed_refund('Yes, I confirm a full refund of 154.99 USD.')

    def test_original_refund_currency_boundary_counterexample_now_rejected(self):
        self.reject_changed_refund('Yes, I confirm a full refund of 54.99 USDT.')

    def test_explicit_two_units_cannot_reconfirm_one_replacement(self):
        self.publish_policy()
        cid,context,command=self.prepared(action='replacement')
        checked=self.check(cid,context,command)
        self.assertTrue(checked['data']['authorized'], checked)
        result,_,_=self.create_operation(cid,context,command,decision=checked)
        op=result['data']['operation']['operation_id']
        self.assertEqual(result['data']['operation']['quantity'],1)
        self.current_selection(cid,command,'Yes, please send 2 replacements of H-CTD16-US-BK.')
        self.reject_execution(cid,op)

    def test_wrong_exact_sku_cannot_reconfirm_original_replacement(self):
        self.publish_policy()
        cid,context,command=self.prepared(action='replacement')
        checked=self.check(cid,context,command)
        self.assertTrue(checked['data']['authorized'], checked)
        result,_,_=self.create_operation(cid,context,command,decision=checked)
        op=result['data']['operation']['operation_id']
        self.current_selection(cid,command,'Yes, please send replacement H-CTD16-US-BK-NEW instead.')
        self.reject_execution(cid,op)
