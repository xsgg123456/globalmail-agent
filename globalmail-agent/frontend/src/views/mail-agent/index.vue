<template>
  <div>
    <RuntimeStatus />
    <div
      ref="workbench"
      class="page-content flex !p-0 overflow-hidden"
      :class="{ 'flex-col': narrow }"
      :style="{ height: narrow ? 'auto' : 'min(850px, max(600px, calc(100vh - 270px)))' }"
    >
      <ConversationList
        class="w-[260px]"
        :class="{ 'w-full! max-h-[380px] border-b-d': narrow }"
        :items="items"
        :selected-id="selectedId"
        :mode="mode"
        :state="state"
        :loading="listLoading"
        :busy="busy"
        :error="listError"
        :page="page"
        :has-previous="page > 1"
        :has-next="Boolean(nextCursor)"
        @select="select"
        @mode="filter('mode', $event)"
        @state="filter('state', $event)"
        @create="openDialog('create')"
        @import="openDialog('import')"
        @refresh="refreshList"
        @previous="paginate(false)"
        @next="paginate(true)"
      >
        <template #scenario
          ><BusinessScenarioLauncher :disabled="busy" @created="selectScenario"
        /></template>
      </ConversationList>
      <section
        class="box-border flex-1 min-w-0 flex flex-col"
        :class="{ 'min-h-[600px]': narrow }"
        aria-label="邮件往来"
      >
        <div class="flex-cb flex-wrap gap-3 p-4">
          <div class="min-w-0">
            <h2 class="text-base font-medium break-words">{{
              detail?.conversation.subject || '邮件往来'
            }}</h2>
            <p v-if="detail" class="text-xs text-g-700 mt-2 break-all"
              >{{ detail.conversation.sender_key }} · {{ modeLabel(detail.conversation.mode) }} ·
              {{ conversationState(detail.conversation) }}</p
            >
          </div>
          <div class="flex flex-wrap gap-2">
            <ElButton v-if="selectedId" :loading="detailLoading" @click="refreshCurrent"
              >刷新会话</ElButton
            >
            <ElButton v-if="compact && detail" @click="drawer = true">处理详情与人审</ElButton>
          </div>
        </div>
        <ElAlert
          v-if="detailError"
          :title="detailError"
          type="error"
          :closable="false"
          show-icon
          class="mx-4 mb-3 max-w-[calc(100%-32px)]"
        />
        <ElAlert
          v-if="actionError"
          :title="actionError"
          type="error"
          :closable="false"
          show-icon
          class="mx-4 mb-3 max-w-[calc(100%-32px)]"
        />
        <ElAlert
          v-if="actionNotice"
          :title="actionNotice"
          type="success"
          :closable="true"
          show-icon
          class="mx-4 mb-3 max-w-[calc(100%-32px)]"
          @close="actionNotice = ''"
        />
        <ElSkeleton v-if="detailLoading && !detail" :rows="6" animated class="p-4" />
        <template v-else-if="detail">
          <MessageTimeline
            @image="selectedImage = $event"
            :messages="detail.messages"
            :conversation-id="detail.conversation.id"
            :scroll-signal="scrollSignal"
            :class="{ 'max-h-[500px]': narrow }"
          />
          <MessageComposer
            :conversation-id="detail.conversation.id"
            :model-value="incomingInput"
            :historical="detail.conversation.mode === 'historical_replay'"
            :replay="detail.replay"
            :busy="busy"
            :active-run="activeRun"
            :human-review="detail.conversation.processing_owner === 'human_review'"
            :resolved="detail.conversation.lifecycle === 'resolved'"
            @update:model-value="setIncoming"
            @submit="append"
            @next="nextReplay"
          />
        </template>
        <ElEmpty
          v-else
          :description="
            selectedId
              ? '会话读取失败，请点击刷新会话重试'
              : '选择会话，或新建模拟会话、导入历史案例'
          "
          :image-size="100"
          class="flex-1"
        />
      </section>
      <section
        v-if="!compact"
        class="w-[360px] shrink-0 overflow-y-auto border-l-d min-w-0"
        aria-label="Agent 处理记录"
      >
        <AgentProcessPanel
          v-if="detail"
          v-bind="panelProps"
          @human-input="setHuman"
          @takeover="takeover"
          @save="saveHuman"
          @complete="completeHuman"
          @close="confirmClose"
          @stop="stop"
          @retry="retry"
          @acknowledge="acknowledgeHuman"
          @business-changed="refreshCurrent"
        />
        <ElEmpty v-else description="选择会话后查看任务与人审" :image-size="70" />
      </section>
    </div>
    <ElDrawer
      v-model="drawer"
      title="Agent 处理记录与人审"
      size="min(420px, 100vw)"
      destroy-on-close
    >
      <AgentProcessPanel
        v-if="detail"
        v-bind="panelProps"
        @human-input="setHuman"
        @takeover="takeover"
        @save="saveHuman"
        @complete="completeHuman"
        @close="confirmClose"
        @stop="stop"
        @retry="retry"
        @acknowledge="acknowledgeHuman"
        @business-changed="refreshCurrent"
      />
    </ElDrawer>
    <ConversationDialog
      v-model="dialogVisible"
      :kind="dialogKind"
      :busy="busy"
      :submit-command="createOrImport"
    />
    <ImageEvidenceDrawer v-if="detail" :image="selectedImage" :conversation="detail.conversation"
      @close="selectedImage = null" @changed="refreshCurrent" />
  </div>
