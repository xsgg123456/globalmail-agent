import { test } from 'node:test'
import assert from 'node:assert/strict'
import { createRenderer, defineComponent, h } from 'vue'
import { createRouter, createMemoryHistory, RouterView } from 'vue-router'
import { useAgentConsole } from '../src/composables/use-agent-console'
import { mailApi } from '../src/api/mail-agent'
import { agentRunApi } from '../src/api/agent-run-api'
import { runContext } from './agent-run-fixture'

test('生产运行台在可达初始loading状态不得把null交给executionSteps', async () => {
  const originals = { list: mailApi.list, detail: mailApi.detail, run: agentRunApi.detail, source: globalThis.EventSource }
  const context = runContext('conversation-1')
  const pending = new Promise<never>(() => {})
  mailApi.list = async () => pending
  mailApi.detail = async () => context
  agentRunApi.detail = async () => pending
  Object.defineProperty(globalThis, 'EventSource', { value: class { onopen=null; onerror=null; addEventListener() {} close() {} }, configurable:true, writable:true })
  const errors: string[] = []
  const page = defineComponent({ setup() { const model = useAgentConsole(); return () => h('div', String(model.steps.value.length)) } })
  const router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/agent-runs', component: page }] })
  await router.push('/agent-runs?conversation_id=conversation-1&run_id=run-1')
  type Node = { kind:string }
  const renderer = createRenderer<Node,Node>({ patchProp() {},insert() {},remove() {},createElement:()=>({kind:'element'}),
    createText:()=>({kind:'text'}),createComment:()=>({kind:'comment'}),setText() {},setElementText() {},parentNode:()=>null,nextSibling:()=>null })
  const app = renderer.createApp({ render: () => h(RouterView) }); app.use(router)
  app.config.errorHandler = error => errors.push(String(error))
  try {
    app.mount({kind:'root'})
    assert.deepEqual(errors, [], '首次生产render发生异常：' + errors.join('; '))
  } finally {
    app.unmount(); mailApi.list=originals.list; mailApi.detail=originals.detail; agentRunApi.detail=originals.run
    Object.defineProperty(globalThis,'EventSource',{value:originals.source,configurable:true,writable:true})
  }
})
