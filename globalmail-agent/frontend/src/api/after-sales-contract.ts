import type { BusinessContext, BusinessRecord, BusinessResult } from './business-contract'
import type { ConversationMode } from './mail-agent-contract'

export type SimulationEventName =
  | 'create_execution' | 'processing' | 'succeeded' | 'failed' | 'unknown'
  | 'reconciled_not_executed' | 'label_created' | 'shipped' | 'delivered'
  | 'return_in_transit' | 'received' | 'inspected' | 'inventory_changed'
  | 'cancellation_acknowledged'
  | 'create_corrective_execution'

export interface OperationRecord extends BusinessRecord {
  operation_id: string
  kind: string
  version: number
  quantity: number
  status: string
  cancelable: boolean
  allowed_events: SimulationEventName[]
}
export interface OperationLedger {
  branch_id: string | null
  branch_generation: number | null
  conversation_version: number
  operations: OperationRecord[]
  executions: BusinessRecord[]
  shipments: BusinessRecord[]
  returns: BusinessRecord[]
}
export type LedgerResult = BusinessResult<OperationLedger>
export type AfterSalesContext = BusinessContext & { mode: ConversationMode }
export interface SimulationInput {
  event: SimulationEventName
  execution_id?: string
  receipt_ref?: string
  tracking_number?: string
  carrier?: string
  reason?: string
  quantity?: number
  confirmed_not_executed?: boolean
  on_hand?: number
  return_address?: string
  packing_instructions?: string
  postage_responsibility?: 'customer' | 'merchant'
  prepaid_label_ref?: string
  staff_id?: string
  correction_of_execution_id?: string
}
export interface SimulationResult {
  conversation_id: string
  operation_id: string
  [key: string]: unknown
}
