<template>
  <div>
    <div class="page-content flex !p-0 overflow-hidden mail-layout">
      <MailConversationList :items="items" :selected-id="selectedId" :state="state" :loading="listLoading" :error="listError" :page="page" :has-next="Boolean(nextCursor)" @select="selectMail" @filter="filter('state',$event)" @refresh="refreshList" @previous="paginate(false)" @next="paginate(true)" />
      <section class="flex-1 min-w-0 flex flex-col min-h-0" aria-label="邮件往来">
        <div class="p-4 flex-cb flex-wrap gap-3">
          <div class="min-w-0"><h2 class="text-base font-medium break-words">{{ conversation?.subject || '邮件往来' }}</h2><p v-if="conversation" class="text-xs text-g-700 mt-2 break-all">{{ conversation.sender_key }} · {{ modeLabel(conversation.mode) }}</p></div>
          <div v-if="conversation" class="flex flex-wrap gap-2"><ElButton :disabled="busy || conversation.lifecycle !== 'open' || (conversation.human_claimed && conversation.processing_owner === 'human_review')" @click="takeover">人工接管</ElButton><ElButton :disabled="busy || conversation.lifecycle !== 'open'" @click="confirmClose">标记已解决</ElButton><ElButton :loading="detailLoading" @click="refreshCurrent">刷新</ElButton></div>
        </div>
        <ElAlert v-if="detailError || actionError" :title="detailError || actionError" type="error" :closable="false" class="mx-4 mb-3 !w-auto" />
        <ElAlert v-if="actionNotice" :title="actionNotice" type="success" class="mx-4 mb-3 !w-auto" @close="actionNotice=''" />
        <ElSkeleton v-if="detailLoading && !detail" :rows="6" animated class="p-4" />
        <template v-else-if="detail && conversation">
          <div class="mx-4 mb-3 p-3 rounded-md bg-active-color flex-cb flex-wrap gap-3">
            <div class="flex items-center flex-wrap gap-2 text-sm"><ArtSvgIcon icon="ri:robot-2-line" class="text-lg text-theme" /><span>Agent</span><ElTag size="small" effect="plain">{{ conversationState(conversation) }}</ElTag><span class="text-xs text-g-700">{{ statusNote }}</span></div>
            <div class="flex flex-wrap gap-2"><ElButton size="small" @click="showAdvice">查看客服建议</ElButton><ElButton size="small" @click="openRuns()">全部 {{ roundCount }} 轮 →</ElButton><ElButton type="primary" plain size="small" :disabled="!detail.runs.length" @click="openRuns(detail.runs.at(-1)?.id)">查看最新运行 →</ElButton></div>
          </div>
          <p v-if="focusedMessage" class="mx-4 mb-3 text-xs text-theme" role="status">已定位第 {{ focusedMessage.seq }} 封邮件 · {{ focusedMessage.sender === 'customer' ? '客户来信' : '跟进回复' }}</p>
          <MessageTimeline ref="timeline" :messages="detail.messages" :conversation-id="selectedId" :scroll-signal="scrollSignal" @image="selectedImage=$event" />
          <StaffReply :model-value="humanInput" :busy="busy" :resolved="conversation.lifecycle !== 'open'" :can-reply="conversation.processing_owner === 'human_review' && detail.review?.status === 'open'" :stale="humanStale" :historical="conversation.mode === 'historical_replay'" :risks="detail.active_risks" @update:model-value="setHuman" @acknowledge="acknowledgeHuman" @save="saveHuman" @send="completeHuman" />
        </template>
        <ElEmpty v-else :description="selectedId ? '会话读取失败，请刷新重试' : '选择客户会话查看邮件往来'" :image-size="100" class="flex-1" />
      </section>
    </div>
    <AgentAdviceDrawer v-model="adviceOpen" :snapshot="snapshot" :can-adopt="Boolean(currentAdvice)" :loading="adviceLoading" :error="adviceError" @adopt="adopt" />
    <ImageEvidenceDrawer v-if="detail" :image="selectedImage" :conversation="detail.conversation" @close="selectedImage=null" @changed="refreshCurrent" />
  </div>
