<template>
  <div class="p-4 min-w-0">
    <div class="flex-cb gap-2 mb-3"
      ><h2 class="text-base font-medium">处理详情</h2
      ><ElTag type="info" size="small">本机模拟</ElTag></div
    >
    <p class="text-xs text-g-700 mb-4"
      >本地模拟，不会投递真实邮箱。回复经核验并提交后进入邮件区，过程和未发送结果保留在此处。</p
    >
    <div class="flex flex-wrap gap-2 mb-3">
      <ElTag :type="detail.conversation.processing_owner === 'human_review' ? 'warning' : 'info'">{{
        conversationState(detail.conversation)
      }}</ElTag>
      <ElTag type="info">{{ modeLabel(detail.conversation.mode) }}</ElTag>
    </div>
    <p class="text-xs text-g-700 mb-4" aria-live="polite">事件订阅：{{ eventState }}</p>
    <section aria-label="Agent 任务" class="mb-5">
      <h3 class="text-sm font-medium mb-3">Agent 运行记录</h3>
      <ElEmpty v-if="!detail.runs.length" description="尚无运行记录" :image-size="50" />
      <template v-else>
        <div v-if="activeRun || retryRun" class="flex flex-wrap gap-2 mb-3">
          <ElButton v-if="activeRun" type="warning" plain :loading="busy" @click="confirmStop"
            >停止当前任务</ElButton
          >
          <ElButton v-if="retryRun" :loading="busy" @click="$emit('retry', retryRun.id)"
            >显式重试</ElButton
          >
        </div>
        <ElCollapse v-model="expanded">
          <ElCollapseItem
            v-for="run in [...detail.runs].reverse()"
            :key="run.id"
            :name="run.id"
            :title="`${runLabels[run.status]} · 第 ${run.attempt_no} 次尝试`"
          >
            <AgentRunPanel
              v-if="expanded.includes(run.id)"
              :run="run"
              :record="records[run.id]"
              :loading="Boolean(loading[run.id])"
              :error="errors[run.id]"
              @refresh="refresh(run.id)"
            />
          </ElCollapseItem>
        </ElCollapse>
      </template>
    </section>
    <section
      v-if="detail.conversation.mode === 'historical_replay'"
      class="border-t-d pt-4 mb-5"
      aria-label="独立对照结果"
    >
      <h3 class="text-sm font-medium mb-2">历史对照结果</h3>
      <p class="text-xs text-g-700"
        >AI 对照在对应运行的“本轮结果”中查看；与真实历史客服邮件分开保存。</p
      >
      <ElCollapse v-if="detail.comparisons.length" class="mt-3">
        <ElCollapseItem
          v-for="comparison in detail.comparisons"
          :key="comparison.id"
          :name="comparison.id"
          title="人工本轮审阅 · 独立对照"
        >
          <p class="text-sm whitespace-pre-wrap break-words">{{ comparison.reply }}</p>
          <p v-if="comparison.note" class="text-sm whitespace-pre-wrap break-words mt-2"
            >备注：{{ comparison.note }}</p
          >
        </ElCollapseItem>
      </ElCollapse>
    </section>
    <CaseMemoryPanel :detail="detail" />
    <BusinessDetails :key="detail.conversation.id" :context="detail.conversation" />
    <OperationDetails :key="detail.conversation.id" :context="detail.conversation" @changed="$emit('businessChanged')" />
    <HumanReviewPanel
      :conversation="detail.conversation"
      :review="detail.review"
      :history="detail.human_history"
      :active-risks="detail.active_risks ?? []"
      :model-value="humanInput"
      :historical="detail.conversation.mode === 'historical_replay'"
      :busy="busy"
      :stale="humanStale"
      :message-count="detail.messages.length"
      @update:model-value="$emit('humanInput', $event)"
      @takeover="$emit('takeover')"
      @save="$emit('save')"
      @complete="$emit('complete')"
      @close="$emit('close')"
      @acknowledge="$emit('acknowledge')"
    />
  </div>
</template>
<script setup lang="ts">
  import { computed, onScopeDispose, toRef } from 'vue'
  import { ElMessageBox } from 'element-plus'
  import type { ConversationDetail } from '@/api/mail-agent-contract'
  import type { HumanInput } from './mail-inputs'
  import { useAgentRunDetails } from '@/composables/useAgentRunDetails'
  import HumanReviewPanel from './HumanReviewPanel.vue'
  import BusinessDetails from './BusinessDetails.vue'
  import OperationDetails from './OperationDetails.vue'
  import AgentRunPanel from './AgentRunPanel.vue'
  import CaseMemoryPanel from './CaseMemoryPanel.vue'
  import { conversationState, modeLabel, runLabels } from './mail-labels'
  import { retryableRun } from './agent-run-format'
  const props = defineProps<{
    detail: ConversationDetail
    humanInput: HumanInput
    humanStale: boolean
    busy: boolean
    eventState: string
  }>()
  const emit = defineEmits<{
    humanInput: [value: HumanInput]
    takeover: []
    save: []
    complete: []
    close: []
    acknowledge: []
    stop: [id: string]
    retry: [id: string]
    businessChanged: []
  }>()
  const { expanded, records, loading, errors, refresh, dispose } = useAgentRunDetails(
    toRef(props, 'detail')
  )
  onScopeDispose(dispose)
  const activeRun = computed(() =>
    props.detail.runs.findLast((run) => ['queued', 'running'].includes(run.status))
  )
  const retryRun = computed(() => retryableRun(props.detail))
  async function confirmStop() {
    const id = activeRun.value?.id
    if (!id || props.busy) return
    try {
      await ElMessageBox.confirm(
        '停止后不再开始新的模型调用，未提交的回复不会发送；恢复需显式重试并沿用本轮剩余预算。',
        '停止当前任务',
        { confirmButtonText: '确认停止', cancelButtonText: '取消', type: 'warning' }
      )
    } catch {
      return
    }
    if (activeRun.value?.id === id && !props.busy) emit('stop', id)
  }
</script>
