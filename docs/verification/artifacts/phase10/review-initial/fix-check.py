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

class AddressAndGateFix(AfterSalesFixture):
    def test_previous_address_source_rejected(self):
        cid, context, command = self.prepared('replacement')
        self.append_mail(cid, 'My delivery address has changed. Do not use the old address.')
        conv = self.conversation(cid)
        fact = BranchFact(conversation_id=cid, expected_version=conv['row_version'], source_event_id='review-fixed-old-address',
            order_line_id=command.order_line_id, event='address_confirmation', expected_business_version=0,
            business_version=1, staff_id='review-staff', receipt_ref='review-old-address-proof',
            reason='Must refuse old source after latest customer change', confirmed=True, selection_ref=command.selection_ref)
        self.assert_error('address_source_superseded', lambda: BranchFactsService(self.engine, self.store).event(
            UUID(str(conv['branch_id'])), fact, uuid4().hex))
        print('FIX_OLD_ADDRESS_SOURCE_REJECTED address_source_superseded')

    def test_unrelated_return_gate_blocked(self):
        observation = {'ledger': {'operations': [
            {'operation_id': 'REF-A', 'kind': 'refund', 'order_id': 'ORDER-A', 'order_line_id': 'LINE-A',
             'managed': True, 'status': 'accepted', 'version': 1, 'quantity': 1, 'plan': {}},
            {'operation_id': 'RET-B', 'kind': 'return', 'order_id': 'ORDER-B', 'order_line_id': 'LINE-B',
             'managed': True, 'status': 'accepted', 'version': 1, 'quantity': 1, 'plan': {}}],
            'executions': [], 'shipments': [], 'returns': []}}
        event = {'gate': {'operation_required': {'kind': 'refund', 'order_line_id': 'LINE-A'}}, 'payload': {'record': {}}}
        result = verify_business_gate(None, 'after_internal_return_request', event, observation, {})
        print('FIX_CROSS_ORDER_RETURN_GATE', json.dumps(result.record()))
        self.assertEqual(result.status, 'blocked')

unittest.main(verbosity=2)
