import type {
  BusinessResult,
  BusinessDetailData,
  BusinessContext,
  EligibilityData,
  AvailabilityData
} from '../src/api/business-contract'
import type { BusinessApi } from '../src/api/business-api'

export function businessResult<T>(
  data: T,
  status: BusinessResult<T>['status'] = 'ok'
): BusinessResult<T> {
  return {
    status,
    reason_code: null,
    data,
    evidence_refs: [],
    observed_at: '2026-10-08T10:00:00+08:00',
    resource_versions: {},
    source_kind: 'synthetic',
    simulation: true,
    retryable: false
  }
}
export function businessDetail(multiple = false): BusinessResult<BusinessDetailData> {
  const lines = [
    {
      line_id: 'line-1',
      sku: 'lamp-us',
      quantity: 1,
      paid_minor: 5499,
      hardware_revision: null,
      product_name: '灯具',
      unknown_fields: ['hardware_revision']
    }
  ]
  if (multiple) lines.push({ ...lines[0], line_id: 'line-2', sku: 'lamp-eu' })
  return businessResult(
    {
      scenario_id: 'SCN-001',
      as_of: null,
      orders: [
        {
          order_id: 'order-1',
          display_order_number: 'ORDER-demo',
          currency: 'USD',
          paid_minor: 5499,
          source_kind: 'synthetic',
          snapshot_at: null,
          is_realtime: false,
          lines
        }
      ],
      selected_line_id: multiple ? null : 'line-1',
      shipments: [],
      operations: [],
      executions: [],
      returns: [],
      missing_fields: [],
      policy: null,
      customer_choices: [],
      address_confirmation: null
    },
    multiple ? 'needs_input' : 'ok'
  )
}
export const contextFixture = (id = 'c-1'): BusinessContext => ({
  id,
  input_revision: 1,
  row_version: 2
})
export function businessApiFixture(): BusinessApi {
  return {
    detail: async () => businessDetail(),
    availability: async (_id, lineId, itemId) =>
      businessResult<AvailabilityData>({
        order_line_id: lineId,
        item_id: itemId,
        compatible: true,
        available_quantity: 0,
        on_hand: 0,
        reserved: 0,
        source_kind: 'synthetic',
        snapshot_at: null,
        missing_fields: []
      }),
    eligibility: async () =>
      businessResult<EligibilityData>({
        outcome: 'needs_input',
        conditions: [],
        policy_id: 'policy-1',
        version: '1.0.1',
        decision_id: 'hash-1',
        authorized: false,
        publication_status: 'unpublished',
        remaining_refund_minor: null,
        missing_fields: ['customer_choice']
      }),
    scenarios: async () => ({ items: [] }),
    createScenario: async () => ({ conversation_id: 'created-1' })
  }
}
export async function settle() {
  await new Promise<void>((resolve) => setImmediate(resolve))
}
