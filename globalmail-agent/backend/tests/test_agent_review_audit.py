"""Audit omission/forgery paths; exact quotations do not prove semantic entailment."""
from copy import deepcopy
import json
import unittest
from pydantic import ValidationError
from agent_fixture import AgentFixture, ScriptedModel, understanding, terminal
from globalmail_agent.agent.outcome_validation import OutcomeReview
from globalmail_agent.agent.review_audit import audit_accepts, trigger_units
from globalmail_agent.agent.tool_schemas import Draft


def example():
    mail = 'Please check my parcel. If it remains missing I will want a refund later, not now.'
    context = {'trigger_message_id': 'mail-1', 'messages': [{'message_id': 'mail-1', 'body': mail}],
        'human_notes': []}
    body = 'The parcel is in transit.\n\nYou want a refund later if still missing, not now.'
    draft = Draft.model_validate({'language': 'en', 'body': body, 'claims': [
        {'kind': 'order_fact', 'text': 'The parcel is in transit.', 'source_ids': ['command:scoped']},
        {'kind': 'customer_fact', 'text': 'You want a refund later if still missing, not now.', 'source_ids': ['mail-1']}],
        'citation_ids': [], 'waiting_for': 'customer_feedback'})
    observed = [{'content': json.dumps({'status': 'ok', 'command_source_id': 'command:scoped',
        'data': {'status': 'in_transit'}})}]
    review = {'request_checks': [
        {'unit_index': 0, 'status': 'addressed', 'reply_quote': draft.claims[0].text},
        {'unit_index': 1, 'status': 'addressed', 'reply_quote': draft.claims[1].text}],
        'source_checks': [
            {'claim_index': 0, 'supported': True, 'evidence': [{'source_id': 'command:scoped', 'quote': 'in_transit'}]},
            {'claim_index': 1, 'supported': True, 'evidence': [{'source_id': 'mail-1', 'quote': mail}]}],
        'supported': True, 'language_correct': True, 'unsupported_claims': [],
        'reason': 'Explicit protocol evidence, not a real-model quality judgement.'}
    return context, observed, draft, review


class ReviewAuditTests(unittest.TestCase):
    def accepted(self, change=None):
        context, observed, draft, review = example()
        if change:
            change(review)
        return audit_accepts(OutcomeReview.model_validate(review), context, observed, draft)

    def test_complete_original_units_and_exact_scoped_quotes_pass_protocol(self):
        self.assertTrue(self.accepted())

    def test_sentence_units_preserve_every_character_without_keyword_classification(self):
        for body in ('你好。\nIf lost, refund later; not now! ', 'SKU A.B?\n\n规格不明。', '\n', ''):
            context = {'messages': [{'message_id': 'x', 'body': body}], 'trigger_message_id': 'x'}
            self.assertEqual(''.join(trigger_units(context)), body)

    def test_omitted_last_conditional_unit_cannot_hide_behind_total_true(self):
        self.assertFalse(self.accepted(lambda value: value['request_checks'].pop()))
        self.assertFalse(self.accepted(lambda value: value['request_checks'][1].update(status='omitted')))
        self.assertFalse(self.accepted(lambda value: value['request_checks'][1].update(status='changed_condition')))

    def test_duplicate_or_out_of_range_request_unit_rejects(self):
        for index in (0, 2):
            self.assertFalse(self.accepted(lambda value: value['request_checks'][1].update(unit_index=index)))

    def test_missing_or_fabricated_reply_quote_rejects(self):
        for quote in ('', 'We refunded you already.'):
            self.assertFalse(self.accepted(lambda value: value['request_checks'][1].update(reply_quote=quote)))

    def test_missing_duplicate_or_out_of_range_claim_index_rejects(self):
        self.assertFalse(self.accepted(lambda value: value['source_checks'].pop()))
        for index in (0, 2):
            self.assertFalse(self.accepted(lambda value: value['source_checks'][1].update(claim_index=index)))

    def test_negative_claim_cannot_be_overridden_by_total_supported(self):
        self.assertFalse(self.accepted(lambda value: value['source_checks'][0].update(supported=False)))

    def test_true_source_id_with_invented_translation_quote_rejects(self):
        self.assertFalse(self.accepted(lambda value: value['source_checks'][0]['evidence'][0].update(quote='ceiling light')))

    def test_existing_but_unclaimed_or_foreign_source_cannot_authorize_claim(self):
        for source in ('mail-1', 'command:foreign'):
            self.assertFalse(self.accepted(lambda value: value['source_checks'][0]['evidence'][0].update(source_id=source)))

    def test_fact_needs_evidence_but_neutral_courtesy_does_not(self):
        self.assertFalse(self.accepted(lambda value: value['source_checks'][0].update(evidence=[])))
        context, observed, draft, review = example()
        context['messages'][0]['body'] = 'Hello.'
        draft = Draft.model_validate({'language': 'en', 'body': 'Thank you for your message.',
            'claims': [{'kind': 'clarification', 'text': 'Thank you for your message.', 'source_ids': []}],
            'citation_ids': [], 'waiting_for': 'customer_feedback'})
        review['request_checks'] = [{'unit_index': 0, 'status': 'context', 'reply_quote': ''}]
        review['source_checks'] = [{'claim_index': 0, 'supported': True, 'evidence': []}]
        self.assertTrue(audit_accepts(OutcomeReview.model_validate(review), context, observed, draft))

    def test_41_short_original_units_have_no_added_limit_but_must_all_be_checked(self):
        context, observed, draft, review = example()
        context['messages'][0]['body'] = 'Hello. ' * 41
        draft = Draft.model_validate({'language': 'en', 'body': 'Thank you for your message.',
            'claims': [{'kind': 'clarification', 'text': 'Thank you for your message.', 'source_ids': []}],
            'citation_ids': [], 'waiting_for': 'customer_feedback'})
        review['source_checks'] = [{'claim_index': 0, 'supported': True, 'evidence': []}]
        review['request_checks'] = [{'unit_index': index, 'status': 'context', 'reply_quote': ''}
            for index in range(41)]
        self.assertTrue(audit_accepts(OutcomeReview.model_validate(review), context, observed, draft))
        review['request_checks'].pop()
        self.assertFalse(audit_accepts(OutcomeReview.model_validate(review), context, observed, draft))

    def test_legacy_four_fields_and_coerced_indices_cannot_pass_new_contract(self):
        _, _, _, review = example()
        legacy = {k: v for k, v in review.items() if k not in {'request_checks', 'source_checks'}}
        with self.assertRaises(ValidationError):
            OutcomeReview.model_validate(legacy)
        for invalid in (False, '0', 0.0):
            value = deepcopy(review)
            value['request_checks'][0]['unit_index'] = invalid
            with self.assertRaises(ValidationError):
                OutcomeReview.model_validate(value)


