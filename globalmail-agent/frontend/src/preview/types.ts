import type { MailMessage } from '@/api/mail-agent-contract'

export type DemoStatus = '等待客户' | '待人工接管' | '人工接管中' | '已解决'
export type DemoBusiness =
  | 'consultation'
  | 'troubleshooting'
  | 'logistics'
  | 'refund'
  | 'return'
  | 'replacement'
  | 'spare_part'
  | 'safety'
export interface DemoFact {
  label: string
  value: string
  source: string
  observedAt: string
}
export interface DemoAdvice {
  runId: string
  triggerMessageId: string
  reason: string
  facts: DemoFact[]
  unknowns: string[]
  recommendation: string
  draft: string
}
export interface DemoConversation {
  id: string
  customer: string
  email: string
  subject: string
  brand: string
  channel: string
  business: DemoBusiness
  status: DemoStatus
  owner: 'agent' | 'human'
  persistentHuman: boolean
  awaitingCustomer: boolean
  orderId: string
  runId: string
  advice?: DemoAdvice
  adviceStale?: boolean
  messages: MailMessage[]
}
export interface DemoStep {
  id: string
  title: string
  kind: 'model' | 'tool' | 'check' | 'commit'
  time: string
  duration: string
  summary: string
  input: unknown
  output: unknown
  thinking: 'off' | 'recorded' | 'not-applicable'
  reasoning?: string
  tool?: string
}
export interface DemoRun {
  id: string
  conversationId: string
  round: number
  title: string
  mode: 'automatic' | 'handoff' | 'human-assist'
  triggerMessageId: string
  outputMessageId?: string
  trigger: string
  status: DemoStatus
  startedAt: string
  duration: string
  tokens: number
  steps: DemoStep[]
}
export interface DemoOrder {
  id: string
  brand: string
  sku: string
  product: string
  paid: string
  channel: string
  shipment: string
  shipmentState: 'in_transit' | 'delivered' | 'unknown'
  refund: string
  refundAmount: string
  returnStatus: string
  exchange: string
  part: string
  available: number
  lookupError: boolean
  lookupNotFound: boolean
}
export interface DemoState {
  conversations: DemoConversation[]
  orders: DemoOrder[]
  runs: DemoRun[]
  drafts: Record<string, string>
  readPositions: Record<string, number>
  viewedRuns: Record<string, string>
  selectedMail: string
}
