import { mailRequest } from './mail-agent-request'
import type { LedgerResult, SimulationResult } from './after-sales-contract'

export const afterSalesApi = {
  listing: (conversationId: string) => mailRequest<LedgerResult>({
    url: `/conversations/${encodeURIComponent(conversationId)}/operations`, method: 'GET'
  }),
  event: (branchId: string, payload: Record<string, unknown>, key: string) =>
    mailRequest<SimulationResult>({
      url: `/simulation/branches/${encodeURIComponent(branchId)}/events`, method: 'POST',
      data: payload, headers: { 'Idempotency-Key': key }
    }),
  link: (branchId: string, payload: Record<string, unknown>, key: string) =>
    mailRequest<SimulationResult>({
      url: `/simulation/branches/${encodeURIComponent(branchId)}/execution-links`, method: 'POST',
      data: payload, headers: { 'Idempotency-Key': key }
    })
}
export type AfterSalesApi = typeof afterSalesApi
