<template>
  <div class="p-4 min-w-0">
    <div class="flex-cb gap-2 mb-3"
      ><h2 class="text-base font-medium">处理详情</h2
      ><ElTag type="info" size="small">本机模拟</ElTag></div
    >
    <ElAlert
      title="模型在 Phase 7 接入"
      description="当前持久任务只验证排队、停止与恢复协议，不生成 AI 回复，也不向真实邮箱发信。"
      type="info"
      :closable="false"
      show-icon
      class="mb-4"
    />
    <div class="flex flex-wrap gap-2 mb-3">
      <ElTag :type="detail.conversation.processing_owner === 'human_review' ? 'warning' : 'info'">{{
        conversationState(detail.conversation)
      }}</ElTag>
      <ElTag type="info">{{ modeLabel(detail.conversation.mode) }}</ElTag>
    </div>
    <p class="text-xs text-g-700 mb-4" aria-live="polite">事件订阅：{{ eventState }}</p>
    <section aria-label="Agent 任务" class="mb-5">
      <h3 class="text-sm font-medium mb-3">Agent 持久任务</h3>
      <ElEmpty v-if="!detail.runs.length" description="尚无任务记录" :image-size="50" />
      <template v-else>
        <div class="flex flex-wrap gap-2 mb-3">
          <ElButton
            v-if="activeRun"
            type="warning"
            plain
            :loading="busy"
            @click="$emit('stop', activeRun.id)"
            >停止当前任务</ElButton
          >
          <ElButton v-if="retryRun && canRetry" :loading="busy" @click="$emit('retry', retryRun.id)"
            >显式重试</ElButton
          >
        </div>
        <ElCollapse>
          <ElCollapseItem
            v-for="run in detail.runs"
            :key="run.id"
            :name="run.id"
            :title="`${runLabels[run.status]} · 第 ${run.attempt_no} 次尝试`"
          >
            <p class="text-xs text-g-700 mb-2 break-all">任务：{{ run.id }}</p>
            <p class="text-xs text-g-700 mb-2">开始：{{ formatMailTime(run.started_at) }}</p>
            <p class="text-xs text-g-700 mb-2">结束：{{ formatMailTime(run.finished_at) }}</p>
            <p v-if="run.status === 'completed'" class="text-sm"
              >任务协议已验证；模型尚未接入，没有 AI 邮件。</p
            >
            <p v-if="run.error_code" class="text-sm">{{ runError(run.error_code) }}</p>
            <p
              v-if="run.status === 'stopped' || run.status === 'interrupted'"
              class="text-xs text-g-700 mt-2"
              >需显式重试，刷新或重新订阅不会恢复旧任务。</p
            >
          </ElCollapseItem>
        </ElCollapse>
      </template>
    </section>
    <section
      v-if="detail.conversation.mode === 'historical_replay'"
      class="border-t-d pt-4 mb-5"
      aria-label="独立对照结果"
    >
      <h3 class="text-sm font-medium mb-2">AI 对照回复</h3>
      <p class="text-sm text-g-700">模型尚未接入，当前没有 AI 对照结果。</p>
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
    <BusinessDetails :key="detail.conversation.id" :context="detail.conversation" />
    <HumanReviewPanel
      :conversation="detail.conversation"
      :review="detail.review"
      :history="detail.human_history"
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
  import { computed } from 'vue'
  import type { ConversationDetail } from '@/api/mail-agent-contract'
  import type { HumanInput } from './mail-inputs'
  import HumanReviewPanel from './HumanReviewPanel.vue'
  import BusinessDetails from './BusinessDetails.vue'
  import { conversationState, modeLabel, runLabels, formatMailTime } from './mail-labels'
  const props = defineProps<{
    detail: ConversationDetail
    humanInput: HumanInput
    humanStale: boolean
    busy: boolean
    eventState: string
  }>()
  defineEmits<{
    humanInput: [value: HumanInput]
    takeover: []
    save: []
    complete: []
    close: []
    acknowledge: []
    stop: [id: string]
    retry: [id: string]
  }>()
  const latestRun = computed(() => props.detail.runs.at(-1))
  const activeRun = computed(() =>
    latestRun.value && ['queued', 'running'].includes(latestRun.value.status)
      ? latestRun.value
      : null
  )
  const retryRun = computed(() =>
    latestRun.value &&
    ['failed', 'stopped', 'interrupted', 'budget_exhausted'].includes(latestRun.value.status)
      ? latestRun.value
      : null
  )
  const canRetry = computed(
    () =>
      props.detail.conversation.lifecycle === 'open' &&
      props.detail.conversation.processing_owner === 'agent' &&
      !activeRun.value
  )
  const errors: Record<string, string> = {
    model_not_connected: '模型尚未接入。',
    lease_expired: '任务租约失效，运行已中断。',
    process_interrupted: '本地进程中断，需显式重试。',
    stopped_by_user: '用户已停止任务。',
    worker_interrupted: '本地进程中断，需显式重试。',
    user_stopped: '用户已停止任务。'
  }
  const runError = (code: string) =>
    errors[code] ?? '任务未完成，已保存状态；请核对会话后显式重试。'
</script>
