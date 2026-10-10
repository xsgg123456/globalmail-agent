import test from 'node:test'
import assert from 'node:assert/strict'
import { createPreviewState } from '../src/preview/state'
import {
  appendToState,
  sendHumanReply,
  updateMockOrder,
  adviceIsCurrent
} from '../src/preview/behavior'
import { conversationRuns, resolvePreviewRun } from '../src/preview/navigation'
import { previewRoutes } from '../src/router/modules/ui-preview'
import { parsePreviewCommand } from '../src/preview/control-contract'
import type { DemoRun } from '../src/preview/types'

const modelInputs = (run: DemoRun) =>
  JSON.stringify(run.steps.filter((step) => step.kind === 'model').map((step) => step.input))
const automaticCount = (messages: { sender: string }[]) =>
  messages.filter((item) => item.sender === 'simulated_agent').length

test('七类业务均有样例，预览导航没有业务中心、实验室或测试控件入口', () => {
  const state = createPreviewState()
  assert.equal(state.conversations.length, 8)
  assert.equal(state.runs.length, 13)
  const initial = state.runs
    .filter((run) => run.round === 1)
    .map((run) => JSON.stringify(run.steps[0]!.output))
  for (const kind of [
    'consultation',
    'troubleshooting',
    'logistics',
    'refund',
    'return',
    'replacement',
    'spare_part'
  ]) {
    assert.ok(
      initial.some((value) => value.includes(`"${kind}"`)),
      kind
    )
  }
  assert.deepEqual(
    previewRoutes.children!.map((route) => route.path),
    ['/workbench', '/agent-runs', '/knowledge', '/system-status']
  )
})

test('四类首轮转人工，只读工具和内部草稿不会产生Agent客户邮件', () => {
  const state = createPreviewState()
  for (const id of ['demo-mail-02', 'demo-mail-04', 'demo-mail-05', 'demo-mail-08']) {
    const mail = state.conversations.find((item) => item.id === id)!
    assert.equal(mail.owner, 'human')
    assert.equal(mail.persistentHuman, true)
    assert.equal(automaticCount(mail.messages), 0)
    assert.ok(mail.advice?.facts.every((fact) => fact.source && fact.observedAt))
    for (const run of conversationRuns(state.runs, id)) {
      assert.equal(run.outputMessageId, undefined)
      assert.ok(run.steps.every((step) => !/submit|cancel|reserve|execute/.test(step.tool ?? '')))
    }
  }
})

test('四类人工回复后的新来信仍内部辅助，复用人工往来且不自动发信', () => {
  const state = createPreviewState()
  for (const id of ['demo-mail-02', 'demo-mail-04', 'demo-mail-05', 'demo-mail-08']) {
    const mail = state.conversations.find((item) => item.id === id)!
    const count = automaticCount(mail.messages)
    assert.ok(sendHumanReply(state, id, 'Human decision: I am checking the existing record.'))
    assert.equal(appendToState(state, id, 'Thank you. Could you check for an update?'), 'assisted')
    const run = conversationRuns(state.runs, id).at(-1)!
    assert.equal(run.mode, 'human-assist')
    assert.ok(modelInputs(run).includes('Human decision:'))
    assert.equal(mail.owner, 'human')
    assert.equal(automaticCount(mail.messages), count)
  }
})

test('退款三次来信和两次人工回复形成三轮，历史没有未来消息或退款事实', () => {
  const state = createPreviewState()
  const mail = state.conversations.find((item) => item.id === 'demo-mail-02')!
  const runs = conversationRuns(state.runs, mail.id)
  assert.deepEqual(
    runs.map((run) => run.round),
    [1, 2, 3]
  )
  assert.equal(mail.messages.length, 5)
  assert.equal(mail.messages.filter((item) => item.sender === 'simulated_human').length, 2)
  assert.ok(!modelInputs(runs[0]!).includes('money has not appeared'))
  assert.ok(!modelInputs(runs[0]!).includes('支付记录已处理'))
  assert.ok(modelInputs(runs[2]!).includes('payment record now shows'))
  assert.ok(modelInputs(runs[2]!).includes('支付记录已处理'))
  const before = modelInputs(runs[2]!)
  mail.messages[0]!.body = 'Later edited input must not rewrite history'
  updateMockOrder(state, mail.orderId, { refund: '后来修改的状态' })
  assert.equal(modelInputs(runs[2]!), before)
})

test('普通排障进入补寄请求后保持人工，随后物流追问不恢复自动发送', () => {
  const state = createPreviewState()
  const mail = state.conversations[0]!
  const runs = conversationRuns(state.runs, mail.id)
  assert.equal(runs[0]!.mode, 'automatic')
  assert.equal(runs[1]!.mode, 'handoff')
  assert.equal(runs[3]!.mode, 'human-assist')
  assert.equal(mail.persistentHuman, true)
  assert.equal(automaticCount(mail.messages), 1)
  assert.ok(!modelInputs(runs[1]!).includes('DEMO-REMOTE-TRACK-01'))
  assert.ok(modelInputs(runs[3]!).includes('DEMO-REMOTE-TRACK-01'))
})

