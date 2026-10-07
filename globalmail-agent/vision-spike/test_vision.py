"""Offline boundary and real SDK transport-failure regression tests."""
import copy
import io
import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx
from openai import OpenAI
from PIL import Image

from prepare_views import CONFIG, DATA, prepare, sha
from probe_vision import Budget, request_payload, run_one
from validate_fixtures import read_rows


class VisionTests(unittest.TestCase):
    def setUp(self):
        self.row = copy.deepcopy(read_rows(DATA / 'manifest.jsonl')[0])

    def test_actual_png_decode_and_coordinate_provenance(self):
        views, coverage = prepare(self.row)
        self.assertEqual(coverage[0]['status'], 'ready')
        self.assertEqual(views[0]['source_size'], (1100, 640))
        self.assertEqual(len(views[0]['derived_sha256']), 64)

    def test_all_scope_dimensions_and_history(self):
        for key in ('customer', 'mode', 'branch', 'purpose'):
            with self.subTest(key=key):
                row = copy.deepcopy(self.row)
                row['attachments'][0]['scope'][key] = 'foreign'
                with self.assertRaisesRegex(ValueError, 'scope_denied'):
                    prepare(row)
        self.row['attachments'][0]['message_seq'] = 2
        with self.assertRaisesRegex(ValueError, 'future_image'):
            prepare(self.row)

    def test_revocation_and_privacy(self):
        self.row['attachments'][0]['revoked'] = True
        with self.assertRaisesRegex(ValueError, 'revoked'):
            prepare(self.row)
        self.row['attachments'][0]['revoked'] = False
        self.row['attachments'][0]['privacy_review'] = 'unreviewed'
        with self.assertRaisesRegex(ValueError, 'unreviewed_source'):
            prepare(self.row)

    def test_traversal_and_hash_change(self):
        self.row['attachments'][0]['path'] = '../evaluation/labels.jsonl'
        with self.assertRaisesRegex(ValueError, 'outside_images'):
            prepare(self.row)
        self.row['attachments'][0]['path'] = 'images/label.png'
        self.row['attachments'][0]['sha256'] = 'bad'
        with self.assertRaisesRegex(ValueError, 'source_hash_mismatch'):
            prepare(self.row)

    def test_count_boundary_never_silently_truncates(self):
        self.row['attachments'] *= 5
        with self.assertRaisesRegex(ValueError, 'image_count_limit'):
            prepare(self.row)

    def test_missing_and_corrupt_are_distinct(self):
        self.row['attachments'][0]['path'] = 'images/not-present.png'
        self.assertEqual(prepare(self.row)[1][0]['status'], 'missing')
        self.row['attachments'][0].update(path='images/corrupt.jpg', sha256=sha((DATA / 'images/corrupt.jpg').read_bytes()))
        self.assertEqual(prepare(self.row)[1][0]['status'], 'unreadable')

    def test_byte_limits_using_real_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'images').mkdir()
            data = (DATA / 'images/label.png').read_bytes()
            # Valid PNG with trailing padding is still rejected by byte count before decode.
            data += bytes(CONFIG['max_bytes'] + 1 - len(data))
            (root / 'images/label.png').write_bytes(data)
            self.row['attachments'][0]['sha256'] = sha(data)
            with self.assertRaisesRegex(ValueError, 'byte_limit'):
                prepare(self.row, root=root)

    def test_pixel_limit_and_animation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'images').mkdir()
            path = root / 'images/label.png'
            Image.new('RGB', (5001, 4000)).save(path)
            self.row['attachments'][0]['sha256'] = sha(path.read_bytes())
            with self.assertRaisesRegex(ValueError, 'pixel_limit'):
                prepare(self.row, root=root)
            Image.new('RGB', (100, 100)).save(path, save_all=True,
                append_images=[Image.new('RGB', (100, 100), 'red')], duration=100, loop=0)
            self.row['attachments'][0]['sha256'] = sha(path.read_bytes())
            self.assertEqual(prepare(self.row, root=root)[1][0]['status'], 'unsupported')

    def test_payload_allowlist_never_labels_or_faults(self):
        self.row['reference_reply'] = 'FORBIDDEN_SENTINEL'
        self.row['options']['future_event'] = 'FORBIDDEN_SENTINEL'
        self.row['allowed_routes'] = ['FORBIDDEN_SENTINEL']
        views, coverage = prepare(self.row)
        payload = json.dumps(request_payload(self.row, views, coverage))
        self.assertNotIn('FORBIDDEN_SENTINEL', payload)
        self.assertNotIn('label.png', payload)

    def test_crop_is_bounded_and_shares_view_budget(self):
        full, _ = prepare(self.row)
        cropped, _ = prepare(self.row, 'crop')
        self.assertEqual(cropped[0]['source_box'], [0, 0, 900, 450])
        self.assertNotEqual(full[0]['derived_sha256'], cropped[0]['derived_sha256'])
        budget = Budget()
        budget.reserve(1000, 4)
        budget.reserve(1000, 2)
        with self.assertRaisesRegex(ValueError, 'budget_exhausted'):
            budget.reserve(1000, 1)

    def test_unknown_usage_keeps_reservation(self):
        budget = Budget()
        reservation = budget.reserve(10000, 1)
        budget.settle(reservation, None)
        self.assertEqual(budget.tokens, 12000)
        self.assertTrue(budget.unknown_usage)

    def test_call_time_and_token_boundaries(self):
        for mutate in (lambda b: setattr(b, 'calls', 6), lambda b: setattr(b, 'tokens', 79000),
                       lambda b: setattr(b, 'started', time.monotonic() - 121)):
            budget = Budget()
            mutate(budget)
            with self.assertRaises(ValueError):
                budget.reserve(1000, 1)
        with self.assertRaises(ValueError):
            Budget().reserve(16001, 1)

    def sdk_call(self, handler):
        transport = httpx.MockTransport(handler)
        with OpenAI(api_key='synthetic-test-key', base_url='https://example.invalid/v1',
                    http_client=httpx.Client(transport=transport), max_retries=0) as client:
            return run_one(client, self.row, 'full', Budget(), 'qwen3.7-plus')

    def test_auth_and_server_failure_no_error_body_leak(self):
        for code in (401, 403, 429, 500):
            result = self.sdk_call(lambda request: httpx.Response(code, json={'error': {'message': 'PRIVATE_SENTINEL'}}))
            self.assertEqual(result['status'], 'failed')
            self.assertEqual(result['http_status'], code)
            self.assertNotIn('PRIVATE_SENTINEL', json.dumps(result))
            self.assertEqual(result['budget']['calls'], 1)

    def test_timeout_is_technical_not_image_quality(self):
        def handler(request):
            raise httpx.ReadTimeout('PRIVATE_SENTINEL', request=request)
        result = self.sdk_call(handler)
        self.assertEqual(result['error_type'], 'APITimeoutError')
        self.assertEqual(result['coverage_input'][0]['status'], 'ready')
        self.assertTrue(result['budget']['usage_unknown'])
        self.assertNotIn('PRIVATE_SENTINEL', json.dumps(result))

    def test_no_image_no_added_request(self):
        self.row['attachments'] = []
        result = run_one(None, self.row, 'full', Budget(), 'qwen3.7-plus')
        self.assertEqual(result['status'], 'text_path_no_added_vision_request')
        self.assertEqual(result['budget']['calls'], 0)


if __name__ == '__main__':
    unittest.main()
