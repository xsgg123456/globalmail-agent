import test from 'node:test'
import assert from 'node:assert/strict'
import { createPreviewState } from '../src/preview/state'
import {
  appendToState,
  updateMockOrder,
  takeoverConversation,
  sendHumanReply
} from '../src/preview/behavior'
import { asRecord } from '../src/preview/presentation'
import { parsePreviewCommand } from '../src/preview/control-contract'

test('缺订单通过交付脚本契约可达，未找到与查询失败分开且不编造事实', () => {
  const state = createPreviewState()
  const command = parsePreviewCommand({
    type: 'business_update',
    orderId: 'DEMO-1004',
    patch: { lookupNotFound: true }
  })
  assert.ok(command?.type === 'business_update')
  updateMockOrder(state, command.orderId, command.patch)
  assert.equal(appendToState(state, 'demo-mail-04', 'I need help with the return.'), 'assisted')
  const run = state.runs.at(-1)!
  assert.equal(
    asRecord(run.steps.find((step) => step.tool === 'query_order')?.output).status,
    'not_found'
  )
  assert.deepEqual(state.conversations[3]!.advice?.facts, [])
  assert.ok(state.conversations[3]!.advice?.unknowns[0]?.includes('未找到'))
})

test('脚本可达的中英文未知、失败或旧扫描交人工，有据结构状态才自动回复', () => {
  for (const shipment of [
    '未知；物流接口未返回可核实的状态',
    '物流查询失败',
    '承运商待核实',
    'Delivery status unknown; last stored scan was delivered',
    'query_failed: previous cached status in transit',
    'Not delivered; current carrier status unknown'
  ]) {
    const state = createPreviewState()
    const mail = state.conversations.find((item) => item.id === 'demo-mail-07')!
    const before = mail.messages.filter((item) => item.sender === 'simulated_agent').length
    const command = parsePreviewCommand({
      type: 'business_update',
      orderId: 'DEMO-1007',
      patch: { shipment }
    })
    assert.ok(command?.type === 'business_update')
    updateMockOrder(state, command.orderId, command.patch)
    assert.equal(appendToState(state, mail.id, 'Could you check the shipping status?'), 'assisted')
    assert.equal(mail.owner, 'human')
    assert.equal(state.runs.at(-1)?.mode, 'handoff')
    assert.equal(mail.messages.filter((item) => item.sender === 'simulated_agent').length, before)
    assert.ok(mail.advice?.unknowns.some((item) => item.includes('物流')))
    assert.ok(mail.advice?.draft.includes('verification'))
  }
  const state = createPreviewState()
  updateMockOrder(state, 'DEMO-1007', {
    shipment: '运输中；最后扫描：目的地分拨中心',
    shipmentState: 'in_transit'
  })
  assert.equal(
    appendToState(state, 'demo-mail-07', 'Could you check the shipping status?'),
    'automatic'
  )
  assert.equal(state.conversations[6]!.messages.at(-1)?.sender, 'simulated_agent')
})

test('人工结案后接管和回复均拒绝，新来信只登记，不能隐式重开', () => {
  const state = createPreviewState()
  const mail = state.conversations[1]!
  mail.status = '已解决'
  const before = state.runs.length
  assert.equal(takeoverConversation(state, mail.id), false)
  assert.equal(mail.status, '已解决')
  assert.equal(sendHumanReply(state, mail.id, 'Reply after close'), false)
  assert.equal(appendToState(state, mail.id, 'I still need a refund.'), 'recorded')
  assert.equal(state.runs.length, before)
  assert.equal(mail.status, '已解决')
  assert.equal(
    parsePreviewCommand({
      type: 'business_update',
      orderId: 'DEMO-1007',
      patch: { shipmentState: 'cached' }
    }),
    undefined
  )
})

test('未查到退货/换货记录不凭空说已有申请；安全陈述使用本轮原文', () => {
  const state = createPreviewState()
  updateMockOrder(state, 'DEMO-1004', { returnStatus: '未查到退货记录' })
  updateMockOrder(state, 'DEMO-1005', { exchange: '当前Mock查询未找到换货记录' })
  appendToState(state, 'demo-mail-04', 'I want to return this item.')
  appendToState(state, 'demo-mail-05', 'I want an exchange.')
  assert.ok(!state.conversations[3]!.advice?.draft.includes('contain return information'))
  assert.ok(!state.conversations[4]!.advice?.draft.includes('contain replacement information'))
  state.conversations[2]!.awaitingCustomer = true
  appendToState(state, 'demo-mail-03', 'The light is still smoking.')
  assert.equal(state.conversations[2]!.advice?.facts[0]?.value, 'The light is still smoking.')
  assert.ok(!state.conversations[2]!.advice?.draft.includes('for disconnecting'))
  assert.equal(asRecord(state.runs.at(-1)?.steps[0]?.output).intent, 'safety')
})
