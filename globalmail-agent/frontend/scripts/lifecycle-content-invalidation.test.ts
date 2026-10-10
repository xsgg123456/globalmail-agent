import assert from 'node:assert/strict'
import test from 'node:test'
import { effectScope } from 'vue'
import { createMailWorkbench } from '../src/composables/create-mail-workbench'
import { revokeConversationContent } from '../src/composables/content-invalidations'
import { ConversationEventSession, type EventStream } from '../src/composables/conversation-event-session'
import { useConversationAdvice } from '../src/composables/use-conversation-advice'
import type { ConversationAdvice } from '../src/api/agent-run-contract'
import { mailApi } from '../src/api/mail-agent'
import { detailFixture } from './mail-workbench-fixture'

function setup(prefix: string) {
  const server = new Map([prefix + '-a', prefix + '-b', prefix + '-other'].map(id => [id, detailFixture(id)]))
  const api = { ...mailApi,
    detail: async (id: string) => structuredClone(server.get(id)!),
    list: async () => ({ items: [...server.values()].map(item => structuredClone(item.conversation)), next_cursor: null }) }
  return { server, api, work: createMailWorkbench(api) }
}
for (const kind of ['attachment', 'document']) test(`${kind}清关联草稿、保留无关草稿；重复水位保留新输入`, async () => {
  const { server, work } = setup(kind)
  for (const id of server.keys()) {
    await work.select(id)
    work.setHuman({ reply: `${id}-private`, note: 'private' })
    work.setIncoming({ body: `${id}-incoming`, subject: 'private' })
  }
  await work.select(`${kind}-a`)
  const ids = [`${kind}-a`, `${kind}-b`]
  for (const id of ids) { server.get(id)!.review = null; server.get(id)!.conversation.content_revision = 101 }
  revokeConversationContent(ids, 101)
  assert.equal(work.detail.value, null)
  assert.equal(work.humanInput.value.reply, '')
  for (const id of ids) {
    await work.select(id)
    assert.equal(work.humanInput.value.reply, '')
    assert.equal(work.incomingInput.value.body, '')
  }
  work.setHuman({ reply: 'new clean reply', note: '' })
  revokeConversationContent(ids, 101)
  assert.equal(work.humanInput.value.reply, 'new clean reply')
  await work.select(`${kind}-other`)
  assert.equal(work.humanInput.value.reply, `${kind}-other-private`)
  assert.equal(work.incomingInput.value.body, `${kind}-other-incoming`)
  work.dispose()
})

test('删除前晚到详情不回填；新GET旧水位也不能恢复正文或列表', async () => {
  const { work, api } = setup('late')
  await work.select('late-a')
  let resolve!: (value: ReturnType<typeof detailFixture>) => void
  api.detail = () => new Promise(done => { resolve = done })
  const pending = work.refreshDetail()
  revokeConversationContent(['late-a'], 102)
  resolve(detailFixture('late-a')); await pending
  assert.equal(work.detail.value, null)
  api.detail = async () => detailFixture('late-a')
  await work.refreshDetail(); await work.refreshList()
  assert.equal(work.detail.value, null)
  assert.equal(work.items.value.some(item => item.id === 'late-a'), false)
  work.dispose()
})
for (const read of ['detail', 'list']) test(`外部删除错过通知后由${read}水位清草稿`, async () => {
  const { work, server } = setup(read)
  await work.select(`${read}-a`)
  work.setHuman({ reply: 'external-private', note: 'external-private' })
  server.get(`${read}-a`)!.conversation.content_revision = 103
  server.get(`${read}-a`)!.review = null
  if (read === 'list') await work.refreshList()
  else await work.refreshDetail()
  assert.equal(work.humanInput.value.reply, '')
  assert.equal(work.humanInput.value.note, '')
  await work.refreshDetail()
  assert.equal(work.humanInput.value.reply, '')
  work.dispose()
})
test('SSE payload为空仍靠作用域ID同步失效', async () => {
  const { work } = setup('sse')
  await work.select('sse-a'); work.setHuman({ reply: 'private', note: '' })
  let receive!: (event: MessageEvent<string>) => void
  const stream: EventStream = { onopen: null, onerror: null, close() {}, addEventListener(_type, callback) { receive = callback } }
  const session = new ConversationEventSession(() => stream)
  const scope = work.conversation.value!
  session.connect(scope, () => {}, () => {})
  receive({ data: JSON.stringify({ ...scope, conversation_id: scope.id, kind: 'content.revoked', seq: scope.next_seq + 1, payload: {} }) } as MessageEvent<string>)
  assert.equal(work.humanInput.value.reply, '')
  assert.equal(work.detail.value, null)
  session.close(); work.dispose()
})
test('失效同步清建议缓存并拒绝晚到建议', async () => {
  const { work } = setup('advice')
  await work.select('advice-a')
  let resolve!: (value: ConversationAdvice) => void
  const scope = effectScope()
  const advice = scope.run(() => useConversationAdvice(work, { advice: () => new Promise(done => { resolve = done }) }))!
  const stale: ConversationAdvice = { advice: null, run_id: null, input_revision: 1, stale: false, observations: [] }
  advice.snapshot.value = stale; advice.open.value = true
  const pending = advice.refresh()
  revokeConversationContent(['advice-a'], 104)
  assert.equal(advice.snapshot.value, null)
  assert.equal(advice.open.value, false)
  resolve(stale); await pending
  assert.equal(advice.snapshot.value, null)
  scope.stop(); work.dispose()
})

test('外部删除整个会话时404清当前正文/草稿，503仍保留', async () => {
  const { work, api } = setup('missing')
  const { MailApiError } = await import('../src/api/mail-agent-request')
  await work.select('missing-a')
  work.setHuman({reply:'private',note:'private'})
  api.detail=async()=>{throw new MailApiError(503,'unavailable','r')}
  await work.refreshDetail()
  assert.equal(work.humanInput.value.reply,'private')
  assert.ok(work.detail.value)
  api.detail=async()=>{throw new MailApiError(404,'not_found','r')}
  await work.refreshDetail()
  assert.equal(work.detail.value,null)
  assert.equal(work.humanInput.value.reply,'')
  assert.equal(work.selectedId.value,'')
  work.dispose()
})
