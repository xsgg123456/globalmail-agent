import type { ConversationDetail } from '../src/api/mail-agent-contract'

export function detailFixture(id = 'c-1'): ConversationDetail {
  return {
    conversation: {
      id,
      workspace_id: 'w',
      dataset_id: 'd',
      branch_id: 'b',
      customer_id: 'customer',
      purpose: 'simulation',
      mode: 'interactive_simulation',
      sender_key: 'a@example.test',
      identity_verified: true,
      subject: 'hello',
      row_version: 2,
      input_revision: 1,
      authority_epoch: 0,
      branch_generation: 1,
      lifecycle: 'open',
      processing_owner: 'human_review',
      auto_run_gate: 'disabled',
      scheduling_state: 'idle',
      visible_message_seq: 1,
      next_seq: 1,
      created_at: '2026-10-08T00:00:00Z',
      updated_at: '2026-10-08T00:00:00Z'
    },
    messages: [
      {
        id: 'm-1',
        seq: 1,
        sender: 'customer',
        subject: 'hello',
        body: 'first customer mail',
        sent_at: '2026-10-08T00:00:00Z'
      }
    ],
    review: {
      id: 'h-1',
      status: 'open',
      version: 1,
      input_revision: 1,
      reason: 'manual',
      draft: 'saved reply',
      note: 'saved note',
      reply: ''
    },
    runs: [],
    issues: [],
    facts: [],
    replay: null,
    comparisons: [],
    human_history: []
  }
}
