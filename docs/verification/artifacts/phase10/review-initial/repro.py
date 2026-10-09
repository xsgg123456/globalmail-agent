from pathlib import Path
import sys, unittest, json
from uuid import UUID, uuid4
root = next(path for path in Path(__file__).resolve().parents if (path / 'Product-Spec.md').is_file())
backend = root / 'globalmail-agent/backend'
sys.path[:0] = [str(backend / 'src'), str(backend / 'tests'), str(root / 'globalmail-agent/agent-eval')]
from bootstrap import isolated_database_environment
isolated_database_environment()
from after_sales_fixture import AfterSalesFixture
from globalmail_agent.application.branch_facts import BranchFactsService
from globalmail_agent.domain.business_events import BranchFact
from globalmail_agent.evaluation.service_gates import verify_business_gate

class IndependentReview(AfterSalesFixture):
    def test_correction_not_executed_releases_original_compensation(self):
        self.publish_policy()
        cid, context, request = self.prepared('spare_part')
        output, _, _ = self.create_operation(cid, context, request)
        op = output['data']['operation']['operation_id']
        first = self.push(cid, op, 'create_execution')['executions'][0]['execution_id']
        self.push(cid, op, 'label_created', receipt_ref='review-label-one', carrier='Mock Carrier', tracking_number='FIRST')
        self.push(cid, op, 'shipped', receipt_ref='review-original-shipped')
        self.push(cid, op, 'succeeded', receipt_ref='review-original-success')
        corrected = self.push(cid, op, 'create_corrective_execution', staff_id='review-warehouse',
            correction_of_execution_id=first, receipt_ref='review-mispick-proof', reason='Wrong part dispatched')
        second = next(e['execution_id'] for e in corrected['executions'] if e['execution_id'] != first)
        self.push(cid, op, 'unknown', execution_id=second)
        result = self.push(cid, op, 'reconciled_not_executed', execution_id=second, confirmed_not_executed=True,
            receipt_ref='review-correction-not-sent', reason='Warehouse confirms second attempt not dispatched')
        import sqlalchemy as sa
        from globalmail_agent.adapters.after_sales_schema import compensation_reservations
        with self.engine.connect() as conn:
            active = conn.execute(sa.select(compensation_reservations.c.active)).scalar_one()
        print('REPRO_CORRECTION_NOT_EXECUTED', json.dumps({'original_execution': first,
            'operation': result['operations'][0], 'executions': result['executions'], 'compensation_active': active}, default=str))
        self.assertFalse(active)
        self.assertEqual(result['operations'][0]['status'], 'failed')
        self.assertTrue(result['operations'][0]['confirmed_not_executed'])

    def test_old_address_quote_accepted_after_new_customer_address(self):
        cid, context, command = self.prepared('replacement')
        old_ref = command.selection_ref
        self.append_mail(cid, 'My delivery address has changed. Do not use the old address. Please ask me for the new address before shipping.')
        conv = self.conversation(cid)
        fact = BranchFact(conversation_id=cid, expected_version=conv['row_version'], source_event_id='review-stale-address',
            order_line_id=command.order_line_id, event='address_confirmation', expected_business_version=0,
            business_version=1, staff_id='review-staff', receipt_ref='review-old-address-proof',
            reason='Attempt to rebind the old address after current customer changed it', confirmed=True,
            selection_ref=old_ref)
        result = BranchFactsService(self.engine, self.store).event(UUID(str(conv['branch_id'])), fact, uuid4().hex)
        print('REPRO_STALE_ADDRESS_ACCEPTED', json.dumps(result, default=str))
        from globalmail_agent.application.business_queries import BusinessQueries
        address = BusinessQueries(self.engine).detail(cid)['data']['address_confirmation']
        print('REPRO_CURRENT_ADDRESS', json.dumps(address, default=str))
        self.assertTrue(address['confirmed'])
        import sqlalchemy as sa
        from globalmail_agent.adapters.business_schema import simulation_branches
        with self.engine.connect() as conn:
            state = conn.execute(sa.select(simulation_branches.c.state).where(simulation_branches.c.id == conv['branch_id'])).scalar_one()
        print('REPRO_STORED_ADDRESS', json.dumps(state['address_confirmation']))
        self.assertEqual(state['address_confirmation']['source_kind'], 'customer_statement')

    def test_return_gate_accepts_other_order_return(self):
        observation = {'ledger': {'operations': [
            {'operation_id': 'REF-A', 'kind': 'refund', 'order_line_id': 'LINE-A', 'managed': True, 'version': 1, 'quantity': 1, 'plan': {}},
            {'operation_id': 'RET-B', 'kind': 'return', 'order_line_id': 'LINE-B', 'managed': True, 'version': 1, 'quantity': 1, 'plan': {}}],
            'executions': [], 'shipments': [], 'returns': []}}
        event = {'gate': {'operation_required': {'kind': 'refund', 'order_line_id': 'LINE-A'}}, 'payload': {'record': {}}}
        result = verify_business_gate(None, 'after_internal_return_request', event, observation, {})
        print('REPRO_CROSS_ORDER_RETURN_GATE', json.dumps(result.record()))
        self.assertEqual(result.status, 'passed')

unittest.main(verbosity=2)
