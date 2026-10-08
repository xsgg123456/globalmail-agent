import { test } from 'node:test'
import assert from 'node:assert/strict'
import { useKnowledgeIndex } from '../src/composables/useKnowledgeIndex'
import { useReleaseManager } from '../src/composables/useReleaseManager'
import { useKnowledgeSearch } from '../src/composables/useKnowledgeSearch'
import { MailApiError } from '../src/api/mail-agent-request'
import type { KnowledgeIndexApi } from '../src/api/knowledge-index-api'
import type { IndexStatus, IndexBuild } from '../src/api/knowledge-index-contract'
import { makeApi, makeDocument, makeVersion } from './knowledge-fixture'

const state = (epoch = 0): IndexStatus => ({
  builds: [],
  publication: null,
  document_row_version: epoch + 1,
  revocation_epoch: epoch,
  withdrawn: false
})
function api(): KnowledgeIndexApi {
  return {
    profiles: async () => ({ items: [], chunkers: [] }),
    status: async () => state(),
    releases: async () => ({
      head: { release_id: null, epoch: 0, embedding_profile_id: null },
      items: []
    }),
    command: async () => ({}),
    search: async () => ({
      reason: 'scope_unavailable',
      head: {
        release_id: null,
        epoch: 0,
        embedding_profile_id: null
      },
      candidate_count: 0,
      evidence: [],
      usage: null,
      diagnostics: []
    }),
    reference: async () => {
      throw new Error('unused')
    }
  }
}
test('索引与发布未知响应重试固定body/key和CAS；明确409后新键重提', async () => {
  const service = api(),
    writes: { body: Record<string, unknown>; key: string }[] = []
  service.command = async (_path, body, key) => {
    writes.push({ body, key })
    if (writes.length === 1) throw new MailApiError(0, 'timeout', '')
    if (writes.length === 3) throw new MailApiError(409, 'stale_release', 'r')
    return {}
  }
  const model = useKnowledgeIndex(service)
  await assert.rejects(
    model.execute('/knowledge/releases', {
      expected_release_epoch: 1,
      build_ids: ['b1'],
      replace_all: false
    })
  )
  await model.execute('/knowledge/releases', {
    expected_release_epoch: 4,
    build_ids: ['b1'],
    replace_all: false
  })
  assert.deepEqual(writes[0], writes[1])
  await assert.rejects(
    model.execute('/knowledge/releases', {
      expected_release_epoch: 4,
      build_ids: ['b2'],
      replace_all: false
    })
  )
  assert.match(model.actionError.value, /发布记录已变化/)
  await model.refresh()
  assert.match(model.actionError.value, /输入已保留/)
  await model.execute('/knowledge/releases', {
    expected_release_epoch: 8,
    build_ids: ['b2'],
    replace_all: false
  })
  assert.notEqual(writes[2].key, writes[3].key)
  assert.equal(writes[3].body.expected_release_epoch, 8)
  model.close()
})
test('同版本刷新和资料切换晚到不覆盖；关闭后不再写入', async () => {
  const service = api()
  let resolve: ((value: IndexStatus) => void) | undefined,
    writes = 0
  service.command = async () => {
    writes++
    return {}
  }
  service.status = async (id) =>
    id === 'slow'
      ? new Promise((r) => {
          resolve = r
        })
      : state(5)
  const model = useKnowledgeIndex(service),
    first = model.refresh('slow')
  await model.refresh('current')
  resolve?.(state(1))
  await first
  assert.equal(model.status.value?.document_row_version, 6)
  assert.equal(writes, 0)
  const late = model.refresh('slow')
  model.close()
  resolve?.(state(9))
  await late
  assert.equal(model.status.value, null)
})
test('整批切换收集全部分页，不漏当前生效资料；错误不伪装候选完成', async () => {
  const content = makeApi(),
    index = api(),
    queries: Record<string, string>[] = []
  content.list = async (query) => {
    queries.push(query)
    return {
      items: [makeDocument(query.cursor || 'd1').document],
      next_cursor: query.cursor ? null : 'd2'
    }
  }
  const model = useReleaseManager(content, index)
  await model.load()
  assert.equal(model.candidates.value.length, 2)
  assert.equal(queries[1].cursor, 'd2')
  index.status = async () => {
    throw new MailApiError(503, 'database_unavailable', 'r')
  }
  await model.load()
  assert.equal(model.candidates.value.length, 0)
  assert.match(model.error.value, /暂不可用/)
})
test('整批候选加载结束后关闭，迟到结果不会更新抽屉', async () => {
  const content = makeApi(),
    index = api()
  content.list = async () => ({ items: [makeDocument('d1').document], next_cursor: null })
  let finish: (() => void) | undefined
  index.status = () =>
    new Promise((resolve) => {
      finish = () => resolve(state())
    })
  const model = useReleaseManager(content, index),
    request = model.load()
  await new Promise((resolve) => setImmediate(resolve))
  model.cancel()
  finish?.()
  await request
  assert.deepEqual(model.candidates.value, [])
})
test('试查保留实际请求条件，后续编辑不把旧结果说成新条件；关闭后丢弃迟到结果', async () => {
  const service = api(),
    original = service.search
  let finish: (() => void) | undefined
  service.search = (body) =>
    new Promise((resolve) => {
      finish = async () => resolve(await original(body))
    })
  const model = useKnowledgeSearch(service),
    command = { query: '完整原问题', sku: 'H-CTD16-US-BK', mode: 'simulation' as const }
  const request = model.search(command)
  command.query = '后来输入的问题'
  assert.equal(model.input.value?.query, '完整原问题')
  finish?.()
  await request
  assert.equal(model.result.value?.reason, 'scope_unavailable')
  const late = model.search(command)
  model.close()
  finish?.()
  await late
  assert.equal(model.result.value, null)
})
test('向量服务报错和来源不完整分开显示；错误后原问题仍可重试', async () => {
  const service = api(),
    model = useKnowledgeSearch(service)
  service.search = async () => {
    throw new MailApiError(0, 'timeout', '')
  }
  const command = { query: '完整原问题', sku: 'H-CTD16-US-BK', mode: 'simulation' as const }
  await model.search(command)
  assert.match(model.error.value, /未确认/)
  assert.equal(model.result.value, null)
  service.search = async () => ({
    reason: 'incomplete_source',
    head: { release_id: 'r', epoch: 3, embedding_profile_id: 'p' },
    candidate_count: 0,
    evidence: [],
    usage: null,
    diagnostics: [{ code: 'source_unavailable' }]
  })
  await model.search(command)
  assert.equal(model.error.value, '')
  assert.equal(model.result.value?.reason, 'incomplete_source')
  model.close()
})
test('当前是新草稿时，整批发布仍展示历史生效版本的合格构建', async () => {
  const content = makeApi(),
    index = api(),
    calls: string[] = []
  const detail = makeDocument('d1', 'v2')
  detail.document.current_version_number = 2
  detail.versions[0].number = 2
  detail.versions.push({ ...makeVersion('v1').version, status: 'reviewed', published: true })
  content.document = async () => detail
  content.list = async () => ({ items: [detail.document], next_cursor: null })
  const build: IndexBuild = {
    id: 'b1',
    version_id: 'v1',
    job_id: 'j1',
    status: 'ready',
    stage: 'ready',
    row_version: 2,
    profile_id: 'p1',
    profile_key: 'qwen3.7-text-embedding',
    chunker_key: 'structure_v1_500',
    chunk_count: 1,
    embedded_count: 1,
    cache_hits: 0,
    eligible: true,
    usage: [],
    error_code: null,
    retryable: false,
    manifest_sha256: 'a'.repeat(64)
  }
  index.status = async (id) => {
    calls.push(id)
    return { ...state(), builds: id === 'v1' ? [build] : [] }
  }
  const model = useReleaseManager(content, index)
  await model.load()
  assert.deepEqual(calls, ['v2', 'v1'])
  assert.equal(model.candidates.value[0].builds[0].id, 'b1')
  assert.equal(model.candidates.value[0].versions.v1, 1)
})