</template>
<script setup lang="ts">
  import { computed, nextTick, onActivated, onMounted, ref, watch } from 'vue'
  import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
  import { ElMessageBox } from 'element-plus'
  import { useMailWorkbench } from '@/composables/useMailWorkbench'
  import { useConversationAdvice } from '@/composables/use-conversation-advice'
  import { useConversationEvents } from '@/composables/useConversationEvents'
  import MailConversationList from '@/components/mail-agent/MailConversationList.vue'
  import MessageTimeline from '@/components/mail-agent/MessageTimeline.vue'
  import StaffReply from '@/components/mail-agent/StaffReply.vue'
  import AgentAdviceDrawer from '@/components/mail-agent/AgentAdviceDrawer.vue'
  import ImageEvidenceDrawer from '@/components/mail-agent/ImageEvidenceDrawer.vue'
  import type { ImageAttachment } from '@/api/attachment-contract'
  import { conversationState, modeLabel } from '@/components/mail-agent/mail-labels'
  import { readingPositions } from '@/composables/mail-reading-state'
  defineOptions({name:'MailWorkbench'})
  const route=useRoute(), router=useRouter(), work=useMailWorkbench()
  const { items, selectedId, state, page, nextCursor, listLoading, listError, detail, conversation, detailLoading, detailError, busy, actionError, actionNotice, humanInput, humanStale, scrollSignal, refreshList, refreshDetail, filter, paginate, setHuman, acknowledgeHuman, takeover, saveHuman, completeHuman, close }=work
  const { open:adviceOpen, snapshot, current:currentAdvice, loading:adviceLoading, error:adviceError, refresh:refreshAdvice, adopt }=useConversationAdvice(work)
  const timeline=ref<InstanceType<typeof MessageTimeline>>(), selectedImage=ref<ImageAttachment|null>(null)
  const roundCount=computed(()=>new Set(detail.value?.runs.map(item=>item.processing_cycle_id)).size)
  const focusedMessage=computed(()=>detail.value?.messages.find(item=>item.id===route.query.message_id))
  const statusNote=computed(()=>conversation.value?.lifecycle==='resolved' ? '已人工结案，后续来信只登记' : conversation.value?.persistent_human ? '客服持续主导 · Agent 只提供内部建议和草稿' : '按本轮权限处理')
  const events=useConversationEvents(conversation,async()=>{await refreshDetail();await refreshList();await refreshAdvice()})
  function savePosition(){const node=timeline.value?.$el as HTMLElement|undefined;if(node)readingPositions[selectedId.value]=node.scrollTop}
  async function restorePosition(){
    await nextTick();await nextTick()
    const node=timeline.value?.$el as HTMLElement|undefined;if(!node)return
    const index=detail.value?.messages.findIndex(item=>item.id===focusedMessage.value?.id)??-1
    const article=index>=0?node.querySelectorAll('article')[index]:undefined
    node.scrollTop=article?node.scrollTop+article.getBoundingClientRect().top-node.getBoundingClientRect().top-16:(readingPositions[selectedId.value]??node.scrollHeight)
  }
  function selectMail(id:string){savePosition();void router.replace({path:'/workbench',query:{conversation_id:id}})}
  async function synchronize(){
    if(route.path!=='/workbench')return
    const id=typeof route.query.conversation_id==='string'?route.query.conversation_id:selectedId.value
    if(id&&id!==selectedId.value){savePosition();await work.select(id)}else if(id)await refreshDetail()
    await refreshAdvice();await restorePosition()
  }
  watch(()=>[route.query.conversation_id,route.query.message_id],synchronize)
  watch(selectedId,()=>{selectedImage.value=null})
  watch(detail,()=>{if(selectedImage.value)selectedImage.value=detail.value?.messages.flatMap(item=>item.attachments??[]).find(item=>item.attachment_id===selectedImage.value?.attachment_id)??null})
  onBeforeRouteLeave(savePosition)
  onActivated(()=>{void synchronize();events.reconnect()})
  onMounted(async()=>{await refreshList();if(!route.query.conversation_id&&!selectedId.value&&items.value[0])await router.replace({path:'/workbench',query:{conversation_id:items.value[0].id}});await synchronize()})
  async function refreshCurrent(){await refreshDetail(true);await refreshAdvice();if(!detailError.value)events.reconnect()}
  async function showAdvice(){adviceOpen.value=true;await refreshAdvice()}
  function openRuns(runId?:string){savePosition();void router.push({path:'/agent-runs',query:{conversation_id:selectedId.value,run_id:runId}})}
  async function confirmClose(){const id=selectedId.value,version=conversation.value?.row_version;try{await ElMessageBox.confirm('确认问题已解决？结案会停止本轮任务，后续客户来信只登记，不自动重开。','人工确认结案',{confirmButtonText:'确认结案',cancelButtonText:'取消'});if(route.path!=='/workbench'||id!==selectedId.value||version!==conversation.value?.row_version){actionError.value='会话已变化，请核对后重新结案。';return}await close()}catch{/* 保留当前状态 */}}
</script>
<style scoped>
  .mail-layout {height:min(850px,max(650px,calc(100vh - 220px)));}
  @media(max-width:850px){.mail-layout{flex-direction:column;height:auto;}.mail-layout>section{min-height:650px;}}
</style>
