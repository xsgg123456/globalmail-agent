import { test } from 'node:test'
import assert from 'node:assert/strict'
import { ref } from 'vue'
import { useAfterSales } from '../src/composables/useAfterSales'
import { emptySimulationForm, eventLabels, simulationInput } from '../src/components/mail-agent/after-sales-inputs'
import type { AfterSalesApi } from '../src/api/after-sales-api'
import type { AfterSalesContext, LedgerResult, OperationRecord, SimulationResult } from '../src/api/after-sales-contract'
import { businessResult, settle } from './business-fixture'
import { MailApiError } from '../src/api/mail-agent-request'
import type { ConversationMode } from '../src/api/mail-agent-contract'

const context = (id = 'c1', mode: ConversationMode = 'interactive_simulation'): AfterSalesContext => ({ id, mode, row_version: 2, input_revision: 1 })
const operation = (id = 'op1', version = 1): OperationRecord => ({ operation_id: id, kind: 'refund', version,
  quantity: 1, status: 'accepted', cancelable: true, allowed_events: ['create_execution'] })
const ledger = (id = 'op1', version = 1, conversationVersion = 2): LedgerResult => businessResult({
  branch_id: 'b1', branch_generation: 1, conversation_version: conversationVersion,
  operations: [operation(id, version)], executions: [], shipments: [], returns: [] })
const apiFixture = (): AfterSalesApi => ({ listing: async () => ledger(),
  event: async (_branch, input) => ({ conversation_id: String(input.conversation_id), operation_id: String(input.operation_id) }),
  link: async (_branch, input) => ({ conversation_id: String(input.conversation_id), operation_id: String(input.operation_id) }) })

test('模拟控制输入严格校验允许事件、整数和实际回执；切换事件不带旧字段', () => {
  const form = emptySimulationForm()
  form.event = 'succeeded'
  assert.equal(simulationInput(form, ['succeeded']).input, null)
  form.receiptRef = ' receipt-1 '
  form.reason = '旧失败说明'
  assert.deepEqual(simulationInput(form, ['succeeded']).input, { event: 'succeeded', receipt_ref: 'receipt-1' })
  form.event = 'inventory_changed'
  for (const invalid of ['-1', '1.2', '1e3', '9007199254740992']) {
    form.onHand = invalid
    assert.equal(simulationInput(form, ['inventory_changed']).input, null)
  }
  form.onHand = '0'
  assert.deepEqual(simulationInput(form, ['inventory_changed']).input, { event: 'inventory_changed', on_hand: 0 })
  assert.equal(simulationInput(form, []).input, null)
  form.event = 'shipped'
  form.trackingNumber = 'SIM-TRACK'
  form.carrier = 'Simulation Carrier'
  form.receiptRef = ''
  assert.equal(simulationInput(form, ['shipped']).input, null)
  form.receiptRef = 'carrier-accepted'
  assert.equal(simulationInput(form, ['shipped']).input?.receipt_ref, 'carrier-accepted')
  form.event = 'delivered'
  form.receiptRef = ''
  assert.equal(simulationInput(form, ['delivered']).input, null)
  form.receiptRef = 'carrier-delivered'
  assert.deepEqual(simulationInput(form, ['delivered']).input, { event: 'delivered', receipt_ref: 'carrier-delivered' })
  form.event = 'inspected'
  form.quantity = '1'
  assert.equal(eventLabels.inspected, '记录仓库质检结果')
  for (const reason of ['passed', 'failed', 'disputed']) {
    form.reason = reason
    assert.equal(simulationInput(form, ['inspected']).input?.reason, reason)
  }
})

test('未知对账必须明确未执行；退货授权和商家预付不能缺真实模拟资料', () => {
  const form = emptySimulationForm()
  form.event = 'reconciled_not_executed'
  form.reason = '核对原回执，无支付'
  assert.equal(simulationInput(form, [form.event]).input, null)
  form.confirmedNotExecuted = true
  assert.equal(simulationInput(form, [form.event]).input, null)
  form.receiptRef = 'original-attempt-not-executed'
  assert.equal(simulationInput(form, [form.event]).input?.confirmed_not_executed, true)
  form.event = 'label_created'
  form.receiptRef = ''
  form.receiptRef = 'return-1'
  assert.equal(simulationInput(form, [form.event], true).input, null)
  form.returnAddress = '仅测试的模拟退货地址'
  form.packingInstructions = '包装整齐'
  assert.equal(simulationInput(form, [form.event], true).input?.return_address, form.returnAddress)
  form.postageResponsibility = 'merchant'
  assert.equal(simulationInput(form, [form.event], true).input, null)
  form.prepaidLabelRef = 'label-1'
  form.carrier = '模拟承运商'
  form.trackingNumber = 'tracking-1'
  assert.equal(simulationInput(form, [form.event], true).input?.prepaid_label_ref, 'label-1')
})

