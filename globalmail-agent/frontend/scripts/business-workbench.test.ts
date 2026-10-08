import { test } from 'node:test'
import assert from 'node:assert/strict'
import { ref } from 'vue'
import type {
  BusinessContext,
  BusinessResult,
  BusinessDetailData,
  EligibilityData,
  AvailabilityData
} from '../src/api/business-contract'
import { useBusinessDetails } from '../src/composables/useBusinessDetails'
import { useBusinessPreviews } from '../src/composables/useBusinessPreviews'
import { useBusinessScenarios } from '../src/composables/useBusinessScenarios'
import { MailApiError } from '../src/api/mail-agent-request'
import { businessApiFixture, businessDetail, contextFixture, settle } from './business-fixture'

test('多商品不自动选首行；精确订单号查询不产生写命令，模拟格式原样传递', async () => {
  const api = businessApiFixture(),
    calls: unknown[][] = []
  api.detail = async (...args) => {
    calls.push(args)
    return businessDetail(true)
  }
  api.createScenario = async () => {
    throw new Error('不应写入')
  }
  api.eligibility = async () => {
    throw new Error('只查询订单时不应试查')
  }
  const model = useBusinessDetails(ref(contextFixture()), api)
  await settle()
  assert.equal(model.selectedLine.value, '')
  assert.equal(model.target.value, undefined)
  assert.equal(model.lines.value.length, 2)
  for (const number of ['ORDER-demo', '999-7100051-8100000', 'demonstration']) {
    model.orderNumber.value = ` ${number} `
    await model.search()
    assert.deepEqual(calls.at(-1), ['c-1', number, ''])
  }
  model.dispose()
})

test('会话切换及版本变化立即清除旧业务，忽略晚到结果', async () => {
  const api = businessApiFixture(),
    context = ref<BusinessContext | null>(contextFixture('slow'))
  let release: ((value: BusinessResult<BusinessDetailData>) => void) | undefined
  api.detail = async (id) =>
    id === 'slow'
      ? await new Promise((resolve) => {
          release = resolve
        })
      : businessDetail(true)
  const model = useBusinessDetails(context, api)
  model.orderNumber.value = 'old draft'
  context.value = contextFixture('latest')
  assert.equal(model.orderNumber.value, '')
  await settle()
  release?.(businessDetail())
  await settle()
  assert.equal(model.selectedLine.value, '')
  assert.equal(model.lines.value.length, 2)
  const releases: ((value: BusinessResult<BusinessDetailData>) => void)[] = []
  api.detail = async () =>
    await new Promise((resolve) => {
      releases.push(resolve)
    })
  const oldRequest = model.refresh()
  context.value = { ...context.value!, row_version: 9 }
  assert.equal(model.result.value, null)
  releases[0](businessDetail())
  await oldRequest
  assert.equal(model.result.value, null)
  releases[1](businessDetail(true))
  await settle()
  assert.equal(model.lines.value.length, 2)
  assert.equal(model.selectedLine.value, '')
  model.dispose()
})

test('业务网络失败保留精确订单输入；空结果、历史不可用和未知不伪造订单', async () => {
  const api = businessApiFixture(),
    model = useBusinessDetails(ref(contextFixture()), api)
  await settle()
  model.orderNumber.value = 'ORDER-not-found'
  api.detail = async () => {
    throw new MailApiError(0, 'network', '')
  }
  await model.search()
  assert.match(model.error.value, /输入已保留/)
  assert.equal(model.orderNumber.value, 'ORDER-not-found')
  assert.equal(model.result.value, null)
  for (const status of ['empty', 'unavailable', 'unknown'] as const) {
    api.detail = async () => ({ ...businessDetail(), status, data: null })
    await model.search()
    assert.equal(model.result.value?.status, status)
    assert.equal(model.lines.value.length, 0)
  }
  model.dispose()
})

test('只读资格请求使用规范字段，晚到资格与库存不能串到新会话', async () => {
  const api = businessApiFixture(),
    context = ref<BusinessContext | null>(contextFixture())
  const model = useBusinessPreviews(context, api)
  const input = {
    action: 'refund' as const,
    order_line_id: 'line-1',
    quantity: 1,
    amount_minor: 1234,
    currency: 'USD',
    item_id: null
  }
  let releaseEligibility: ((value: BusinessResult<EligibilityData>) => void) | undefined
  let releaseAvailability: ((value: BusinessResult<AvailabilityData>) => void) | undefined
  const server = businessApiFixture()
  api.eligibility = async (_id, payload) => {
    assert.deepEqual(payload, input)
    return await new Promise((resolve) => {
      releaseEligibility = resolve
    })
  }
  api.availability = async (_id, lineId, itemId) => {
    assert.equal(lineId, 'line-1')
    assert.equal(itemId, 'SIM-PART-1')
    return await new Promise((resolve) => {
      releaseAvailability = resolve
    })
  }
  const check = model.checkEligibility(input),
    stock = model.checkAvailability('line-1', 'SIM-PART-1')
  context.value = contextFixture('c-2')
  releaseEligibility?.(await server.eligibility('c-1', input))
  releaseAvailability?.(await server.availability('c-1', 'line-1', 'SIM-PART-1'))
  await Promise.all([check, stock])
  assert.equal(model.eligibility.value, null)
  assert.equal(model.availability.value, null)
  assert.equal(model.eligibilityLoading.value, false)
  assert.equal(model.availabilityLoading.value, false)
  api.eligibility = async () => {
    throw new MailApiError(0, 'timeout', '')
  }
  await model.checkEligibility(input)
  assert.match(model.eligibilityError.value, /输入已保留/)
  assert.equal(input.amount_minor, 1234)
  model.dispose()
})

test('场景创建未知结果重试使用同键和固定expected_version，成功后新建独立命令', async () => {
  const api = businessApiFixture(),
    writes: { id: string; payload: Record<string, unknown>; key: string }[] = []
  api.createScenario = async (id, payload, key) => {
    writes.push({ id, payload, key })
    if (writes.length === 1) throw new MailApiError(0, 'timeout', '')
    return { conversation_id: `created-${writes.length}` }
  }
  const model = useBusinessScenarios(api)
  model.selectedId.value = 'SCN-004'
  assert.equal(await model.create(), null)
  assert.equal(model.selectedId.value, 'SCN-004')
  assert.match(model.error.value, /结果尚未确认/)
  assert.equal(await model.create(), 'created-2')
  assert.deepEqual(writes[0].payload, { expected_version: 0 })
  assert.deepEqual(writes[0], writes[1])
  await model.create()
  assert.notEqual(writes[1].key, writes[2].key)
})
