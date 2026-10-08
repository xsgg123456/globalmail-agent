export type BusinessStatus =
  | 'ok'
  | 'empty'
  | 'needs_input'
  | 'denied'
  | 'conflict'
  | 'unavailable'
  | 'unknown'
  | 'error'
export interface BusinessResult<T> {
  status: BusinessStatus
  reason_code: string | null
  data: T | null
  evidence_refs: (string | Record<string, unknown>)[]
  observed_at: string | null
  resource_versions: Record<string, unknown>
  source_kind: string | null
  simulation: boolean
  retryable: boolean
}
export interface BusinessLine {
  line_id: string
  sku: string | null
  quantity: number | null
  paid_minor: number | null
  hardware_revision: string | null
  product_name: string | null
  unknown_fields: string[]
}
export interface BusinessOrder {
  order_id: string
  display_order_number?: string | null
  brand?: string | null
  market?: string | null
  currency: string | null
  paid_minor: number | null
  refunded_minor?: number | null
  pending_refund_minor?: number | null
  source_kind: string | null
  snapshot_at: string | null
  is_realtime: boolean | null
  purchase_at?: string | null
  delivered_at?: string | null
  unknown_fields?: string[]
  lines: BusinessLine[]
}
export interface BusinessRecord {
  [key: string]: unknown
  order_id?: string | null
  order_line_id?: string | null
  line_id?: string | null
  operation_id?: string | null
  execution_id?: string | null
  source_kind?: string | null
  updated_at?: string | null
  status?: string | null
}
export interface BusinessPolicy {
  policy_id: string
  version: string
  publication_status: string
  description: string
  available_at: string | null
  source_kind: string | null
}
export interface BusinessDetailData {
  scenario_id: string | null
  as_of: string | null
  orders: BusinessOrder[]
  selected_line_id: string | null
  shipments: BusinessRecord[]
  operations: BusinessRecord[]
  executions: BusinessRecord[]
  returns: BusinessRecord[]
  missing_fields: string[]
  policy: BusinessPolicy | null
  customer_choices: BusinessChoice[]
  address_confirmation: BusinessAddress | null
}
export interface BusinessChoice {
  action: string | null
  accepted?: boolean | null
  quantity?: number | null
  amount_minor?: number | null
  currency?: string | null
  order_line_id?: string | null
  item_id?: string | null
  part_id?: string | null
  address_version?: number | null
  source_message_id?: string | null
  source_message_seq?: number | null
  source_kind: string | null
  evidence_ref?: string | null
}
export interface BusinessAddress {
  confirmed?: boolean | null
  version?: number | null
  market?: string | null
  source_kind: string | null
  evidence_ref?: string | null
}
export interface AvailabilityData {
  item_id: string
  order_line_id: string
  compatible: boolean | null
  available_quantity: number | null
  on_hand: number | null
  reserved: number | null
  source_kind: string | null
  snapshot_at: string | null
  missing_fields: string[]
}
export type BusinessAction = 'refund' | 'return' | 'replacement' | 'spare_part' | 'logistics'
export interface EligibilityRequest {
  action: BusinessAction
  order_line_id: string | null
  quantity: number
  amount_minor: number | null
  currency: string | null
  item_id: string | null
}
export interface EligibilityData {
  outcome: 'eligible' | 'needs_input' | 'wait' | 'requires_review' | 'ineligible'
  conditions: { code: string; label: string; status: string; fulfilled_by: string[] }[]
  policy_id: string
  version: string
  decision_id: string
  authorized: false
  publication_status: 'unpublished'
  remaining_refund_minor: number | null
  missing_fields: string[]
}
export interface BusinessScenario {
  scenario_id: string
  label: string
  mode: 'simulation' | 'historical_replay'
  brand: string
  business_categories: string[]
}
export interface BusinessContext {
  id: string
  input_revision: number
  row_version: number
}