test('读请求晚到不覆盖新会话或新刷新；读取失败可恢复，空记录保持空', async () => {
  const api = apiFixture(), ctx = ref(context('slow'))
  let release!: (value: LedgerResult) => void
  api.listing = async id => id === 'slow' ? new Promise(resolve => { release = resolve }) : ledger('new')
  const model = useAfterSales(ctx, api)
  ctx.value = context('new')
  await settle()
  release(ledger('old'))
  await settle()
  assert.equal(model.data.value?.operations[0].operation_id, 'new')
  api.listing = async () => { throw new MailApiError(503, 'unavailable', 'r1') }
  await model.refresh()
  assert.match(model.error.value, /不可用/)
  api.listing = async () => businessResult({ ...ledger().data!, operations: [] })
  await model.refresh()
  assert.equal(model.error.value, '')
  assert.deepEqual(model.data.value?.operations, [])
  model.dispose()
})

test('写入结果未知重试同键及原版本；刷新不能偷换命令；参数变化才另建命令', async () => {
  const api = apiFixture(), ctx = ref(context()), calls: { key: string; payload: Record<string, unknown> }[] = []
  api.event = async (_branch, payload, key) => {
    calls.push({ key, payload: structuredClone(payload) })
    if (calls.length === 1) throw new MailApiError(0, 'timeout', '')
    return { conversation_id: 'c1', operation_id: 'op1' }
  }
  const model = useAfterSales(ctx, api)
  await settle()
  const input = { event: 'create_execution' as const }
  assert.equal(await model.submit('event', model.data.value!.operations[0], input), false)
  api.listing = async () => ledger('op1', 2, 3)
  ctx.value = { ...ctx.value, row_version: 3 }
  await settle()
  model.data.value!.operations[0].allowed_events = ['succeeded']
  assert.equal(model.canRetry.value, true)
  assert.equal(await model.submit('event', model.data.value!.operations[0], input), false)
  assert.equal(calls.length, 1)
  assert.equal(await model.retry(), true)
  assert.equal(calls[0].key, calls[1].key)
  assert.deepEqual(calls[0].payload, calls[1].payload)
  assert.equal(calls[1].payload.expected_operation_version, 1)
  await model.submit('event', model.data.value!.operations[0], { event: 'unknown', reason: '核对中' })
  assert.notEqual(calls[1].key, calls[2].key)
  model.dispose()
})

test('明确版本拒绝后按新版本提交；跨会话和历史模式清除原请求核对', async () => {
  const api = apiFixture(), ctx = ref(context()), versions: unknown[] = []
  api.event = async (_branch, payload) => {
    versions.push(payload.expected_version)
    if (versions.length === 1) throw new MailApiError(409, 'stale', '')
    if (versions.length === 3) throw new MailApiError(0, 'network', '')
    return { conversation_id: 'c1', operation_id: 'op1' }
  }
  const model = useAfterSales(ctx, api)
  await settle()
  const input = { event: 'create_execution' as const }
  assert.equal(await model.submit('event', operation(), input), false)
  assert.equal(model.canRetry.value, false)
  api.listing = async () => ledger('op1', 2, 3)
  await model.refresh()
  assert.equal(await model.submit('event', model.data.value!.operations[0], input), true)
  assert.deepEqual(versions, [2, 3])
  assert.equal(await model.submit('event', model.data.value!.operations[0], input), false)
  assert.equal(model.canRetry.value, true)
  ctx.value = context('c1', 'historical_replay')
  await settle()
  assert.equal(model.canRetry.value, false)
  assert.equal(await model.retry(), false)
  ctx.value = context('c2')
  await settle()
  assert.equal(await model.retry(), false)
  assert.equal(versions.length, 3)
  model.dispose()
})

test('写响应跨会话晚到被丢弃；历史写入、错误关联和过期申请均拒绝', async () => {
  const api = apiFixture(), ctx = ref(context())
  let release!: (value: SimulationResult) => void
  api.event = async () => new Promise(resolve => { release = resolve })
  const model = useAfterSales(ctx, api)
  await settle()
  const write = model.submit('event', model.data.value!.operations[0], { event: 'create_execution' })
  ctx.value = context('c2')
  await settle()
  release({ conversation_id: 'c1', operation_id: 'op1' })
  assert.equal(await write, false)
  assert.equal(model.notice.value, '')
  assert.equal(model.busy.value, false)
  ctx.value = context('c2', 'historical_replay')
  await settle()
  assert.equal(await model.submit('event', operation(), { event: 'create_execution' }), false)
  ctx.value = context('c2')
  await settle()
  assert.equal(await model.submit('event', operation('op1', 99), { event: 'create_execution' }), false)
  api.event = async () => ({ conversation_id: 'c-other', operation_id: 'op1' })
  assert.equal(await model.submit('event', model.data.value!.operations[0], { event: 'create_execution' }), false)
  assert.match(model.actionError.value, /关联不匹配/)
  model.dispose()
})