test('显式历史选择跨新轮保留，不抢当前节点，不串其他客户', () => {
  const state = createPreviewState()
  state.viewedRuns['demo-mail-02'] = 'demo-run-02'
  const old = JSON.stringify(state.runs)
  const otherCount = conversationRuns(state.runs, 'demo-mail-04').length
  appendToState(state, 'demo-mail-02', 'Please check again.')
  assert.equal(
    resolvePreviewRun(state.runs, 'demo-mail-02', undefined, state.viewedRuns['demo-mail-02'])
      .round,
    1
  )
  assert.equal(resolvePreviewRun(state.runs, 'demo-mail-02', 'demo-run-01').round, 4)
  assert.equal(JSON.stringify(state.runs.slice(0, -1)), old)
  assert.equal(conversationRuns(state.runs, 'demo-mail-04').length, otherCount)
})

test('测试数据更新不构造执行或发信；下次客户来信才观察新事实', () => {
  const state = createPreviewState()
  const mail = state.conversations.find((item) => item.id === 'demo-mail-02')!
  const runCount = state.runs.length
  const messageCount = mail.messages.length
  assert.equal(adviceIsCurrent(state, mail.id), true)
  assert.ok(updateMockOrder(state, mail.orderId, { refund: '支付记录查询失败', lookupError: true }))
  assert.equal(state.runs.length, runCount)
  assert.equal(mail.messages.length, messageCount)
  assert.equal(adviceIsCurrent(state, mail.id), false)
  assert.equal(appendToState(state, mail.id, 'Can someone check this?'), 'assisted')
  assert.equal(mail.advice!.facts.length, 0)
  assert.ok(mail.advice!.unknowns.some((gap) => gap.includes('查询失败')))
  assert.equal(automaticCount(mail.messages), 0)
})

test('缺订单也交客服，不把补齐数据当成接管前置条件', () => {
  const state = createPreviewState()
  const mail = state.conversations.find((item) => item.id === 'demo-mail-08')!
  mail.orderId = 'MISSING-ORDER'
  assert.equal(appendToState(state, mail.id, 'Please send the missing screws.'), 'assisted')
  assert.equal(mail.owner, 'human')
  assert.equal(mail.advice!.facts.length, 0)
  assert.ok(mail.advice!.unknowns.some((gap) => gap.includes('未找到')))
})

test('危险迹象转人工；结案后只追加来信；空输入无副作用', () => {
  const state = createPreviewState()
  const risk = state.conversations.find((item) => item.id === 'demo-mail-03')!
  assert.equal(risk.owner, 'human')
  assert.equal(automaticCount(risk.messages), 0)
  const count = state.runs.length
  const closed = state.conversations[1]!
  closed.status = '已解决'
  assert.equal(appendToState(state, closed.id, 'Already closed'), 'recorded')
  assert.equal(sendHumanReply(state, closed.id, 'Must not send'), false)
  assert.equal(appendToState(state, risk.id, '  '), 'invalid')
  assert.equal(appendToState(state, 'missing', 'Hello'), 'invalid')
  assert.equal(state.runs.length, count)
})

test('普通问题有据回复，普通人工接管回复后下一封恢复；草稿不串客户', () => {
  const state = createPreviewState()
  const mail = state.conversations.find((item) => item.id === 'demo-mail-06')!
  const count = automaticCount(mail.messages)
  mail.owner = 'human'
  mail.awaitingCustomer = false
  state.drafts[mail.id] = 'My unsent reply'
  state.drafts['demo-mail-02'] = 'Another customer draft'
  assert.equal(appendToState(state, mail.id, 'Thanks'), 'recorded')
  assert.ok(sendHumanReply(state, mail.id, 'Human answer'))
  assert.equal(appendToState(state, mail.id, 'Any other detail?'), 'automatic')
  assert.equal(automaticCount(mail.messages), count + 1)
  assert.equal(state.drafts['demo-mail-02'], 'Another customer draft')
  assert.equal(state.drafts[mail.id], '')
})

test('建议仅在最新未回复来信可采用，人工发送后失效，节点时间按轮次递增', () => {
  const state = createPreviewState()
  const id = 'demo-mail-02'
  assert.ok(adviceIsCurrent(state, id))
  sendHumanReply(state, id, 'Human response')
  assert.equal(adviceIsCurrent(state, id), false)
  appendToState(state, id, 'Thank you, another question.')
  assert.ok(adviceIsCurrent(state, id))
  for (const run of state.runs) {
    assert.ok(run.steps[0]!.time > run.startedAt)
    assert.ok(run.steps.every((step, index) => !index || step.time > run.steps[index - 1]!.time))
  }
})

test('控制契约拒绝未知客户、写工具、额外字段及无效库存，接受合法Mock更新', () => {
  assert.equal(
    parsePreviewCommand({ type: 'incoming', conversationId: 'other-customer', body: 'Hi' }),
    undefined
  )
  assert.equal(parsePreviewCommand({ type: 'execute_refund', orderId: 'DEMO-1002' }), undefined)
  assert.equal(
    parsePreviewCommand({ type: 'business_update', orderId: 'DEMO-1002', patch: { reserved: 1 } }),
    undefined
  )
  assert.equal(
    parsePreviewCommand({
      type: 'business_update',
      orderId: 'DEMO-1002',
      patch: { available: -1 }
    }),
    undefined
  )
  assert.equal(
    parsePreviewCommand({
      type: 'business_update',
      orderId: 'DEMO-1002',
      patch: { available: '8' }
    }),
    undefined
  )
  assert.deepEqual(
    parsePreviewCommand({
      type: 'business_update',
      orderId: 'DEMO-1002',
      patch: { lookupError: true }
    }),
    { type: 'business_update', orderId: 'DEMO-1002', patch: { lookupError: true } }
  )
})
