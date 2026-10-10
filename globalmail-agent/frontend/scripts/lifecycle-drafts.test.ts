import assert from 'node:assert/strict'
import test from 'node:test'
import { createMailWorkbench } from '../src/composables/create-mail-workbench'
import { mailApi } from '../src/api/mail-agent'
import { runContext } from './agent-run-fixture'

test('会话删除清除个人草稿并拒绝删除前尚未返回的详情', async () => {
  const context=runContext('deleted-conversation')
  let finish: ((value:typeof context)=>void)|undefined
  let wait=false
  const api={...mailApi, detail:async()=>wait?new Promise<typeof context>(resolve=>{finish=resolve}):context}
  const work=createMailWorkbench(api)
  await work.select(context.conversation.id)
  work.setHuman({reply:'private personal draft',note:'private note',risk_decision:'keep_active'})
  wait=true
  const pending=work.refreshDetail()
  work.forget(context.conversation.id)
  finish?.(context)
  await pending
  assert.equal(work.detail.value,null)
  assert.equal(work.selectedId.value,'')
  assert.equal(work.humanInput.value.reply,'')
  assert.equal(work.humanInput.value.note,'')
})
