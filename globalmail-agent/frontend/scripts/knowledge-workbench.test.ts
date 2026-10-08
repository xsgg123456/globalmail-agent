import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createRenderer } from 'vue'
import { useKnowledgeWorkbench } from '../src/composables/useKnowledgeWorkbench'
import { useKnowledgeCommands } from '../src/composables/useKnowledgeCommands'
import { MailApiError, unwrapMailEnvelope } from '../src/api/mail-agent-request'
import { makeApi, makeDocument, makeVersion } from './knowledge-fixture'

test('知识写入接受202；丢失响应后重试保留原body/key，409后允许明确刷新版本', async () => {
  const api = makeApi(),
    writes: { body: Record<string, unknown>; key: string }[] = []
  api.command = async (_path, body, key) => {
    writes.push({ body, key })
    if (writes.length === 1) throw new MailApiError(0, 'timeout', '')
    if (writes.length === 3) throw new MailApiError(409, 'stale_version', 'r1')
    return unwrapMailEnvelope(
      {
        code: 202,
        msg: 'ok',
        request_id: 'r1',
        data: { document_id: 'd1', version_id: 'v1', version: 2 }
      },
      202
    )
  }
  const commands = useKnowledgeCommands(api)
  await assert.rejects(commands.command('/review', { expected_version: 2, note: '实际核对备注' }))
  await commands.command('/review', { expected_version: 8, note: '实际核对备注' })
  assert.equal(writes[0].key, writes[1].key)
  assert.deepEqual(writes[0].body, writes[1].body)
  await assert.rejects(commands.command('/review', { expected_version: 8, note: '另一轮核对' }))
  await commands.command('/review', { expected_version: 9, note: '另一轮核对' })
  assert.notEqual(writes[2].key, writes[3].key)
  assert.equal(writes[3].body.expected_version, 9)
})
test('上传响应未知保留原key，成功后复用上传结果，不重复生成原件', async () => {
  const api = makeApi(),
    keys: string[] = []
  api.upload = async (_file, key) => {
    keys.push(key)
    if (keys.length === 1) throw new MailApiError(0, 'network', '')
    return {
      object_id: 'o1',
      sha256: 'a'.repeat(64),
      size_bytes: 4,
      format: 'md',
      page_count: null
    }
  }
  const commands = useKnowledgeCommands(api),
    file = new File(['资料'], 'source.md')
  await assert.rejects(commands.upload(file))
  assert.equal((await commands.upload(file)).object_id, 'o1')
  await commands.upload(new File(['资料'], 'source.md'))
  assert.equal(keys.length, 2)
  assert.equal(keys[0], keys[1])
  await assert.rejects(commands.upload({ size: 50 * 1024 * 1024 + 1 } as File), /50 MiB/)
})
test('详情读取只GET；快速切换资料/同版刷新时晚到响应不能覆盖当前资料', async () => {
  const api = makeApi()
  let writes = 0,
    release: ((value: ReturnType<typeof makeVersion>) => void) | undefined
  api.command = async () => {
    writes++
    return { document_id: 'd1', version_id: 'v1', version: 2 }
  }
  api.version = async (id) =>
    id === 'slow'
      ? new Promise((resolve) => {
          release = resolve
        })
      : makeVersion(id)
  const model = useKnowledgeWorkbench(api),
    first = model.select('old', 'slow')
  await model.select('current', 'latest')
  release?.(makeVersion('slow'))
  await first
  assert.equal(model.detail.value?.version.id, 'latest')
  assert.equal(writes, 0)
  let count = 0
  api.version = async (id) => {
    count++
    if (count === 1)
      return new Promise((resolve) => {
        release = resolve
      })
    const result = makeVersion(id)
    result.version.row_version = 9
    return result
  }
  const refresh = model.refreshDetail()
  await model.refreshDetail()
  release?.(makeVersion('latest'))
  await refresh
  assert.equal(model.detail.value?.version.row_version, 9)
  model.closeDetail()
})
test('筛选和分页真实传参；命令失败保留错误，GET恢复不清空操作错误', async () => {
  const api = makeApi(),
    queries: Record<string, string>[] = []
  api.list = async (query) => {
    queries.push(query)
    return { items: [], next_cursor: 'next' }
  }
  const model = useKnowledgeWorkbench(api)
  await model.refreshList()
  await model.paginate(true)
  model.filters.value.sku = 'OUTON-1'
  model.filters.value.brand = 'OUTON'
  await model.filter()
  assert.equal(queries[1].cursor, 'next')
  assert.equal(queries[2].cursor, '')
  assert.equal(queries[2].sku, 'OUTON-1')
  assert.equal(queries[2].brand, 'OUTON')
  await model.select('d1', 'v1')
  api.command = async () => {
    throw new MailApiError(409, 'stale_version', 'r1')
  }
  const input = { expected_version: 1, note: '尚未提交的备注' }
  await assert.rejects(model.execute('/review', input))
  assert.match(model.actionError.value, /输入已保留/)
  await model.refreshDetail()
  assert.match(model.actionError.value, /输入已保留/)
  assert.equal(input.note, '尚未提交的备注')
  model.closeDetail()
})
test('任务轮询在组件卸载后停止，晚到详情不再写界面', async () => {
  const api = makeApi()
  let calls = 0,
    model: ReturnType<typeof useKnowledgeWorkbench> | undefined
  api.document = async (id) => makeDocument(id)
  api.version = async (id) => {
    calls++
    const result = makeVersion(id)
    result.jobs = [
      {
        id: 'j1',
        kind: 'knowledge',
        version_id: id,
        status: 'running',
        stage: 'parsing',
        row_version: 1,
        attempt_no: 1,
        error_code: null,
        retryable: false,
        parser_profile_id: 'markdown'
      }
    ]
    return result
  }
  const renderer = createRenderer<Record<string, unknown>, Record<string, unknown>>({
    patchProp() {},
    insert() {},
    remove() {},
    createElement: () => ({}),
    createText: () => ({}),
    createComment: () => ({}),
    setText() {},
    setElementText() {},
    parentNode: () => null,
    nextSibling: () => null
  })
  const app = renderer.createApp({
    setup() {
      model = useKnowledgeWorkbench(api)
      return () => null
    }
  })
  app.mount({})
  await new Promise((resolve) => setImmediate(resolve))
  await model!.select('d1', 'v1')
  const before = calls
  app.unmount()
  await new Promise((resolve) => setTimeout(resolve, 1650))
  assert.equal(calls, before)
})
