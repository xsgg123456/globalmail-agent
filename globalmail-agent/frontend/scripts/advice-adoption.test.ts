import { test } from 'node:test'
import assert from 'node:assert/strict'
import { effectScope } from 'vue'
import { useMailWorkbench } from '../src/composables/useMailWorkbench'
import { useConversationAdvice } from '../src/composables/use-conversation-advice'
import { detailFixture } from './mail-workbench-fixture'
import type { MailApi } from '../src/api/mail-agent'
import type { ConversationAdvice } from '../src/api/agent-run-contract'

function setup() {
  const server = detailFixture()
  server.review!.staff_draft = ''; server.review!.staff_note = ''
  server.runs = [{id:'r-1',processing_cycle_id:'cycle-1',attempt_no:1,status:'completed',
    input_revision:1,authority_epoch:0,branch_generation:1,stop_requested:false,
    outcome:'human_advice',error_code:null,created_at:'2026-10-09T00:00:00Z',started_at:null,finished_at:null}]
  const api:MailApi = { list:async()=>({items:[],next_cursor:null}), detail:async()=>structuredClone(server),
    example:async()=>({}),command:async()=>({}) }
  const value:ConversationAdvice = { advice:{summary:'advice',gaps:[],recommendations:[],draft:'agent-draft',
    facts:[],intents:[],run_id:'r-1',input_revision:1,queried_at:'2026-10-09T00:00:00Z'},
    run_id:'r-1',stale:false,input_revision:1,observations:[] }
  return {server,api,work:useMailWorkbench(api),value}
}

test('新review保留已编辑个人草稿但不能自动确认最新来信',async()=>{
  for (const previousReview of [false,true]) {
    const {work,server,api}=setup()
    let writes=0;api.command=async()=>{writes++;return {}}
    if(!previousReview) server.review=null
    server.conversation.processing_owner='human_wait_customer'
    await work.select('c-1'); work.setHuman({reply:'older-staff-draft',note:''})
    server.conversation.input_revision=3; server.conversation.row_version=4
    server.conversation.processing_owner='human_review'
    server.review={...detailFixture().review!,id:'h-new',input_revision:3,staff_draft:'',staff_note:''}
    await work.refreshDetail()
    assert.equal(work.humanInput.value.reply,'older-staff-draft')
    assert.equal(work.humanStale.value,true)
    await work.completeHuman();assert.equal(writes,0)
    work.acknowledgeHuman();assert.equal(work.humanStale.value,false)
  }
})

test('采用等待服务器复查时再次输入，不能被Agent草稿覆盖',async()=>{
  for (const initial of ['', 'previous staff draft']) {
    const {work,value}=setup();await work.select('c-1');work.setHuman({reply:initial,note:''})
    let release!:(value:ConversationAdvice)=>void
    const read=new Promise<ConversationAdvice>(resolve=>{release=resolve})
    const scope=effectScope()
    const advice=scope.run(()=>useConversationAdvice(work,{advice:async()=>read},async()=>{}))!
    advice.snapshot.value=value
    const pending=advice.adopt()
    // Confirmation and the server recheck are both asynchronous. Editing remains possible.
    work.setHuman({reply:'staff-text-entered-during-network',note:''});release(value)
    await pending
    assert.equal(work.humanInput.value.reply,'staff-text-entered-during-network')
    assert.match(advice.error.value,/继续编辑/)
    scope.stop()
  }
})

test('服务器判定过期或读取失败时拒绝采用，保持个人文本',async()=>{
  for (const failure of ['stale','network']) {
    const {work,value}=setup();await work.select('c-1')
    const scope=effectScope()
    const advice=scope.run(()=>useConversationAdvice(work,{advice:async()=>{
      if(failure==='network')throw Error('read failed')
      return {...value,stale:true}
    }},async()=>{}))!
    advice.snapshot.value=value;await advice.adopt()
    assert.equal(work.humanInput.value.reply,'');assert.ok(advice.error.value)
    scope.stop()
  }
})

test('合法采用只更新客服输入，不调用发送接口',async()=>{
  const {work,value,api}=setup();let writes=0;api.command=async()=>{writes++;return {}};await work.select('c-1')
  const scope=effectScope()
  const advice=scope.run(()=>useConversationAdvice(work,{advice:async()=>value},async()=>{}))!
  advice.snapshot.value=value;advice.open.value=true;await advice.adopt()
  assert.equal(work.humanInput.value.reply,'agent-draft');assert.equal(advice.open.value,false)
  assert.equal(work.detail.value?.messages.length,1)
  assert.equal(writes,0)
  scope.stop()
})
