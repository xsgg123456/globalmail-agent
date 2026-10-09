import { test } from 'node:test'
import assert from 'node:assert/strict'
import { ref } from 'vue'
import { useAfterSales } from '../src/composables/useAfterSales'
import { MailApiError } from '../src/api/mail-agent-request'
import { emptyBranchFact, branchFactInput } from '../src/components/mail-agent/branch-fact-inputs'
import { emptySimulationForm, simulationInput } from '../src/components/mail-agent/after-sales-inputs'
import type { AfterSalesApi } from '../src/api/after-sales-api'
import { businessResult, settle } from './business-fixture'

test('早到库存没有规格和快照不能暗填；地址确认需要逐字客户来源', () => {
  const form = emptyBranchFact()
  Object.assign(form, { orderLine: 'line1', staff: 'operator', receipt: 'stock-proof', reason: 'Current exact stock' })
  assert.equal(branchFactInput(form).input, null)
  Object.assign(form, { item: 'sku', region: 'US', hardware: 'r1', snapshot: '2026-10-08T10:00:00Z', onHand: '0' })
  assert.equal(branchFactInput(form).input?.on_hand, 0)
  form.snapshot = '2026-10-08T10:00:00'
  assert.equal(branchFactInput(form).input, null)
  form.event = 'address_confirmation'
  assert.equal(branchFactInput(form).input, null)
  form.message = 'mail1'; form.quote = 'I confirm my address.'
  const output = branchFactInput(form).input
  assert.deepEqual(output?.selection_ref, { message_id: 'mail1', quote: form.quote })
  assert.equal('item_id' in output!, false)
})

test('取消回执与纠错尝试都需要实际证明', () => {
  const form = emptySimulationForm()
  form.event = 'cancellation_acknowledged'
  assert.equal(simulationInput(form, [form.event]).input, null)
  form.receiptRef = 'not-dispatched'; form.reason = 'Carrier and ERP verified'; form.confirmedNotExecuted = true
  assert.equal(simulationInput(form, [form.event]).input?.confirmed_not_executed, true)
  form.event = 'create_corrective_execution'
  assert.equal(simulationInput(form, [form.event]).input, null)
  form.staffId = 'operator'; form.correctionOf = 'original-success'
  assert.equal(simulationInput(form, [form.event]).input?.correction_of_execution_id, 'original-success')
})

test('连续事实丢回包保留原键与参数，不能新建第二条事件', async () => {
  const calls: { key: string; payload: Record<string, unknown> }[] = []
  const api: AfterSalesApi = {
    listing: async () => businessResult({ branch_id: 'b1', branch_generation: 1, conversation_version: 2, operations: [], executions: [], shipments: [], returns: [] }),
    event: async () => { throw new Error('unexpected event') }, link: async () => { throw new Error('unexpected link') },
    fact: async (_branch, payload, key) => {
      calls.push({ key, payload })
      if (calls.length === 1) throw new MailApiError(503, 'response_unknown', 'request1')
      return { conversation_id: 'c1', operation_id: '', event_id: 'real-event1' }
    }
  }
  const model = useAfterSales(ref({ id: 'c1', mode: 'interactive_simulation' as const, row_version: 2, input_revision: 1 }), api)
  await settle()
  assert.equal(await model.submitFact({ source_event_id: 's1', event: 'service_note', reason: 'Current fact' }), false)
  assert.equal(model.canRetry.value, true)
  assert.equal(await model.submitFact({ source_event_id: 's2' }), false)
  assert.equal(calls.length, 1)
  assert.equal(await model.retry(), true)
  assert.deepEqual(calls[0], calls[1])
  assert.equal(model.canRetry.value, false)
  model.dispose()
})
