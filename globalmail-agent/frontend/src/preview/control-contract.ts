import type { MockOrderPatch } from './behavior'

export type PreviewCommand =
  | { type: 'reset' }
  | { type: 'incoming'; conversationId: string; body: string }
  | { type: 'business_update'; orderId: string; patch: MockOrderPatch }
export interface PreviewControlEvent {
  sequence: number
  id: string
  command: PreviewCommand
}
function record(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {}
}
const stringFields = ['refund', 'refundAmount', 'shipment', 'returnStatus', 'exchange', 'part']
export function parsePreviewCommand(value: unknown): PreviewCommand | undefined {
  const input = record(value)
  if (input.type === 'reset') return { type: 'reset' }
  if (
    input.type === 'incoming' &&
    /^demo-mail-0[1-8]$/.test(String(input.conversationId)) &&
    typeof input.body === 'string' &&
    input.body.trim() &&
    input.body.length <= 20000
  ) {
    return { type: 'incoming', conversationId: String(input.conversationId), body: input.body }
  }
  if (input.type !== 'business_update' || !/^DEMO-100[1-8]$/.test(String(input.orderId))) return
  const candidate = record(input.patch)
  const keys = Object.keys(candidate)
  if (
    !keys.length ||
    keys.some(
      (key) =>
        ![...stringFields, 'shipmentState', 'available', 'lookupError', 'lookupNotFound'].includes(
          key
        )
    )
  )
    return
  for (const [key, item] of Object.entries(candidate)) {
    if (
      key === 'shipmentState' &&
      (typeof item !== 'string' || !['in_transit', 'delivered', 'unknown'].includes(item))
    )
      return
    if (
      stringFields.includes(key) &&
      (typeof item !== 'string' || !item.trim() || item.length > 1000)
    )
      return
    if (
      key === 'available' &&
      (typeof item !== 'number' || !Number.isInteger(item) || item < 0 || item > 100000)
    )
      return
    if (['lookupError', 'lookupNotFound'].includes(key) && typeof item !== 'boolean') return
  }
  return {
    type: 'business_update',
    orderId: String(input.orderId),
    patch: candidate as MockOrderPatch
  }
}
