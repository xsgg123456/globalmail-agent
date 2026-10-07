"""Regression checks for dangerous scope and evidence-assembly failures."""
import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from common import HERE, WORK, read, execute_report
from chunking import Budget, build_chunks, eligible, load_documents, split_units
from parse_one import content_text, table_rows
from probe_retrieval import evidence_covered
from probe_evidence import assemble


class KnowledgeContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs = load_documents()
        cls.budget = Budget()
        cls.chunks = build_chunks(cls.docs,'structured500',cls.budget)
        cls.queries = [json.loads(x) for x in (HERE/'retrieval-queries.jsonl').read_text(encoding='utf-8').splitlines()]

    def test_brand_mode_time_and_unknown_identity_are_denied(self):
        query = self.queries[0]
        candidates = [c for c in self.chunks if eligible(c,query)]
        self.assertTrue(candidates)
        for change in [{'brand':'BELEEV'},{'mode':'historical_eval'},
                       {'as_of':'2026-10-07T03:00:38+00:00'},{'sku':'H-CTD16-UNKNOWN'}]:
            self.assertFalse(any(eligible(c,{**query,**change}) for c in self.chunks))
        for c in candidates:
            self.assertFalse(eligible({**c,'usage_split':'eval_holdout'},query))

    def test_all_frozen_boundary_queries_have_no_allowed_candidate(self):
        for query in self.queries:
            if query['kind']=='boundary':
                self.assertFalse(any(eligible(c,query) for c in self.chunks), query['query_id'])

    def test_sop_actions_retain_precautions_and_stop_conditions(self):
        for d in self.docs:
            if d['document_type']!='troubleshooting_md':
                continue
            stop = next(s['text'] for s in d['sections'] if s['heading']=='交给人工的情况')
            steps = [c for c in self.chunks if c['document_id']==d['document_id'] and c['heading']=='怎么处理']
            self.assertTrue(steps)
            for c in steps:
                self.assertIn(stop,c['text'])
                self.assertEqual(c['skus'],d['skus'])

    def test_changed_body_or_embedded_heading_changes_reuse_key(self):
        original = build_chunks(self.docs,'structured500',self.budget)
        edited = copy.deepcopy(self.docs)
        edited[0]['title'] += ' 修订'
        revised = build_chunks(edited,'structured500',self.budget)
        old = {c['chunk_id']:c['input_hash'] for c in original}
        self.assertTrue(all(c['input_hash']!=old[c['chunk_id']] for c in revised
                            if c['document_id']==edited[0]['document_id']))
        self.assertTrue(all(c['input_hash']==old[c['chunk_id']] for c in revised
                            if c['document_id']!=edited[0]['document_id']))

    def test_metadata_change_reuses_vector_input_but_restricts_scope(self):
        docs = copy.deepcopy(self.docs)
        original = build_chunks(docs,'structured500',self.budget)
        docs[0]['skus'] = []
        revised = build_chunks(docs,'structured500',self.budget)
        self.assertEqual([c['input_hash'] for c in original],[c['input_hash'] for c in revised])
        self.assertFalse(any(eligible(c,self.queries[0]) for c in revised
                             if c['document_id']==docs[0]['document_id']))

    def test_structured_parser_excludes_assets_and_keeps_table_cells(self):
        block = {'type':'image','content':[{'type':'image_body','content':'data:image/png;base64,SECRET'},
                                         {'type':'image_caption','content':'Disconnect power first'}]}
        self.assertEqual(content_text(block),'Disconnect power first')
        table = {'type':'table_body','content':'<table><tr><th>Voltage</th><td>12 V</td></tr></table>'}
        self.assertEqual(table_rows(table),[['Voltage','12 V']])
        self.assertIn('12 V',content_text(table))

    def test_evidence_requires_correct_document_and_relevant_text(self):
        ev = self.queries[0]['evidence'][0]
        wrong = {'document_id':'WRONG','text':ev['required_any'][0]}
        self.assertFalse(evidence_covered(ev,[wrong]))
        self.assertFalse(evidence_covered(ev,[{**wrong,'document_id':ev['document_id'],'text':'irrelevant'}]))

    def test_long_steps_split_without_crossing_budget(self):
        text = '\n'.join(f'{i}. Disconnect the supply and verify step {i} before continuing.' for i in range(1,41))
        blocks = split_units(text,self.budget,100)
        self.assertGreater(len(blocks),1)
        self.assertTrue(all(self.budget.count(b)<=100 for b in blocks))
        self.assertEqual(sum(b.count('Disconnect') for b in blocks),40)

    def test_diversity_and_budget_apply_before_parent_expansion(self):
        data = read(WORK/'retrieval-qwen3.7-text-embedding-structured500.json')
        data['chunks'] = self.chunks
        parents = {d['parent_id']:d for d in self.docs}
        evidence = assemble(data,0,parents,token_budget=1200)
        self.assertEqual(len(evidence),len({c['parent_id'] for c in evidence}))
        self.assertLessEqual(sum(self.budget.count(c['text']) for c in evidence),1200)
        self.assertTrue(all(eligible(c,data['queries'][0]) for c in evidence))

    def test_parent_expansion_rejects_scope_version_body_and_missing_parent(self):
        data = read(WORK/'retrieval-qwen3.7-text-embedding-structured500.json')
        data['chunks'] = self.chunks
        parents = {d['parent_id']:d for d in self.docs}
        self.assertTrue(assemble(data,0,parents))
        for mutation in ({'skus':[]}, {'allowed_modes':[]}, {'version':'stale'},
                         {'usage_split':'eval_holdout'}, {'text':'changed content'}):
            altered = {key:{**p,**mutation} for key,p in parents.items()}
            self.assertEqual(assemble(data,0,altered),[],mutation)
        self.assertEqual(assemble(data,0,{}),[])

    def test_failure_replaces_stale_report(self):
        with tempfile.TemporaryDirectory(dir=WORK) as directory:
            target = Path(directory)/'result.json'
            target.write_text('{"status":"completed","passed":true}',encoding='utf-8')
            with patch('common.HERE',Path(directory)):
                with self.assertRaises(SystemExit):
                    execute_report('result.json',lambda:(_ for _ in ()).throw(ValueError('redacted')))
            value = read(target)
            self.assertEqual(value['status'],'failed')
            self.assertNotIn('passed',value)
            self.assertNotIn('redacted',target.read_text())


if __name__=='__main__':
    unittest.main()
