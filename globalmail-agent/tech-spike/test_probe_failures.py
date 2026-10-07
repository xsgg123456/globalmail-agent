"""Offline regressions for failed reruns and independent resource cleanup."""
import json
import tempfile
import unittest
from pathlib import Path
from probe_support import cleanup_database, run_reported, write_report


class FailureTests(unittest.TestCase):
    def test_failure_replaces_old_green_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'report.json'
            write_report(path,{'passed':True,'checks':[{'passed':True}]})
            def fail():
                raise TimeoutError('Synthetic timeout')
            with self.assertRaises(SystemExit) as caught:
                run_reported(path,fail)
            self.assertEqual(caught.exception.code,1)
            result=json.loads(path.read_text(encoding='utf-8'))
            self.assertFalse(result['passed'])
            self.assertEqual(result['status'],'failed')
            self.assertEqual(result['error_type'],'TimeoutError')
            self.assertEqual(result['checks'],[])

    def test_success_preserves_final_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'report.json'
            run_reported(path,lambda:write_report(path,{'passed':True,'checks':[{'name':'real-check','passed':True}]}))
            result=json.loads(path.read_text(encoding='utf-8'))
            self.assertTrue(result['passed'])
            self.assertEqual(result['status'],'completed')
            self.assertEqual(result['checks'][0]['name'],'real-check')

    def test_cleanup_daemon_failure_still_removes_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'temporary.env'
            path.write_text('synthetic credential',encoding='utf-8')
            calls=[]
            def docker(*args):
                calls.append(args[0])
                raise RuntimeError('Container already exited or daemon unavailable')
            result={'passed':True}
            self.assertFalse(cleanup_database(docker,'container-id','owned',path,result))
            self.assertFalse(path.exists())
            self.assertEqual(calls,['inspect'])
            self.assertTrue(result['temporary_credentials_removed'])
            self.assertFalse(result['passed'])

    def test_foreign_container_is_not_stopped(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'temporary.env'
            path.write_text('synthetic credential',encoding='utf-8')
            calls=[]
            def docker(*args):
                calls.append(args[0])
                return 'different-owner'
            result={'passed':True}
            self.assertFalse(cleanup_database(docker,'container-id','owned',path,result))
            self.assertEqual(calls,['inspect'])
            self.assertFalse(path.exists())


if __name__=='__main__':
    unittest.main()
