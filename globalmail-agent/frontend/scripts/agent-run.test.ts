import { test } from 'node:test'
import assert from 'node:assert/strict'
import { ref } from 'vue'
import { useAgentRunDetails } from '../src/composables/useAgentRunDetails'
import { useRunReference, type ReferenceSelection } from '../src/composables/useRunReference'
import {
  retryableRun,
  usageCost,
  outcomeLabel
} from '../src/components/mail-agent/agent-run-format'
import { MailApiError } from '../src/api/mail-agent-request'
import type { AgentRunDetail, RunReference } from '../src/api/agent-run-contract'
import {
  runFixture,
  runContext,
  runDetail,
  runReference,
  runApiFixture,
  settle
} from './agent-run-fixture'

test('默认只读取最新run，展开旧run才读取；空列表不发请求', async () => {
  const api = runApiFixture(),
    calls: string[] = []
  api.detail = async (id) => {
    calls.push(id)
    return runDetail(id)
  }
  const context = ref(runContext('c-1', [runFixture('older'), runFixture('latest')]))
  const model = useAgentRunDetails(context, api)
  await settle()
  assert.deepEqual(calls, ['latest'])
  model.expanded.value = ['older', 'latest']
  await settle()
  assert.deepEqual(calls, ['latest', 'older'])
  context.value = runContext('empty', [])
  await settle()
  assert.deepEqual(model.records.value, {})
  assert.deepEqual(model.expanded.value, [])
  assert.equal(calls.length, 2)
  model.dispose()
})

test('会话切换立即清理旧run，旧会话晚到响应不能覆盖', async () => {
  const api = runApiFixture()
  let resolveOld: ((value: AgentRunDetail) => void) | undefined
  api.detail = async (id) =>
    id === 'slow'
      ? new Promise((resolve) => {
          resolveOld = resolve
        })
      : runDetail(id)
  const context = ref(runContext('old', [runFixture('slow')]))
  const model = useAgentRunDetails(context, api)
  context.value = runContext('new', [runFixture('fresh')])
  await settle()
  resolveOld?.(runDetail('slow'))
  await settle()
  assert.equal(model.records.value.fresh.run.id, 'fresh')
  assert.equal(model.records.value.slow, undefined)
  assert.deepEqual(model.expanded.value, ['fresh'])
  model.dispose()
})

test('SSE刷新相同row_version仍读取展开记录，旧请求和更早同run响应均不覆盖', async () => {
  const api = runApiFixture(),
    pending: ((value: AgentRunDetail) => void)[] = []
  api.detail = () => new Promise((resolve) => pending.push(resolve))
  const context = ref(runContext())
  const model = useAgentRunDetails(context, api)
  await settle()
  context.value = runContext()
  await settle()
  assert.equal(pending.length, 2)
  const second = runDetail()
  second.usage.model_requests = 2
  pending[1](second)
  await settle()
  pending[0](runDetail())
  await settle()
  assert.equal(model.records.value['run-1'].usage.model_requests, 2)
  const older = model.refresh('run-1'),
    newer = model.refresh('run-1')
  const latest = runDetail()
  latest.usage.model_requests = 4
  pending[3](latest)
  await newer
  pending[2](runDetail())
  await older
  assert.equal(model.records.value['run-1'].usage.model_requests, 4)
  model.dispose()
})

test('run读取失败有错误且不保留旧结果，显式读取重试可恢复；卸载丢弃晚到响应', async () => {
  const api = runApiFixture(),
    model = useAgentRunDetails(ref(runContext()), api)
  await settle()
  api.detail = async () => {
    throw new MailApiError(503, 'database_unavailable', '')
  }
  await model.refresh('run-1')
  assert.match(model.errors.value['run-1'], /暂不可用/)
  assert.equal(model.records.value['run-1'], undefined)
  api.detail = async () => runDetail()
  await model.refresh('run-1')
  assert.equal(model.errors.value['run-1'], '')
  let release: ((value: AgentRunDetail) => void) | undefined
  api.detail = () =>
    new Promise((resolve) => {
      release = resolve
    })
  const pending = model.refresh('run-1')
  model.dispose()
  const late = runDetail()
  late.usage.model_requests = 6
  release?.(late)
  await pending
  assert.equal(model.records.value['run-1'].usage.model_requests, 0)
})

test('引用只带run和引用ID读取；切换/关闭忽略旧引用，停用真实状态不伪造有效', async () => {
  const api = runApiFixture(),
    calls: string[][] = []
  let resolveOld: ((value: RunReference) => void) | undefined
  api.reference = async (runId, id) => {
    calls.push([runId, id])
    return id === 'old'
      ? new Promise((resolve) => {
          resolveOld = resolve
        })
      : runReference(id, false)
  }
  const selection = ref<ReferenceSelection | null>({ runId: 'run-1', referenceId: 'old' })
  const model = useRunReference(selection, api)
  selection.value = { runId: 'run-2', referenceId: 'revoked' }
  await settle()
  resolveOld?.(runReference('old'))
  await settle()
  assert.deepEqual(calls, [
    ['run-1', 'old'],
    ['run-2', 'revoked']
  ])
  assert.equal(model.result.value?.eligible, false)
  assert.equal(model.result.value?.reference.text, '')
  selection.value = null
  assert.equal(model.result.value, null)
  model.dispose()
})

test('引用鉴权/网络失败清空正文并显示重试，重试成功后恢复', async () => {
  const api = runApiFixture()
  api.reference = async () => {
    throw new MailApiError(403, 'reference_unavailable', '')
  }
  const model = useRunReference(ref({ runId: 'run-1', referenceId: 'ref-1' }), api)
  await settle()
  assert.notEqual(model.error.value, '')
  assert.equal(model.result.value, null)
  api.reference = async () => runReference('ref-1')
  await model.refresh()
  assert.equal(model.result.value?.eligible, true)
  assert.equal(model.error.value, '')
  model.dispose()
})

test('预算耗尽不可重试；失败仅当前输入、人工处理权/生命周期/门禁允许才可重试', () => {
  const context = runContext()
  context.runs[0].status = 'budget_exhausted'
  assert.equal(retryableRun(context), null)
  for (const status of ['failed', 'stopped', 'interrupted'] as const) {
    context.runs[0].status = status
    assert.equal(retryableRun(context)?.id, 'run-1')
  }
  context.conversation.input_revision = 2
  assert.equal(retryableRun(context), null)
  context.conversation.input_revision = 1
  context.conversation.processing_owner = 'human_review'
  assert.equal(retryableRun(context), null)
  context.conversation.processing_owner = 'agent'
  context.conversation.auto_run_gate = 'disabled'
  assert.equal(retryableRun(context), null)
  context.conversation.auto_run_gate = 'open'
  context.conversation.lifecycle = 'resolved'
  assert.equal(retryableRun(context), null)
})

test('费用null保持未知，真实0与未知分开；历史对照结果文案不声明模拟已发送', () => {
  const usage = runDetail().usage
  assert.equal(usageCost(usage), '未知')
  usage.cost = 0
  assert.equal(usageCost(usage), '0')
  assert.match(outcomeLabel('historical_comparison'), /未加入历史邮件/)
  assert.doesNotMatch(outcomeLabel('historical_comparison'), /已发送/)
  assert.match(outcomeLabel('protocol_verified_model_not_connected'), /当时未接入模型/)
})
