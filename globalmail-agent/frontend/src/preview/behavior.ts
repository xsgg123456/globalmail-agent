import type { DemoState, DemoOrder } from './types'
import { createIncomingRun } from './run-builder'
import { detectBusiness, financialKinds } from './advice'

export function nextDemoTime(messages: { sent_at: string }[], requested?: string) {
  const latest = Math.max(
    ...messages.map((item) => Date.parse(item.sent_at)),
    Date.parse('2026-10-09T02:00:00Z')
  )
  return new Date(
    Math.max(requested ? Date.parse(requested) : latest + 60_000, latest + 1000)
  ).toISOString()
}
export function appendToState(state: DemoState, conversationId: string, body: string, at?: string) {
  const mail = state.conversations.find((item) => item.id === conversationId)
  if (!mail || !body.trim() || body.length > 20000) return 'invalid'
  const trigger = {
    id: `demo-incoming-${mail.id}-${mail.messages.length + 1}`,
    seq: mail.messages.length + 1,
    sender: 'customer' as const,
    subject: `Re: ${mail.subject}`,
    body,
    sent_at: nextDemoTime(mail.messages, at)
  }
  mail.messages.push(trigger)
  if (mail.status === '已解决') return 'recorded'
  mail.business = detectBusiness(body, mail.business)
  if (financialKinds.includes(mail.business)) mail.persistentHuman = true
  if (mail.owner === 'human' && !mail.persistentHuman && !mail.awaitingCustomer) return 'recorded'
  const round =
    Math.max(
      ...state.runs.filter((item) => item.conversationId === mail.id).map((item) => item.round),
      0
    ) + 1
  const run = createIncomingRun(
    mail,
    state.orders.find((item) => item.id === mail.orderId),
    trigger,
    round
  )
  state.runs.push(run)
  return run.mode === 'automatic' ? 'automatic' : 'assisted'
}
export function sendHumanReply(
  state: DemoState,
  conversationId: string,
  body: string,
  at?: string
) {
  const mail = state.conversations.find((item) => item.id === conversationId)
  if (!mail || mail.status === '已解决' || !body.trim() || body.length > 20000) return false
  mail.messages.push({
    id: `demo-human-${mail.id}-${mail.messages.length + 1}`,
    seq: mail.messages.length + 1,
    sender: 'simulated_human',
    subject: `Re: ${mail.subject}`,
    body,
    sent_at: nextDemoTime(mail.messages, at)
  })
  state.drafts[mail.id] = ''
  mail.owner = 'human'
  mail.awaitingCustomer = true
  mail.status = '等待客户'
  return true
}
export type MockOrderPatch = Partial<
  Pick<
    DemoOrder,
    | 'refund'
    | 'refundAmount'
    | 'shipment'
    | 'shipmentState'
    | 'returnStatus'
    | 'exchange'
    | 'part'
    | 'available'
    | 'lookupError'
    | 'lookupNotFound'
  >
>
export function updateMockOrder(state: DemoState, orderId: string, patch: MockOrderPatch) {
  const order = state.orders.find((item) => item.id === orderId)
  if (!order) return false
  Object.assign(order, patch)
  if ('shipment' in patch && !('shipmentState' in patch)) order.shipmentState = 'unknown'
  for (const mail of state.conversations) {
    if (mail.orderId === orderId && mail.advice) mail.adviceStale = true
  }
  // 只改测试查询数据；不构造执行回执，不唤醒Agent，不向客户发信。
  return true
}
export function adviceIsCurrent(state: DemoState, conversationId: string) {
  const mail = state.conversations.find((item) => item.id === conversationId)
  if (!mail?.advice || mail.adviceStale || mail.status === '已解决') return false
  const latest = mail.messages.at(-1)
  return latest?.sender === 'customer' && latest.id === mail.advice.triggerMessageId
}

export function takeoverConversation(state: DemoState, conversationId: string) {
  const mail = state.conversations.find((item) => item.id === conversationId)
  if (!mail || mail.status === '已解决') return false
  mail.owner = 'human'
  mail.awaitingCustomer = false
  mail.status = '人工接管中'
  return true
}