</template>
<script setup lang="ts">
  import { computed, onMounted, ref, watch } from 'vue'
  import ImageEvidenceDrawer from '@/components/mail-agent/ImageEvidenceDrawer.vue'
  import type { ImageAttachment } from '@/api/attachment-contract'
  import { useElementSize } from '@vueuse/core'
  import { ElMessageBox } from 'element-plus'
  import RuntimeStatus from '@/components/business/runtime-status.vue'
  import ConversationList from '@/components/mail-agent/ConversationList.vue'
  import MessageTimeline from '@/components/mail-agent/MessageTimeline.vue'
  import MessageComposer from '@/components/mail-agent/MessageComposer.vue'
  import AgentProcessPanel from '@/components/mail-agent/AgentProcessPanel.vue'
  import ConversationDialog from '@/components/mail-agent/ConversationDialog.vue'
  import BusinessScenarioLauncher from '@/components/mail-agent/BusinessScenarioLauncher.vue'
  import { conversationState, modeLabel } from '@/components/mail-agent/mail-labels'
  import { useMailWorkbench } from '@/composables/useMailWorkbench'
  import { useConversationEvents } from '@/composables/useConversationEvents'
  defineOptions({ name: 'MailWorkbench' })
  const {
    items,
    selectedId,
    mode,
    state,
    page,
    nextCursor,
    listLoading,
    listError,
    detail,
    detailLoading,
    detailError,
    busy,
    actionError,
    actionNotice,
    incomingInput,
    humanInput,
    humanStale,
    acknowledgeHuman,
    scrollSignal,
    conversation,
    filter,
    paginate,
    select,
    refreshList,
    refreshDetail,
    createOrImport,
    setIncoming,
    setHuman,
    append,
    nextReplay,
    takeover,
    saveHuman,
    completeHuman,
    close,
    stop,
    retry
  } = useMailWorkbench()
  const { state: eventState, reconnect } = useConversationEvents(conversation, async () => {
    await refreshDetail()
    await refreshList()
  })
  const workbench = ref<HTMLElement>()
  const { width } = useElementSize(workbench)
  const compact = computed(() => width.value < 1024)
  const narrow = computed(() => width.value < 640)
  const drawer = ref(false)
  const selectedImage = ref<ImageAttachment | null>(null)
  watch(selectedId, () => { selectedImage.value = null })
  watch(detail, (snapshot) => {
    const id = selectedImage.value?.attachment_id
    if (id) selectedImage.value = snapshot?.messages.flatMap((message) => message.attachments ?? []).find((image) => image.attachment_id === id) ?? null
  })
  const dialogVisible = ref(false)
  const dialogKind = ref<'create' | 'import'>('create')
  const activeRun = computed(() =>
    Boolean(detail.value?.runs.some((run) => ['queued', 'running'].includes(run.status)))
  )
  const panelProps = computed(() => ({
    detail: detail.value!,
    humanInput: humanInput.value,
    humanStale: humanStale.value,
    busy: busy.value,
    eventState: eventState.value
  }))
  function openDialog(kind: 'create' | 'import') {
    dialogKind.value = kind
    dialogVisible.value = true
  }
  async function refreshCurrent() {
    await refreshDetail(true)
    if (!detailError.value) reconnect()
  }
  async function selectScenario(id: string) {
    await filter('mode', '')
    await filter('state', '')
    await select(id)
    actionNotice.value = '初始业务资料已载入独立会话，可以核对订单与售后条件。'
  }
  async function confirmClose() {
    try {
      await ElMessageBox.confirm(
        '确认客户问题已解决？结案会停止当前任务。之后客户新来信会重开原会话。',
        '人工确认结案',
        { confirmButtonText: '确认结案', cancelButtonText: '取消', type: 'warning' }
      )
      await close()
    } catch {
      /* 用户取消，保持会话状态。 */
    }
  }
  onMounted(refreshList)
</script>
