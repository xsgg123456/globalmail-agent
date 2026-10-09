import hashlib
import io
import json
from pathlib import Path
import sys
import time
import unittest
from uuid import UUID, uuid4

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / 'globalmail-agent/backend'
sys.path[:0] = [str(BACKEND / 'src'), str(BACKEND / 'tests'), str(ROOT / 'globalmail-agent/agent-eval')]
from bootstrap import isolated_database_environment
isolated_database_environment()
from PIL import Image
from vision_fixture import VisionFixture, VisionModel, image_output, handoff
from globalmail_agent.attachments.corrections import EvidenceService, EvidenceCommand
from globalmail_agent.domain.conversation import Takeover

def snapshot():
    paths = [p for folder in ('src', 'tests', 'migrations') for p in (BACKEND / folder).rglob('*')
             if p.is_file() and p.suffix in ('.py', '.md')]
    return {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}

class Review7ThumbnailTests(VisionFixture):
    def test_real_exif_thumbnail_scope_and_revocation_http(self):
        raw = io.BytesIO()
        exif = Image.Exif()
        exif[274] = 6
        Image.new('RGB', (1200, 600), '#347892').save(raw, 'JPEG', exif=exif)
        uploaded = self.stage(email='review7-exif@example.test', content=raw.getvalue(), filename='photo.jpg')
        cid, aid = UUID(uploaded['conversation_id']), uploaded['attachment_id']
        params = {'conversation_id': str(cid), 'thumbnail': 'true'}
        thumbnail = self.client.get(f'/api/v1/attachments/{aid}/preview', params=params)
        self.assertEqual(thumbnail.status_code, 200, thumbnail.text)
        decoded = Image.open(io.BytesIO(thumbnail.content))
        decoded.load()
        self.assertEqual(decoded.size, (256, 512))
        self.assertEqual(thumbnail.headers['cache-control'], 'no-store')
        self.assertEqual(thumbnail.headers['x-content-type-options'], 'nosniff')
        other, _ = self.create('review7-other@example.test')
        denied = self.client.get(f'/api/v1/attachments/{aid}/preview', params={**params, 'conversation_id': str(other)})
        self.assertEqual(denied.status_code, 404)
        self.post('/conversations', {'expected_version': 0, 'sender_email':'review7-exif@example.test',
            'body':'', 'attachments':[{'attachment_id': aid}]}).raise_for_status()
        self.service.takeover(cid, Takeover(expected_version=self.conversation(cid)['row_version']), uuid4().hex)
        conv = self.conversation(cid)
        EvidenceService(self.engine, self.store).mutate(UUID(aid), EvidenceCommand(
            expected_version=conv['row_version'], expected_input_revision=conv['input_revision'], evidence_revision=0), uuid4().hex, revoke=True)
        statuses = {}
        for thumb in ('true', 'false'):
            response = self.client.get(f'/api/v1/attachments/{aid}/preview', params={**params,'thumbnail':thumb})
            self.assertEqual(response.status_code, 410, response.text)
            statuses[thumb] = response.status_code
        print('REVIEW7_REAL_THUMBNAIL', json.dumps({'decoded_size': decoded.size, 'scope_denied':denied.status_code,
            'cache_control':thumbnail.headers['cache-control'], 'after_revoke':statuses}))

before = snapshot()
names = ['test_attachment_binding', 'test_attachment_lifecycle', 'test_vision_import',
    'test_vision_provider', 'test_vision_graph', 'test_vision_corrections', 'test_vision_risks', '__main__.Review7ThumbnailTests']
suite = unittest.defaultTestLoader.loadTestsFromNames(sys.argv[1:] or names)
started = time.monotonic()
result = unittest.TextTestRunner(verbosity=2).run(suite)
after = snapshot()
report = {'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),
    'skipped':len(result.skipped),'duration_seconds':time.monotonic()-started,'source_changed':before != after,
    'before':before,'after':after}
target = ROOT / 'tmp/phase8-review7'
target.mkdir(exist_ok=True)
(target / ('thumbnail-tests.json' if sys.argv[1:] else 'independent-tests.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
print('REVIEW7_TEST_RESULT', json.dumps({k:v for k,v in report.items() if k not in ('before','after')}))
raise SystemExit(not result.wasSuccessful() or bool(result.skipped) or before != after)
