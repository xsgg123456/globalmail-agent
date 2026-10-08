"""Real owned child boundaries; no provider network calls in these tests."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from globalmail_agent.application.conversation_lock import ServiceError
from globalmail_agent.knowledge.embedding import EmbeddingGateway, normalize_vector, probe_matches
from globalmail_agent.knowledge.embedding_process import child_environment, run_embedding_child
from globalmail_agent.settings import Settings


class EmbeddingTests(unittest.TestCase):
    def gateway(self, base='https://dashscope.aliyuncs.com/compatible-mode/v1'):
        return EmbeddingGateway(Settings(model_base_url=base, model_api_key='unit-test-secret'))

    def test_finite_dimensions_normalization_and_probe(self):
        vector = [3., 4.] + [0.] * 1022
        result = normalize_vector(vector)
        self.assertAlmostEqual(math.hypot(*result), 1., places=6)
        self.assertTrue(probe_matches(vector, result))
        self.assertFalse(probe_matches(vector, [1.] + [0.] * 1023))
        for invalid in ([0.] * 1024, [1.] * 1023, [True] + [0.] * 1023,
                        [math.nan] + [1.] * 1023, [math.inf] + [1.] * 1023):
            with self.assertRaises(ServiceError) as error:
                normalize_vector(invalid)
            self.assertEqual(error.exception.code, 'embedding_output_invalid')

    def test_safe_profiles_and_exact_endpoint(self):
        profile = self.gateway().profiles()[0]
        self.assertTrue(profile['available'])
        self.assertNotIn('unit-test-secret', json.dumps(profile))
        self.assertNotIn('base_url', profile)
        for base in ('http://dashscope.aliyuncs.com/compatible-mode/v1',
                     'https://dashscope.aliyuncs.com.evil.test/compatible-mode/v1',
                     'https://dashscope-intl.aliyuncs.com/compatible-mode/v1',
                     'https://user:secret@dashscope.aliyuncs.com/compatible-mode/v1',
                     'https://dashscope.aliyuncs.com:bad/compatible-mode/v1',
                     'https://[broken', ''):
            self.assertFalse(self.gateway(base).profiles()[0]['available'])

    def test_input_and_drift_never_silently_pass(self):
        gateway = self.gateway(); profile = gateway.profiles()[0]
        with patch('globalmail_agent.knowledge.embedding.embed_child') as child:
            for texts in ([], [''] , ['a'] * 10, ['a'] * 1 + ['中' * 4001]):
                with self.assertRaises(ServiceError): gateway.embed(profile, texts)
            child.assert_not_called()
            child.return_value = {'vectors': [[1.] + [0.] * 1023] * 2, 'usage': {}}
            output = gateway.embed(profile, ['完整输入'])
            self.assertEqual(len(output['vectors'][0]), 1024)
            with self.assertRaises(ServiceError) as error:
                gateway.embed({**profile, 'probe_vector': [0., 1.] + [0.] * 1022}, ['完整输入'])
            self.assertEqual(error.exception.code, 'embedding_model_drift')

    def test_child_has_only_provider_secrets(self):
        with patch.dict(os.environ, {'GLOBALMAIL_DATABASE_URL': 'db-unit-secret',
            'LLM_API_KEY': 'chat-unit-secret', 'VITE_KEY': 'browser-unit-secret'}):
            environment = child_environment('https://configured.test', 'embedding-unit-secret')
        self.assertEqual(environment['GLOBALMAIL_EMBEDDING_API_KEY'], 'embedding-unit-secret')
        self.assertNotIn('GLOBALMAIL_DATABASE_URL', environment)
        self.assertNotIn('LLM_API_KEY', environment)
        self.assertNotIn('VITE_KEY', environment)

    def child(self, code, **options):
        real_popen = subprocess.Popen; processes = []
        def start(*args, **kwargs):
            process = real_popen(*args, **kwargs); processes.append(process); return process
        with TemporaryDirectory(prefix='globalmail_embedding_test_') as name:
            directory = Path(name)
            with patch('globalmail_agent.knowledge.embedding_process.subprocess.Popen', side_effect=start):
                try:
                    return run_embedding_child([sys.executable, '-c', code], directory,
                        child_environment('', ''), options.pop('current', lambda: True),
                        options.pop('stopped', lambda: False), **options)
                finally:
                    self.assertTrue(all(p.poll() is not None for p in processes))

    def test_actual_child_success_and_redacted_failure(self):
        self.assertEqual(self.child("from pathlib import Path; Path('result.json').write_text('{\"vectors\":[]}')"), {'vectors': []})
        with self.assertRaises(ServiceError) as error:
            self.child("from pathlib import Path; Path('result.json').write_text('{\"error\":\"unit-secret-server-body\"}'); raise SystemExit(1)")
        self.assertEqual(error.exception.code, 'embedding_provider_error')

    def test_actual_child_timeout_stops_owned_process(self):
        with self.assertRaises(ServiceError) as error:
            self.child('import time; time.sleep(30)', timeout=.15)
        self.assertEqual(error.exception.code, 'embedding_timeout')

    def test_actual_child_lease_revocation_and_late_output(self):
        states = iter([True, False])
        with self.assertRaises(ServiceError) as error:
            self.child('import time; time.sleep(30)', current=lambda: next(states), heartbeat_interval=.05)
        self.assertEqual(error.exception.code, 'embedding_cancelled')
        states = iter([True, False])
        with self.assertRaises(ServiceError):
            self.child("from pathlib import Path; Path('result.json').write_text('{}')", current=lambda: next(states))

    def test_actual_child_invalid_or_oversized_output(self):
        for content in ('[]', 'not-json', 'x' * (4 * 1024 * 1024 + 1)):
            with self.assertRaises(ServiceError) as error:
                self.child('from pathlib import Path; Path("result.json").write_text(' + repr(content) + ')'
                    if len(content) < 100 else 'from pathlib import Path; Path("result.json").write_text("x" * (4*1024*1024+1))')
            self.assertEqual(error.exception.code, 'embedding_output_invalid')


if __name__ == '__main__': unittest.main()
