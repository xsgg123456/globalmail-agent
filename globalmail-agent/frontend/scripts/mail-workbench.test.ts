import { test } from 'node:test'
import assert from 'node:assert/strict'
import { useMailWorkbench } from '../src/composables/useMailWorkbench'
import type { MailApi } from '../src/api/mail-agent'
import { MailApiError } from '../src/api/mail-agent-request'
import { detailFixture } from './mail-workbench-fixture'

function makeApi(): MailApi {
  return {
    list: async () => ({ items: [], next_cursor: null }),
    detail: async (id) => detailFixture(id),
    example: async () => ({}),
    command: async () => ({ conversation_id: 'c-1' })
  }
}

test('选择/刷新只GET，不生成任务；输入按会话保存；服务错误有真实状态', async () => {
  const api = makeApi()
  let writes = 0
  api.command = async () => {
    writes++
    return {}
  }
  const model = useMailWorkbench(api)
  await model.select('c-1')
  model.setIncoming({ subject: 'draft subject', body: 'new\nmail' })
  model.setHuman({ reply: 'human reply', note: 'note' })
  await model.select('c-2')
  await model.select('c-1')
  await model.refreshDetail()
  assert.equal(writes, 0)
  assert.equal(model.incomingInput.value.body, 'new\nmail')
  assert.equal(model.humanInput.value.reply, 'human reply')
  api.detail = async () => {
    throw new MailApiError(503, 'database_unavailable', '')
  }
  await model.refreshDetail()
  assert.match(model.detailError.value, /暂不可用/)
  assert.equal(model.detail.value?.conversation.id, 'c-1')
  assert.equal(model.incomingInput.value.body, 'new\nmail')
})

test('人工提交409保留文本并刷新；新来信不能静默重绑定草稿，明确核对后才使用新输入版本', async () => {
  const api = makeApi(),
    server = detailFixture()
  api.detail = async () => structuredClone(server)
  const submitted: Record<string, unknown>[] = []
  api.command = async (_path, payload) => {
    submitted.push(payload)
    if (submitted.length === 1) {
      server.conversation.row_version = 3
      server.conversation.input_revision = 2
      throw new MailApiError(409, 'stale_input_revision', 'r-1')
    }
    return { conversation_id: 'c-1' }
  }
  const model = useMailWorkbench(api)
  await model.select('c-1')
  model.setHuman({ reply: 'unsent reply', note: 'unsent note' })
  await model.completeHuman()
  assert.equal(model.humanInput.value.reply, 'unsent reply')
  assert.match(model.actionError.value, /已保留/)
  assert.equal(model.detail.value?.conversation.input_revision, 2)
  assert.equal(model.humanStale.value, true)
  assert.equal(submitted[0].expected_input_revision, 1)
  await model.refreshDetail()
  assert.equal(model.humanStale.value, true)
  model.acknowledgeHuman()
  assert.equal(model.humanStale.value, false)
  await model.completeHuman()
  assert.equal(submitted[1].expected_input_revision, 2)
  assert.equal(submitted[1].expected_version, 3)
  assert.equal(model.humanInput.value.reply, '')
})

test('网络结果未知后即使快照更新，重试仍是同key和同payload；成功才清空来信', async () => {
  const api = makeApi(),
    server = detailFixture()
  const writes: { payload: Record<string, unknown>; key: string }[] = []
  api.detail = async () => structuredClone(server)
  api.command = async (_path, payload, key) => {
    writes.push({ payload, key })
    if (writes.length === 1) {
      server.conversation.row_version = 8
      throw new MailApiError(0, 'timeout', '')
    }
    return { conversation_id: 'c-1' }
  }
  const model = useMailWorkbench(api)
  await model.select('c-1')
  model.setIncoming({ body: 'new mail', subject: '' })
  await model.append()
  assert.equal(model.incomingInput.value.body, 'new mail')
  await model.refreshDetail()
  await model.append()
  assert.equal(writes[0].key, writes[1].key)
  assert.deepEqual(writes[0].payload, writes[1].payload)
  assert.equal(writes[1].payload.expected_version, 2)
  assert.equal(model.incomingInput.value.body, '')
})

test('快速切换会话时忽略前一会话晚到快照', async () => {
  const api = makeApi()
  let release: ((value: ReturnType<typeof detailFixture>) => void) | undefined
  api.detail = async (id) =>
    id === 'slow'
      ? await new Promise((resolve) => {
          release = resolve
        })
      : detailFixture(id)
  const model = useMailWorkbench(api)
  const first = model.select('slow')
  await model.select('latest')
  release?.(detailFixture('slow'))
  await first
  assert.equal(model.detail.value?.conversation.id, 'latest')
  assert.equal(model.selectedId.value, 'latest')
})

test('列表分页和模式/状态过滤传给服务端，过滤变化重置页码', async () => {
  const api = makeApi(),
    queries: unknown[][] = []
  api.list = async (...args) => {
    queries.push(args)
    return { items: [], next_cursor: args[2] ? null : 'next-id' }
  }
  const model = useMailWorkbench(api)
  await model.refreshList()
  await model.paginate(true)
  assert.equal(model.page.value, 2)
  assert.equal(queries[1][2], 'next-id')
  await model.filter('mode', 'historical_replay')
  await model.filter('state', 'human_review')
  assert.equal(model.page.value, 1)
  assert.deepEqual(queries.at(-1), ['historical_replay', 'human_review', undefined])
})

