<template>
  <div class="space-y-4 min-w-0">
    <div class="text-xs text-g-700 space-y-2">
      <p class="break-all">运行：{{ run.id }}</p>
      <p class="break-all"
        >处理轮次：{{ run.processing_cycle_id }} · 输入版本 {{ run.input_revision }}</p
      >
      <p>开始：{{ formatMailTime(run.started_at) }}</p>
      <p>结束：{{ formatMailTime(run.finished_at) }}</p>
    </div>
    <ElAlert
      v-if="run.error_code"
      :title="runError(run.error_code)"
      type="warning"
      :closable="false"
      show-icon
    />
    <ElAlert
      v-if="run.status === 'budget_exhausted'"
      title="本轮预算已耗尽"
      description="已保留工具与材料；等待新来信后建立新一轮，重试不能重置预算。"
      type="warning"
      :closable="false"
      show-icon
    />
    <p v-if="['stopped', 'interrupted'].includes(run.status)" class="text-xs text-g-700"
      >刷新会恢复记录；恢复处理需显式重试，沿用原轮剩余额度。</p
    >
    <ElAlert v-if="error" :title="error" type="error" :closable="false" show-icon />
    <ElButton v-if="error" size="small" :loading="loading" @click="$emit('refresh')"
      >重试读取处理记录</ElButton
    >
    <ElSkeleton v-if="loading" :rows="4" animated />
    <template v-else-if="record && !error">
      <ElAlert
        v-if="legacyProtocol"
        title="历史任务协议验证"
        description="这次运行发生在模型接入前，没有 AI 回复。"
        type="info"
        :closable="false"
      />
      <p v-else-if="run.outcome" class="text-sm font-medium break-words">{{
        outcomeLabel(run.outcome)
      }}</p>
      <UnderstandingPanel v-if="record.understanding" :result="record.understanding" />
      <p v-else-if="!legacyProtocol" class="text-sm text-g-700">本轮尚无已保存的理解结果。</p>
      <AgentToolRecords :tools="record.tools" />
      <section aria-label="运行引用" class="space-y-2">
        <h4 class="text-sm font-medium">引用 · {{ record.references.length }} 份</h4>
        <p v-if="!record.references.length" class="text-sm text-g-700">本轮尚无知识引用。</p>
        <article
          v-for="item in record.references"
          :key="item.reference.evidence_id"
          class="border-d rounded p-3 space-y-2"
        >
          <p class="text-sm break-words"
            >{{ item.reference.title }} · 第 {{ item.reference.version_number }} 版</p
          >
          <ElTag size="small" :type="item.eligible ? 'success' : 'warning'">{{
            item.eligible ? '当前有效' : '已停用或不适用'
          }}</ElTag>
          <p v-if="!item.eligible" class="text-xs text-g-700 break-words">{{ item.reason }}</p>
          <div
            ><ElButton
              size="small"
              @click="selection = { runId: run.id, referenceId: item.reference.evidence_id }"
              >查看引用与来源</ElButton
            ></div
          >
        </article>
      </section>
      <section v-if="record.artifacts.length" aria-label="本轮结果" class="space-y-3">
        <h4 class="text-sm font-medium">本轮结果</h4>
        <article
          v-for="artifact in record.artifacts"
          :key="artifact.id"
          class="border-d rounded p-3 space-y-2"
        >
          <p class="text-sm font-medium">{{ outcomeLabel(artifact.outcome) }}</p>
          <p class="text-xs text-g-700"
            >{{ artifact.language || '语言未记录' }} · {{ formatMailTime(artifact.created_at) }}</p
          >
          <p v-if="artifact.body" class="text-sm whitespace-pre-wrap break-words">{{
            artifact.body
          }}</p>
          <p v-else class="text-sm text-g-700">本轮没有回复正文。</p>
          <p v-if="artifact.citation_ids.length" class="text-xs text-g-700 break-all"
            >依据引用：{{ artifact.citation_ids.join('、') }}</p
          >
        </article>
      </section>
      <section v-if="record.waits.length" aria-label="等待条件" class="space-y-2">
        <h4 class="text-sm font-medium">等待条件</h4>
        <p v-for="(wait, index) in record.waits" :key="index" class="text-sm break-words"
          >{{ waitLabels[wait.condition_type] || wait.condition_type }} · {{ wait.status
          }}<span v-if="wait.operation_id"> · {{ wait.operation_id }}</span></p
        >
      </section>
      <section aria-label="本地用量" class="border-t-d pt-3 text-xs text-g-700 space-y-2">
        <h4 class="text-sm font-medium text-g-900">本轮累计本地用量</h4>
        <p
          >模型请求 {{ record.usage.model_requests }} / {{ record.usage.limits.model_requests }} ·
          工具 {{ record.usage.tool_calls }} / {{ record.usage.limits.tool_calls }}</p
        >
        <p>实际 tokens：{{ usageTokens(record.usage) }}</p>
        <p
          >本轮预算计数 {{ record.usage.reserved_tokens.toLocaleString('zh-CN') }} /
          {{ record.usage.limits.tokens.toLocaleString('zh-CN') }} tokens</p
        >
        <p
          >活动耗时 {{ (record.usage.active_ms / 1000).toFixed(1) }} /
          {{ record.usage.limits.active_ms / 1000 }} 秒</p
        >
        <p v-if="record.usage.unknown_requests"
          >{{ record.usage.unknown_requests }} 次请求缺少实际 usage，保留保守预算占用。</p
        >
        <p>费用：{{ usageCost(record.usage) }} · Langfuse 观测尚未接入</p>
        <p>同一处理轮次的重试共享预算，当前数据来自本地持久记录。</p>
      </section>
    </template>
    <ReferenceDrawer :selection="selection" @close="selection = null" />
  </div>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import type { AgentRun } from '@/api/mail-agent-contract'
  import type { AgentRunDetail } from '@/api/agent-run-contract'
  import type { ReferenceSelection } from '@/composables/useRunReference'
  import { formatMailTime } from './mail-labels'
  import { runError, outcomeLabel, usageTokens, usageCost, waitLabels } from './agent-run-format'
  import UnderstandingPanel from './UnderstandingPanel.vue'
  import AgentToolRecords from './AgentToolRecords.vue'
  import ReferenceDrawer from './ReferenceDrawer.vue'
  const props = defineProps<{
    run: AgentRun
    record?: AgentRunDetail
    loading: boolean
    error?: string
  }>()
  defineEmits<{ refresh: [] }>()
  const selection = ref<ReferenceSelection | null>(null)
  const legacyProtocol = computed(
    () => props.run.outcome === 'protocol_verified_model_not_connected'
  )
  watch(
    () => props.record,
    () => {
      if (selection.value) selection.value = { ...selection.value }
    }
  )
</script>
