import { mailRequest } from './mail-agent-request'
import type { ActionResult } from './mail-agent-contract'
import type {
  BusinessDetailData,
  BusinessResult,
  AvailabilityData,
  EligibilityData,
  EligibilityRequest,
  BusinessScenario
} from './business-contract'

const conversationPath = (id: string) => `/conversations/${encodeURIComponent(id)}`
export const businessApi = {
  detail: (id: string, orderNumber = '', lineId = '') =>
    mailRequest<BusinessResult<BusinessDetailData>>({
      url: `${conversationPath(id)}/business`,
      method: 'GET',
      params: { order_number: orderNumber || undefined, order_line_id: lineId || undefined }
    }),
  availability: (id: string, lineId: string, itemId: string) =>
    mailRequest<BusinessResult<AvailabilityData>>({
      url: `${conversationPath(id)}/availability`,
      method: 'GET',
      params: { order_line_id: lineId, item_id: itemId }
    }),
  eligibility: (id: string, input: EligibilityRequest) =>
    mailRequest<BusinessResult<EligibilityData>>({
      url: `${conversationPath(id)}/eligibility`,
      method: 'POST',
      data: input
    }),
  scenarios: () =>
    mailRequest<{ items: BusinessScenario[] }>({
      url: '/business/scenarios',
      method: 'GET'
    }),
  createScenario: (scenarioId: string, payload: Record<string, unknown>, key: string) =>
    mailRequest<ActionResult>({
      url: `/business/scenarios/${encodeURIComponent(scenarioId)}/conversations`,
      method: 'POST',
      data: payload,
      headers: { 'Idempotency-Key': key }
    })
}
export type BusinessApi = typeof businessApi
