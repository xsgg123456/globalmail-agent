import type { AgentRun } from './mail-agent-contract'
import type { BusinessResult } from './business-contract'
import type { EvidenceReference } from './knowledge-index-contract'

export interface UnderstandingSource {
  message_id: string
  quote: string
}
export interface UnderstandingIntent {
  business_type:
    | 'product_inquiry'
    | 'troubleshooting'
    | 'shipment'
    | 'refund'
    | 'return'
    | 'replacement'
    | 'parts'
    | 'other'
  order_number: string | null
  target_item: string | null
  condition: string | null
  requested_solution: string | null
  consent: 'none' | 'conditional' | 'explicit' | 'declined'
  sources: UnderstandingSource[]
}
export interface UnderstandingResult {
  language: string
  intents: UnderstandingIntent[]
  order_candidates: { value: string; sources: UnderstandingSource[] }[]
  facts: {
    key: string
    value: string
    kind: 'customer_report' | 'historical_claim' | 'human_decision' | 'model_inference'
    sources: UnderstandingSource[]
  }[]
  risk_flags: { kind: string; sources: UnderstandingSource[] }[]
  missing_information: string[]
  initial_understanding?: UnderstandingResult
  revisions?: UnderstandingRevision[]
}
export interface UnderstandingRevision {
  revision: number
  case_revision: number
  change_reason: string
  source_ids: string[]
  sources: UnderstandingSource[]
  created_at: string
  understanding: UnderstandingResult
}
export interface AgentToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
  status: string
  reason_code: string | null
  created_at: string
  result: BusinessResult<Record<string, unknown>> | null
}
export interface RunReference {
  reference: EvidenceReference
  eligible: boolean
  reason: string
}
export type RunOutcome =
  | 'reply_and_wait'
  | 'historical_comparison'
  | 'handoff'
  | 'wait_business'
  | 'no_material_update'
  | 'human_advice'
export interface ReplyArtifact {
  id: string
  outcome: RunOutcome
  language: string
  body: string
  citation_ids: string[]
  created_at: string
}
export interface RunUsage {
  model_requests: number
  tool_calls: number
  input_tokens: number
  output_tokens: number
  unknown_requests: number
  reserved_tokens: number
  active_ms: number
  limits: { model_requests: number; tool_calls: number; tokens: number; active_ms: number }
  cost: number | null
}
export interface RunWait {
  condition_type: string
  status: string
  last_seen_business_version: number | null
  operation_id?: string | null
}
export interface AgentRunDetail {
  run: AgentRun
  job: Record<string, unknown> | null
  understanding: UnderstandingResult | null
  tools: AgentToolCall[]
  references: RunReference[]
  artifacts: ReplyArtifact[]
  usage: RunUsage
  waits: RunWait[]
  model_calls?: ModelCall[]
  advice?: AgentAdvice[]
  context?: Record<string, unknown> | null
}

export interface ModelCall {
  id: string
  request_key: string
  stage: string
  model: string
  status: string
  request: Record<string, unknown> | null
  response: Record<string, unknown> | null
  reasoning_state: 'returned' | 'disabled' | 'not_returned' | 'failed' | 'not_recorded'
  created_at: string
  finished_at: string | null
  error_code: string | null
  input_tokens: number | null
  output_tokens: number | null
}
export interface AgentAdvice {
  summary: string
  gaps: string[]
  recommendations: string[]
  draft: string
  facts: UnderstandingResult['facts']
  intents: UnderstandingIntent[]
  run_id: string
  input_revision: number
  queried_at: string
}
export interface ConversationAdvice {
  advice: AgentAdvice | null
  run_id: string | null
  stale: boolean
  input_revision: number
  observations: AgentToolCall[]
}
