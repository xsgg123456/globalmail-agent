import test from 'node:test'
import assert from 'node:assert/strict'
import { createRenderer, defineComponent, h, KeepAlive } from 'vue'
import { createRouter, createMemoryHistory, RouterView } from 'vue-router'
import { useAgentConsole } from '../src/composables/use-agent-console'
import { revokeConversationContent } from '../src/composables/content-invalidations'
import { mailApi } from '../src/api/mail-agent'
import { agentRunApi } from '../src/api/agent-run-api'
import { runContext, runDetail, settle } from './agent-run-fixture'

test('KeepAlive隐藏运行台立即清缓存并拒绝晚到详情', async () => {
  const originals = { list: mailApi.list, detail: mailApi.detail, run: agentRunApi.detail, source: globalThis.EventSource }
  const context = runContext('run-revoke-case')
  mailApi.list = async () => ({items:[context.conversation],next_cursor:null})
  mailApi.detail = async () => structuredClone(context)
  agentRunApi.detail = async () => runDetail()
  Object.defineProperty(globalThis, 'EventSource', { value: class { onopen=null; onerror=null; addEventListener() {} close() {} }, configurable:true, writable:true })
  let model!: ReturnType<typeof useAgentConsole>
  const page = defineComponent({ setup() { model=useAgentConsole(); return () => h('div', String(model.record.value?.run.id ?? 'empty')) } })
  const router = createRouter({ history:createMemoryHistory(), routes:[{path:'/agent-runs',component:page},{path:'/other',component:{render:()=>h('div')}}] })
  await router.push('/agent-runs?conversation_id=run-revoke-case&run_id=run-1')
  type Node = {kind:string}
  const renderer = createRenderer<Node,Node>({patchProp(){},insert(){},remove(){},createElement:()=>({kind:'element'}),createText:()=>({kind:'text'}),createComment:()=>({kind:'comment'}),setText(){},setElementText(){},parentNode:()=>null,nextSibling:()=>null})
  const app = renderer.createApp({render:()=>h(RouterView,null,{default:({Component}:{Component:object})=>h(KeepAlive,null,()=>h(Component))})})
  app.use(router)
  try {
    app.mount({kind:'root'}); await settle(); await settle()
    assert.equal(model.record.value?.run.id,'run-1')
    let resolve!: (value:ReturnType<typeof runDetail>)=>void
    agentRunApi.detail=()=>new Promise(done=>{resolve=done})
    const pending=model.refreshRun()
    await router.push('/other'); await settle()
    context.conversation.content_revision=200; context.review=null
    revokeConversationContent(['run-revoke-case'],200)
    assert.equal(model.record.value,null)
    await model.work.refreshDetail()
    assert.equal(model.record.value,null, '隐藏页重载相同run ID不得暴露旧loadedRecord')
    resolve(runDetail()); await pending
    assert.equal(model.record.value,null)
  } finally {
    app.unmount(); mailApi.list=originals.list;mailApi.detail=originals.detail;agentRunApi.detail=originals.run
    Object.defineProperty(globalThis,'EventSource',{value:originals.source,configurable:true,writable:true})
  }
})
