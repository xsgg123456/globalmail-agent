"""Fail closed on failed reruns, stale snapshots and tampered intermediate data."""
import unittest
from unittest.mock import patch

from artifact_contract import verify_dataset
from common import fingerprint
import probe_evidence
import probe_retrieval


class ArtifactContract(unittest.TestCase):
    def setUp(self):
        self.model = 'qwen3.7-text-embedding'
        self.strategy = 'structured500'
        vector = [1.0]+[0.0]*1023
        self.data = {'chunks':[{'text':'original'}], 'queries':[{'query':'question'}],
                     'vectors':[vector], 'query_vectors':[vector],
                     'profile':{'model':self.model}, 'run_id':'new-run'}
        self.snapshot = {'parents':'parent-hash', 'queries':fingerprint(self.data['queries']),
                         'strategies':{self.strategy:fingerprint(self.data['chunks'])}}
        self.data['input_snapshot'] = self.snapshot
        self.report = {'status':'completed','all_models_completed':True,'run_id':'new-run',
                       'input_snapshot':self.snapshot, 'models':[{'model':self.model,'status':'completed',
                        'artifact_fingerprints':{self.strategy:fingerprint(self.data)}}]}

    def test_matching_successful_run_is_accepted(self):
        self.assertIs(verify_dataset(self.report,self.data,self.model,self.strategy,self.snapshot),self.data)

    def test_failed_model_cannot_reuse_successful_artifact(self):
        self.report['models'][0]['status'] = 'failed'
        with self.assertRaises(ValueError):
            verify_dataset(self.report,self.data,self.model,self.strategy,self.snapshot)

    def test_run_source_and_payload_mismatches_are_rejected(self):
        for change in ({'run_id':'old-run'}, {'vectors':[[0.0]*1024]}, {'chunks':[{'text':'tampered'}]}):
            with self.assertRaises(ValueError):
                verify_dataset(self.report,{**self.data,**change},self.model,self.strategy,self.snapshot)
        with self.assertRaises(ValueError):
            verify_dataset(self.report,self.data,self.model,self.strategy,{**self.snapshot,'parents':'changed'})

    def test_incomplete_upstream_stops_before_guard_calls(self):
        with patch('probe_evidence.load_verified_dataset',side_effect=ValueError('stale')):
            with patch('probe_evidence.ask_guard') as guard:
                with self.assertRaises(ValueError):
                    probe_evidence.main()
                guard.assert_not_called()

    def test_candidate_model_failure_marks_comparison_failed(self):
        queries = [{'kind':kind,'query':'q'} for kind,count in
                   [('positive',36),('boundary',12),('unanswerable',6),('multi_evidence',6)] for _ in range(count)]
        inputs = (queries,{}, {'structured500':[{'embedding_input':'body'}]}, {})
        with patch('probe_retrieval.current_inputs',return_value=inputs), patch('probe_retrieval.write'), \
                patch('probe_retrieval.evaluate',return_value={'summary':{},'observations':[]}), \
                patch('probe_retrieval.embed',side_effect=[([[1.0]]*61,{'profile':{}}),ValueError('failed')]):
            result = probe_retrieval.main()
        self.assertTrue(result['baseline_available'])
        self.assertFalse(result['all_models_completed'])
        self.assertEqual(result['status'],'failed')


if __name__ == '__main__':
    unittest.main()