class ReviewAuditProtocolTests(AgentFixture):
    def test_semantic_negative_with_valid_bindings_preserves_specific_model_reason(self):
        for mode in ('omitted', 'claim_false'):
            with self.subTest(mode=mode):
                from agent_review_fixture import engineering_audit
                cid, _ = self.create_mail('Please check my order.', email=f'{mode}@example.test')
                def negative(messages):
                    value = engineering_audit(messages, {'supported': False, 'language_correct': True,
                        'unsupported_claims': ['The requested condition is missing.'],
                        'reason': 'SPECIFIC_SEMANTIC_REQUEST_CONDITION_MISSING'})
                    if mode == 'omitted':
                        for row in value['source_checks']:
                            row['supported'] = True
                    else:
                        for row in value['request_checks']:
                            row['status'] = 'addressed'
                            row['reply_quote'] = json.loads(messages[1]['content'])['draft']['body']
                    return value
                model = ScriptedModel(understanding, terminal(), terminal(), reviews=[negative, {
                    'supported': True, 'language_correct': True, 'unsupported_claims': [],
                    'reason': 'Explicit engineering repaired approval.'}])
                output, job = self.execute(model)
                self.assertEqual(output.get('outcome'), 'reply_and_wait', output)
                feedback = model.requests[3]['messages'][-2]['content']
                self.assertIn('SPECIFIC_SEMANTIC_REQUEST_CONDITION_MISSING', feedback)
                self.assertNotIn('Deterministic audit rejected', feedback)
                self.assertEqual(self.budget_row(job)['model_requests'], 5)
                self.assertEqual(len(self.outbound(cid)), 1)

    def test_binding_rejection_repairs_with_actual_failure_not_positive_model_reason(self):
        from agent_fixture import call
        from agent_review_fixture import engineering_audit
        cid, _ = self.create_mail('My parcel has not arrived.')
        def fact(messages):
            source = json.loads(messages[1]['content'])['context']['trigger_message_id']
            return terminal('You said your parcel has not arrived.', claims=[{
                'kind': 'customer_fact', 'text': 'You said your parcel has not arrived.',
                'source_ids': [source]}])
        def forged(messages):
            value = engineering_audit(messages, {'supported': True, 'language_correct': True,
                'unsupported_claims': [], 'reason': 'WRONG_APPROVAL_ALL_FACTS_SUPPORTED'})
            value['source_checks'][0]['evidence'][0]['quote'] = 'Fabricated exact source excerpt.'
            return value
        model = ScriptedModel(understanding, {'calls': [call('get_case_context', {})]}, fact,
            terminal(), reviews=[forged, {'supported': True, 'language_correct': True,
                'unsupported_claims': [], 'reason': 'Explicit repaired engineering approval.'}])
        output, job = self.execute(model)
        self.assertEqual(output.get('outcome'), 'reply_and_wait', output)
        feedback = model.requests[4]['messages'][-2]['content']
        self.assertIn('claim_0_quote_not_in_source', feedback)
        self.assertNotIn('WRONG_APPROVAL', feedback)
        self.assertEqual(self.budget_row(job)['model_requests'], 6)
        self.assertEqual(len(self.outbound(cid)), 1)
        self.assertEqual(self.service.detail(cid)['messages'][-1]['body'], 'Please share your order number.')

    def test_real_graph_rejects_old_four_field_response_without_outbound(self):
        cid, _ = self.create_mail()
        old = {'supported': True, 'language_correct': True, 'unsupported_claims': [], 'reason': 'Legacy schema'}
        model = ScriptedModel(understanding, terminal(), reviews=[old], audit_fixture=False)
        output, job = self.execute(model)
        self.assertEqual(output.get('error_code'), 'outcome_validation_invalid', output)
        self.assertEqual(self.budget_row(job)['model_requests'], 3)
        self.assertEqual(self.outbound(cid), [])

    def test_real_graph_rejects_missing_unit_and_never_saves_validated_hash(self):
        def missing(messages):
            from agent_review_fixture import engineering_audit
            value = engineering_audit(messages, {'supported': True, 'language_correct': True,
                'unsupported_claims': [], 'reason': 'Fixture omits the last request.'})
            value['request_checks'].pop()
            return value
        cid, _ = self.create_mail('Check delivery. Refund later if still missing, not now.')
        model = ScriptedModel(understanding, terminal(), terminal(), reviews=[missing, missing])
        output, job = self.execute(model)
        self.assertEqual(output.get('error_code'), 'reply_grounding_invalid', output)
        self.assertEqual(self.budget_row(job)['model_requests'], 5)
        self.assertEqual(self.outbound(cid), [])
