import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  formatMinor,
  parseMinor,
  businessStatus
} from '../src/components/mail-agent/business-format'
import { eligibilityInput } from '../src/components/mail-agent/business-eligibility-input'
import {
  recordFields,
  recordStatus,
  recordsForOrder,
  recordsForLine
} from '../src/components/mail-agent/business-records'
import { choiceLabel, choiceFields } from '../src/components/mail-agent/business-choices'
import { businessDetail } from './business-fixture'

test('货币最小单位保留精度，五种演练币种与日元采用正确位数', () => {
  for (const currency of ['USD', 'EUR', 'GBP', 'CAD', 'AUD']) {
    assert.match(formatMinor(1234, currency), /12\.34$/)
    assert.equal(parseMinor('12.34', currency), 1234)
  }
  assert.equal(parseMinor('1234', 'JPY'), 1234)
  assert.equal(parseMinor('12.34', 'JPY'), null)
  assert.match(formatMinor(1234, 'JPY'), /1,234$/)
  assert.match(formatMinor(Number.MAX_SAFE_INTEGER, 'USD'), /90,071,992,547,409\.91$/)
  assert.equal(parseMinor('90071992547409.91', 'USD'), Number.MAX_SAFE_INTEGER)
  assert.equal(parseMinor('90071992547409.92', 'USD'), null)
  assert.match(formatMinor(Number.MAX_SAFE_INTEGER + 1, 'USD'), /不可用/)
  assert.equal(formatMinor(null, 'USD'), '未知')
  assert.equal(formatMinor(0, null), '金额未知（币种未确认）')
})

test('同订单同SKU的两行物流严格分开，无关联记录不凭型号猜归属', () => {
  const data = businessDetail(true).data!
  data.orders[0].lines[1].sku = data.orders[0].lines[0].sku
  data.shipments = [
    { order_id: 'order-1', order_line_id: 'line-1', parcel_id: 'parcel-1' },
    { order_id: 'order-1', order_line_id: 'line-2', parcel_id: 'parcel-2' },
    { order_id: 'other', order_line_id: 'line-1', parcel_id: 'foreign' },
    { order_id: 'order-1', sku: 'lamp-us', parcel_id: 'unbound' }
  ]
  data.operations = [{ order_id: 'order-1', order_line_id: 'line-2', operation_id: 'op-2' }]
  data.executions = [{ order_id: 'order-1', order_line_id: 'line-2', operation_id: 'op-2' }]
  data.returns = [{ order_id: 'order-1', line_id: 'line-2', return_id: 'return-2' }]
  assert.deepEqual(
    recordsForLine(data, 'order-1', 'line-1').shipments.map((row) => row.parcel_id),
    ['parcel-1']
  )
  const second = recordsForLine(data, 'order-1', 'line-2')
  assert.deepEqual(
    second.shipments.map((row) => row.parcel_id),
    ['parcel-2']
  )
  assert.equal(second.operations.length, 1)
  assert.equal(second.executions.length, 1)
  assert.equal(second.returns.length, 1)
})

test('已取得的客户选择保留明确拒绝、零金额与未绑定商品，不用候选表单补齐', () => {
  const data = businessDetail(true).data!
  const choice = {
    action: 'refund',
    accepted: false,
    amount_minor: 0,
    currency: 'USD',
    source_kind: 'synthetic'
  }
  assert.equal(choiceLabel(choice), '退款 · 未同意')
  assert.equal(
    choiceFields(choice, data).find((row) => row.label === '对应商品')?.value,
    '尚未明确对应商品'
  )
  assert.match(choiceFields(choice, data).find((row) => row.label === '金额')!.value, /0\.00$/)
  const bound = { ...choice, accepted: true, order_line_id: 'line-2', quantity: 1 }
  assert.match(choiceFields(bound, data).find((row) => row.label === '对应商品')!.value, /第2项/)
  assert.equal(choiceLabel({ ...choice, accepted: undefined }), '退款 · 是否同意未确认')
})

test('资格输入转精确整数，拒绝负数/小数量/指数/超大金额，保留原输入', () => {
  const form = {
    action: 'refund' as const,
    quantity: '2',
    amount: '12.34',
    currency: 'usd',
    itemId: ''
  }
  const built = eligibilityInput(form, 'line-1')
  assert.deepEqual(built.errors, {})
  assert.deepEqual(built.request, {
    action: 'refund',
    quantity: 2,
    amount_minor: 1234,
    currency: 'USD',
    item_id: null,
    order_line_id: 'line-1'
  })
  assert.equal(form.currency, 'usd')
  for (const quantity of ['0', '-1', '1.5', '1e2', '9007199254740992'])
    assert.ok(eligibilityInput({ ...form, quantity }, '').errors.quantity)
  for (const amount of ['-1', '12.345', '1e3', '90071992547409.92'])
    assert.ok(eligibilityInput({ ...form, amount }, '').errors.amount)
  assert.equal(eligibilityInput({ ...form, amount: '' }, '').request.amount_minor, null)
})

test('状态有可读区分，创建单据不声明履约成功，订单关联不混入其他单据', () => {
  const statuses = ['empty', 'needs_input', 'unavailable', 'unknown', 'error'] as const
  assert.equal(
    new Set(statuses.map((status) => businessStatus({ ...businessDetail(), status }))).size,
    5
  )
  assert.match(recordStatus('created'), /尚未确认/)
  const rows = recordFields(
    { execution_id: 'ex-1', status: 'created', source_kind: 'synthetic' },
    'executions'
  )
  assert.equal(rows.find((row) => row.label === '更新时间')?.value, '未记录')
  const data = businessDetail().data!
  data.operations = [
    { order_id: 'order-1', operation_id: 'op-1' },
    { order_id: 'other', operation_id: 'op-2' }
  ]
  data.executions = [
    { operation_id: 'op-1', execution_id: 'ex-1' },
    { operation_id: 'op-2', execution_id: 'ex-2' }
  ]
  assert.deepEqual(
    recordsForOrder(data, 'order-1').executions.map((record) => record.execution_id),
    ['ex-1']
  )
})
