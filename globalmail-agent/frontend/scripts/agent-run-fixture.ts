import type { AgentRunDetail, RunReference } from '../src/api/agent-run-contract'
import type { AgentRun, ConversationDetail } from '../src/api/mail-agent-contract'
import type { AgentRunApi } from '../src/api/agent-run-api'
import { detailFixture } from './mail-workbench-fixture'

export const runFixture = (id = 'run-1'): AgentRun => ({
  id,
  status: 'running',
  processing_cycle_id: 'cycle-1',
  attempt_no: 1,
  input_revision: 1,
  error_code: null,
  outcome: null,
  started_at: '2026-10-08T00:00:00Z',
  finished_at: null,
  created_at: '2026-10-08T00:00:00Z'
})
export function runContext(id = 'conversation-1', runs = [runFixture()]): ConversationDetail {
  const result = detailFixture(id)
  result.conversation.processing_owner = 'agent'
  result.conversation.auto_run_gate = 'open'
  result.runs = runs
  return result
}
export const runDetail = (id = 'run-1'): AgentRunDetail => ({
  run: runFixture(id),
  job: null,
  understanding: null,
  tools: [],
  references: [],
  artifacts: [],
  usage: {
    model_requests: 0,
    tool_calls: 0,
    input_tokens: 0,
    output_tokens: 0,
    unknown_requests: 0,
    reserved_tokens: 0,
    active_ms: 0,
    cost: null,
    limits: { model_requests: 6, tool_calls: 12, tokens: 80000, active_ms: 120000 }
  },
  waits: []
})
export const runReference = (id = 'reference-1', eligible = true): RunReference => ({
  eligible,
  reason: eligible ? 'ok' : 'withdrawn',
  reference: {
    evidence_id: id,
    release_id: 'release-1',
    release_epoch: 1,
    document_id: 'doc-1',
    version_id: 'version-1',
    version_number: 1,
    build_id: 'build-1',
    embedding_profile_id: 'profile-1',
    chunk_id: 'chunk-1',
    parent_id: 'parent-1',
    title: '排障',
    text: eligible ? '步骤' : '',
    score: 0.9,
    page: [1],
    section: '配对',
    figure: [],
    source_sha256: 'source',
    content_hash: 'content',
    source_kind: 'simulation',
    completeness: 'full',
    available_at: '2026-10-08T00:00:00Z',
    observed_at: '2026-10-08T00:00:00Z',
    applicability_revision: '1',
    applicability: [],
    allowed_scope: {},
    allowed_modes: ['simulation']
  }
})
export const runApiFixture = (): AgentRunApi => ({
  detail: async (id) => runDetail(id),
  reference: async (_runId, referenceId) => runReference(referenceId)
})
export const settle = () => new Promise<void>((resolve) => setImmediate(resolve))
