"""Mutation checks ensure the data validator actually rejects key regressions."""
import copy
import unittest
from journey_common import OUT, read, rows
from validate_journeys import inspect


class IntegrityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = [rows(OUT / 'scenarios/journeys/inputs.jsonl'), rows(OUT / 'scenarios/journeys/controller-events.jsonl'),
                    rows(OUT / 'evaluation/journey-assertions.jsonl'), read(OUT / 'scenarios/journeys/manifest.json'),
                    read(OUT / 'scenarios/journeys/artifacts.json')]

    def result(self, data, name):
        return next(c['passed'] for c in inspect(*data) if c['name'] == name)

    def test_baseline_valid(self):
        self.assertTrue(all(c['passed'] for c in inspect(*self.base)))

    def test_future_answer_leak_is_rejected(self):
        data = copy.deepcopy(self.base)
        data[0][0]['reference_reply'] = 'The refund is already complete.'
        self.assertFalse(self.result(data, 'reference replies and expected actions absent from inputs and controller events'))

    def test_excess_refund_is_rejected(self):
        data = copy.deepcopy(self.base)
        event = next(e for e in data[1] if e['kind'] == 'execution_record' and e['payload']['record'].get('kind') == 'refund' and e['payload']['record'].get('status') == 'succeeded')
        event['payload']['record']['amount_minor'] = 99999999
        self.assertFalse(self.result(data, 'refund amount currency and total consistent'))

    def test_cross_order_reference_is_rejected(self):
        data = copy.deepcopy(self.base)
        event = next(e for e in data[1] if e['kind'] == 'execution_record')
        event['payload']['record']['order_id'] = 'different-customer-order'
        self.assertFalse(self.result(data, 'record order and execution references resolve'))

    def test_reference_reply_cannot_contain_internal_tokens(self):
        data = copy.deepcopy(self.base)
        data[2][0]['reference_reply'] = 'Your SIM-OP-001 is in HITL.'
        self.assertFalse(self.result(data, 'customer facing correspondence contains no test vocabulary'))

    def test_failed_inspection_blocks_replacement(self):
        data = copy.deepcopy(self.base)
        event = next(e for e in data[1] if e['event_id'] == 'JRN-06-s09')
        event['payload']['record'].update(received=False, inspection='failed')
        self.assertFalse(self.result(data, 'full refunds and replacement follow warehouse inspection'))

    def test_missing_customer_acceptance_blocks_partial_refund(self):
        data = copy.deepcopy(self.base)
        next(a for a in data[2] if a['event_id'] == 'JRN-04-s04')['evaluation_facts'] = {}
        self.assertFalse(self.result(data, 'partial refunds follow explicit amount acceptance within policy cap'))

    def test_old_address_version_blocks_dispatch(self):
        data = copy.deepcopy(self.base)
        event = next(e for e in data[1] if e['event_id'] == 'JRN-19-s13')
        event['payload']['record']['address_version'] = 1
        self.assertFalse(self.result(data, 'dispatch uses confirmed current address with customer evidence'))


if __name__ == '__main__':
    unittest.main()
