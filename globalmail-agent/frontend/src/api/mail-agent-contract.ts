export type ConversationMode = 'interactive_simulation' | 'historical_replay'
export type ProcessingOwner = 'agent' | 'human_review' | 'human_wait_customer'
export type SchedulingState =
  | 'idle'
  | 'queued'
  | 'running'
  | 'waiting_customer'
  | 'waiting_business'
  | 'failed'
  | 'stopped'
export type RunStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'handed_off'
  | 'failed'
  | 'budget_exhausted'
  | 'stopped'
  | 'superseded'
  | 'interrupted'
  | 'cancelled'
export interface Conversation {
  id: string
  workspace_id: string
  dataset_id: string
  branch_id: string
  customer_id: string
  purpose: string
  mode: ConversationMode
  sender_key: string
  identity_verified: boolean
  subject: string
  row_version: number
  input_revision: number
  authority_epoch: number
  branch_generation: number
  lifecycle: 'open' | 'resolved' | 'deleting' | 'deleted'
  processing_owner: ProcessingOwner
  auto_run_gate: 'open' | 'manual_retry_required' | 'disabled'
  scheduling_state: SchedulingState
  visible_message_seq: number
  next_seq: number
  created_at: string
  updated_at: string
}
export interface MailMessage {
  id: string
  seq: number
  sender: 'customer' | 'historical_staff' | 'simulated_human'
  subject: string
  body: string
  sent_at: string
}
export interface HumanReview {
  id: string
  status: 'open' | 'completed' | 'closed'
  version: number
  input_revision: number
  reason: string
  draft: string
  note: string
  reply: string
}
export interface AgentRun {
  id: string
  status: RunStatus
  processing_cycle_id: string
  attempt_no: number
  input_revision: number
  error_code: string | null
  outcome: string | null
  started_at: string | null
  finished_at: string | null
  created_at: string
}
export interface ReplayCursor {
  position: number
  total_customer_messages: number
  as_of: string | null
  finished: boolean
}
export interface ConversationDetail {
  conversation: Conversation
  messages: MailMessage[]
  review: HumanReview | null
  runs: AgentRun[]
  issues: { id: string; issue_key: string; status: string; version: number }[]
  facts: {
    id: string
    source_message_id: string
    kind: string
    value: string
    visible_seq: number
  }[]
  replay: ReplayCursor | null
  comparisons: HumanReview[]
  human_history: HumanReview[]
}
export interface ConversationPage {
  items: Conversation[]
  next_cursor: string | null
}
export interface ActionResult {
  conversation_id?: string
  run_id?: string
  version?: number
  review_id?: string
}
export interface ConversationEvent {
  conversation_id: string
  workspace_id: string
  branch_id: string
  mode: string
  seq: number
  kind: string
  payload: Record<string, unknown>
}
