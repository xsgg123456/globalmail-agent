import { test } from 'node:test'
import assert from 'node:assert/strict'
import {
  ConversationEventSession,
  readConversationEvent,
  type EventStream,
  type EventScope
} from '../src/composables/conversation-event-session'

const scope: EventScope = {
  id: 'c-1',
  workspace_id: 'w',
  branch_id: 'b',
  mode: 'interactive_simulation',
  next_seq: 5
}
const update = (seq: number, changes: Record<string, unknown> = {}) =>
  JSON.stringify({
    conversation_id: scope.id,
    workspace_id: 'w',
    branch_id: 'b',
    mode: 'interactive_simulation',
    seq,
    kind: 'message.accepted',
    payload: {},
    ...changes
  })
class Stream implements EventStream {
  onopen: ((event: Event) => void) | null = null
  onerror: ((event: Event) => void) | null = null
  handler: ((event: MessageEvent<string>) => void) | null = null
  closed = false
  addEventListener(type: string, callback: (event: MessageEvent<string>) => void) {
    assert.equal(type, 'update')
    this.handler = callback
  }
  close() {
    this.closed = true
  }
  send(data: string) {
    this.handler?.({ data } as MessageEvent<string>)
  }
}

test('事件只接受本会话作用域并按序去重', () => {
  assert.equal(readConversationEvent(update(5), scope, 5), null)
  assert.equal(readConversationEvent(update(6), scope, 5)?.seq, 6)
  for (const changes of [
    { conversation_id: 'other' },
    { workspace_id: 'other' },
    { branch_id: 'other' },
    { mode: 'historical_replay' },
    { seq: 1.1 },
    { payload: 'bad' }
  ]) {
    assert.throws(() => readConversationEvent(update(6, changes), scope, 5))
  }
})

test('连接带after_seq；断线保持同连接让原生EventSource补读；切会话取消旧连接与晚到事件', () => {
  const streams: Stream[] = [],
    urls: string[] = [],
    received: number[] = [],
    states: string[] = []
  const session = new ConversationEventSession((url) => {
    urls.push(url)
    const source = new Stream()
    streams.push(source)
    return source
  })
  session.connect(
    scope,
    (event) => received.push(event.seq),
    (state) => states.push(state)
  )
  assert.equal(urls[0], '/api/v1/conversations/c-1/events?after_seq=5')
  streams[0].send(update(6))
  streams[0].send(update(6))
  streams[0].onerror?.(new Event('error'))
  assert.equal(streams.length, 1)
  assert.match(states.at(-1) ?? '', /重连/)
  streams[0].send(update(7))
  session.connect(
    { ...scope, id: 'c-2', next_seq: 2 },
    (event) => received.push(event.seq),
    (state) => states.push(state)
  )
  assert.ok(streams[0].closed)
  streams[0].send(update(8))
  assert.deepEqual(received, [6, 7])
  streams[1].send(update(3, { conversation_id: 'c-2' }))
  assert.deepEqual(received, [6, 7, 3])
  session.close()
  assert.ok(streams[1].closed)
})

test('跨作用域或畸形事件关闭流，给出明确刷新恢复路径', () => {
  const source = new Stream(),
    states: string[] = []
  const session = new ConversationEventSession(() => source)
  session.connect(
    scope,
    () => assert.fail('无效事件不能刷新详情'),
    (state) => states.push(state)
  )
  source.send(update(6, { branch_id: 'other' }))
  assert.ok(source.closed)
  assert.match(states.at(-1) ?? '', /校验失败.*刷新/)
})
