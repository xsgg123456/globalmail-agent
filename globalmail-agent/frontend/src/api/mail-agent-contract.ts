export type ConversationMode = 'interactive_simulation' | 'historical_replay'
export type ProcessingOwner = 'agent' | 'human_review' | 'human_wait_customer'
export type RiskDecision = 'keep_active' | 'resolved_by_human' | 'corrected_by_human'
export interface ActiveRisk {
  id: string
  kind: string
  status: 'active' | 'resolved_by_human' | 'corrected_by_human'
  sources: { message_id: string; quote: string }[]
}
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
  persistent_human?: boolean
  human_claimed?: boolean
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
  sender: 'customer' | 'historical_staff' | 'simulated_human' | 'simulated_agent'
  subject: string
  body: string
  sent_at: string
  attachments?: import('./attachment-contract').ImageAttachment[]
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
  staff_draft?: string
  staff_note?: string
}
export interface AgentRun {
  id: string
  conversation_id?: string
  trigger_message_id?: string | null
  execution_mode?: 'autonomous' | 'human_assist'
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
  issues: { id: string; issue_key: string; status: string; version: number;
    order_line_id?: string | null; order_number?: string | null; business_type?: string | null;
    plan_status?: string | null; current_operation_id?: string | null }[]
  waits?: { id: string; issue_id: string; operation_id: string | null; condition_type: string;
    last_seen_business_version: number; owner: string; status: string; run_id: string }[]
  wakes?: { id: string; issue_id: string | null; operation_id: string | null; condition_key: string;
    business_version: number; status: string; observed_run_id: string | null }[]
  business_events?: { id: string; source: string; source_event_id: string; issue_id: string | null;
    operation_id: string | null; condition_type: string | null; business_version: number | null;
    status: string; observed_run_id: string | null }[]
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
  active_risks?: ActiveRisk[]
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
