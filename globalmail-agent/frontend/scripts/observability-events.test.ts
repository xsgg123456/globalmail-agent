import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createRenderer, defineComponent, computed, h, KeepAlive, onActivated, onDeactivated, onScopeDispose } from 'vue'
import { createRouter, createMemoryHistory, RouterView } from 'vue-router'
import { useAgentConsole } from '../src/composables/use-agent-console'
import { useRunObservability } from '../src/composables/use-run-observability'
import { mailApi } from '../src/api/mail-agent'
import { agentRunApi } from '../src/api/agent-run-api'
import { runContext } from './agent-run-fixture'
import type { ConversationDetail } from '../src/api/mail-agent-contract'
import type { EventStream } from '../src/composables/conversation-event-session'

const settle = async () => { for (let n = 0; n < 8; n++) await new Promise(resolve => setTimeout(resolve, 0)) }
type HostNode = { kind: string }

test('生产SSE撤销在其他读取失败或挂起时立即清追踪；KeepAlive离页拒绝晚到', async () => {
  const context = runContext('conversation-1'), sources: TestSource[] = []
  const originals = { list: mailApi.list, detail: mailApi.detail, run: agentRunApi.detail, source: globalThis.EventSource }
  let blocked: Promise<ConversationDetail> | null = null, release: ((value: ConversationDetail) => void) | undefined
  mailApi.list = async () => ({ items: [context.conversation], next_cursor: null })
  mailApi.detail = async () => blocked ?? context
  agentRunApi.detail = async () => { throw new Error('run record unavailable') }
  class TestSource implements EventStream {
    onopen = null; onerror = null
    listener: ((event: MessageEvent<string>) => void) | undefined
    constructor() { sources.push(this) }
    addEventListener(type: string, callback: (event: MessageEvent<string>) => void) { if (type === 'update') this.listener = callback }
    close() {}
  }
  Object.defineProperty(globalThis, 'EventSource', { value: TestSource, configurable: true, writable: true })
  let gets = 0, revoked = false
  let model: ReturnType<typeof useRunObservability> | undefined
  const trace = 'a'.repeat(32)
  const page = defineComponent({ name: 'ObservationTestPage', setup() {
    const consoleModel = useAgentConsole()
    model = useRunObservability(computed(() => consoleModel.run.value?.id), consoleModel.traceRevision, { run: async runId => {
      gets++
      return { run_id: runId, trace_id: trace, trace_url: revoked ? null : `http://127.0.0.1:3001/project/local/traces/${trace}`,
        export_status: revoked ? 'revoked' : 'exported', reason_code: revoked ? 'trace_revoked' : null }
    } })
    onActivated(model.activate); onDeactivated(model.suspend); onScopeDispose(model.dispose)
    return () => h('div')
  } })
  const router = createRouter({ history: createMemoryHistory(), routes: [
    { path: '/agent-runs', component: page }, { path: '/else', component: { render: () => h('div') } }
  ] })
  await router.push('/agent-runs?conversation_id=conversation-1&run_id=run-1')
  const renderer = createRenderer<HostNode, HostNode>({
    patchProp() {}, insert() {}, remove() {}, createElement: () => ({ kind: 'element' }),
    createText: () => ({ kind: 'text' }), createComment: () => ({ kind: 'comment' }), setText() {},
    setElementText() {}, parentNode: () => null, nextSibling: () => null
  })
  const app = renderer.createApp({ render: () => h(RouterView, {}, {
    default: ({ Component }: { Component: Parameters<typeof h>[0] }) => h(KeepAlive, {}, () => h(Component))
  }) })
  app.use(router); app.mount({ kind: 'root' })
  function event(seq: number) {
    sources.at(-1)?.listener?.({ data: JSON.stringify({ conversation_id: 'conversation-1',
      workspace_id: 'w', branch_id: 'b', mode: 'simulation', seq, kind: 'attachment.revoked', payload: {} }) } as MessageEvent<string>)
  }
  try {
    await settle(); assert.ok(model)
    assert.equal(model.record.value?.export_status, 'exported')
    const before = gets
    blocked = new Promise(resolve => { release = resolve })
    revoked = true; event(2)
    assert.equal(model.record.value, null)
    await settle()
    assert.ok(gets > before)
    assert.equal(model.record.value?.export_status, 'revoked')
    const during = gets
    event(3)
    assert.equal(model.record.value, null)
    await settle(); assert.ok(gets > during)
    await router.push('/else'); await settle()
    assert.equal(model.record.value, null)
    blocked = null; release?.(context)
    await settle(); assert.equal(model.record.value, null)
    await router.push('/agent-runs?conversation_id=conversation-1&run_id=run-1'); await settle()
    assert.equal(model.record.value?.export_status, 'revoked')
  } finally {
    app.unmount()
    mailApi.list = originals.list; mailApi.detail = originals.detail; agentRunApi.detail = originals.run
    Object.defineProperty(globalThis, 'EventSource', { value: originals.source, configurable: true, writable: true })
  }
})