test('人审草稿PATCH使用review版本，完成人工回复另带会话和输入版本', async () => {
  const api = makeApi(),
    calls: unknown[][] = []
  api.command = async (...args) => {
    calls.push(args)
    return {}
  }
  const model = useMailWorkbench(api)
  await model.select('c-1')
  await model.saveHuman()
  assert.equal(calls[0][0], '/human-reviews/h-1')
  assert.equal(calls[0][3], 'PATCH')
  assert.equal((calls[0][1] as Record<string, unknown>).expected_version, 1)
  assert.equal((calls[0][1] as Record<string, unknown>).draft, 'saved reply')
  assert.equal(
    (calls[0][1] as Record<string, unknown>).expected_input_revision,
    model.detail.value?.review?.input_revision
  )
})

test('自动人审晚于首次打开会话时加载服务器草稿，已有用户输入保留', async () => {
  for (const existing of ['', '客服已编辑的回复']) {
    const api = makeApi(),
      server = detailFixture()
    server.review = null
    api.detail = async () => structuredClone(server)
    const model = useMailWorkbench(api)
    await model.select('c-1')
    if (existing) model.setHuman({ reply: existing, note: '客服备注' })
    server.review = { ...detailFixture().review!, draft: '服务器未发送草稿', note: '证据缺口' }
    await model.refreshDetail()
    assert.equal(model.humanInput.value.reply, existing || '服务器未发送草稿')
    assert.equal(model.humanInput.value.note, existing ? '客服备注' : '证据缺口')
    assert.equal(model.humanStale.value, false)
  }
})

test('普通人工回复显式保持风险；自由文字不授权清除风险', async () => {
  const api = makeApi(),
    calls: Record<string, unknown>[] = []
  api.command = async (_path, payload) => {
    calls.push(payload)
    return {}
  }
  const model = useMailWorkbench(api)
  await model.select('c-1')
  assert.equal(model.humanInput.value.risk_decision, 'keep_active')
  model.setHuman({ reply: 'The risk is resolved', note: '已处理，误判' })
  await model.completeHuman()
  assert.equal(calls[0].risk_decision, 'keep_active')
  assert.equal(calls[0].expected_version, 2)
  assert.equal(calls[0].expected_input_revision, 1)
  assert.equal(model.humanInput.value.risk_decision, 'keep_active')
})

test('风险更正没有依据不提交；有依据提交明确决定及版本，失败保留输入', async () => {
  const api = makeApi(),
    server = detailFixture(),
    calls: Record<string, unknown>[] = []
  server.active_risks = [{ id: 'risk-1', kind: 'fire', status: 'active', sources: [] }]
  api.detail = async () => structuredClone(server)
  api.command = async (_path, payload) => {
    calls.push(payload)
    throw new MailApiError(503, 'database_unavailable', '')
  }
  const model = useMailWorkbench(api)
  await model.select('c-1')
  model.setHuman({ reply: '复核后的回复', note: ' \n ', risk_decision: 'corrected_by_human' })
  await model.completeHuman()
  assert.equal(calls.length, 0)
  assert.match(model.actionError.value, /复核依据/)
  model.setHuman({
    reply: '复核后的回复',
    note: '经客户确认，烧灼描述属于其他设备',
    risk_decision: 'corrected_by_human'
  })
  await model.refreshDetail()
  assert.equal(model.humanInput.value.risk_decision, 'corrected_by_human')
  await model.completeHuman()
  assert.equal(calls[0].risk_decision, 'corrected_by_human')
  assert.equal(calls[0].expected_version, 2)
  assert.equal(calls[0].expected_input_revision, 1)
  assert.equal(model.humanInput.value.reply, '复核后的回复')
  assert.equal(model.humanInput.value.risk_decision, 'corrected_by_human')
})

test('切会话、新接管、新输入或新风险都重置风险决定，保留人工文本', async () => {
  const api = makeApi(),
    server = detailFixture()
  server.active_risks = [{ id: 'risk-1', kind: 'fire', status: 'active', sources: [] }]
  api.detail = async (id) => (id === 'c-1' ? structuredClone(server) : detailFixture(id))
  const model = useMailWorkbench(api)
  await model.select('c-1')
  const choose = () =>
    model.setHuman({
      reply: '未发送的人工草稿',
      note: '复核依据',
      risk_decision: 'resolved_by_human'
    })
  choose()
  await model.select('c-2')
  assert.equal(model.humanInput.value.risk_decision, 'keep_active')
  await model.select('c-1')
  assert.equal(model.humanInput.value.risk_decision, 'keep_active')
  assert.equal(model.humanInput.value.reply, '未发送的人工草稿')
  choose()
  server.review!.id = 'new-review'
  await model.refreshDetail()
  assert.equal(model.humanInput.value.risk_decision, 'keep_active')
  choose()
  server.conversation.input_revision += 1
  await model.refreshDetail()
  assert.equal(model.humanInput.value.risk_decision, 'keep_active')
  assert.equal(model.humanStale.value, true)
  model.acknowledgeHuman()
  choose()
  server.active_risks.push({ id: 'risk-2', kind: 'injury', status: 'active', sources: [] })
  await model.refreshDetail()
  assert.equal(model.humanInput.value.risk_decision, 'keep_active')
  assert.equal(model.humanInput.value.reply, '未发送的人工草稿')
  assert.equal(model.humanInput.value.note, '复核依据')
})
