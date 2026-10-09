from test_selection_freshness import SelectionFreshnessTests
from agent_fixture import understanding
from globalmail_agent.agent.understanding import Understanding, validate_sources
from globalmail_agent.observability.local_records import save_understanding
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.adapters import business_schema as b

class AdversarialReconfirmationTests(SelectionFreshnessTests):
    def reject_expected(self, operation, cid, reason):
        try:
            result = self.push(cid, operation, 'create_execution')
        except ServiceError as error:
            self.assertIn(error.code, {'selection_amount_currency_required', 'selection_superseded', 'selection_item_required', 'customer_selection_required', 'selection_quantity_required', 'selection_units_required'})
            return
        self.fail(f'{reason}: create_execution was accepted: {result}; execution_count={self.count(b.executions)}')

    def test_refund_amount_substring_must_not_reconfirm_original(self):
        self.publish_policy()
        cid, _, command = self.prepared()
        context, current = self.current_selection(cid, command, 'Please give me a full refund.')
        result, _, _ = self.create_operation(cid, context, current)
        op = result['data']['operation']['operation_id']
        self.current_selection(cid, command, 'Yes, I confirm a full refund of 154.99 USD.')
        self.reject_expected(op, cid, 'Customer selected 154.99 USD while original is 54.99 USD')

    def test_replacement_units_change_must_not_reconfirm_original(self):
        self.publish_policy()
        cid, _, command = self.prepared(action='replacement')
        context, current = self.current_selection(cid, command, 'Please replace the same item.')
        result, _, _ = self.create_operation(cid, context, current)
        op = result['data']['operation']['operation_id']
        self.current_selection(cid, command, 'Yes, please send 2 replacements of H-CTD16-US-BK.')
        self.reject_expected(op, cid, 'Customer selected 2 replacements while original quantity is 1')

    def test_replacement_changed_target_must_not_execute_old_plan(self):
        self.publish_policy()
        cid, _, command = self.prepared(action='replacement')
        context, current = self.current_selection(cid, command, 'Please replace the same item.')
        result, _, _ = self.create_operation(cid, context, current)
        op = result['data']['operation']['operation_id']
        self.append_mail(cid, 'Instead, please replace it with H-OTHER-SKU.')
        job, latest, _, _ = self.components()
        msg = latest.payload['messages'][-1]
        value = Understanding.model_validate(understanding([], intents=[{
            'business_type':'replacement', 'order_number':None, 'target_item':'H-OTHER-SKU', 'condition':None,
            'requested_solution':msg['body'], 'consent':'explicit', 'sources':[{'message_id':msg['message_id'], 'quote':msg['body']}]}]))
        save_understanding(self.engine, self.store, latest.workspace_id, job, validate_sources(value, latest.payload))
        self.reject_expected(op, cid, 'Latest understanding explicitly selects a different replacement SKU')
