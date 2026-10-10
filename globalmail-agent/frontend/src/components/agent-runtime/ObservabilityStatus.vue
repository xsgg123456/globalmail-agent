<template>
  <div class="flex items-center flex-wrap gap-3 mt-3 text-xs text-g-700" aria-label="本轮运行追踪">
    <span v-if="loading">运行追踪状态读取中…</span>
    <span v-else-if="error" role="status">{{ error }}</span>
    <template v-else-if="record">
      <ElTag :type="record.export_status === 'degraded' ? 'warning' : 'info'" size="small" effect="plain">{{ labels[record.export_status] }}</ElTag>
      <a v-if="record.export_status === 'exported' && record.trace_url" :href="record.trace_url" target="_blank" rel="noopener noreferrer" class="text-theme">打开本轮 Langfuse 追踪 ↗</a>
      <span v-if="record.export_status === 'degraded'">观测导出暂不可用，业务处理不受影响。</span>
    </template>
    <ElButton link :disabled="loading" @click="refresh">刷新追踪状态</ElButton>
  </div>
</template>
<script setup lang="ts">
  import { toRef, onActivated, onDeactivated, onScopeDispose } from 'vue'
  import { useRunObservability } from '@/composables/use-run-observability'
  import type { ExportStatus } from '@/api/observability-api'
  const props = defineProps<{ runId: string; revision: unknown }>()
  const { record, loading, error, refresh, suspend, activate, dispose } = useRunObservability(toRef(props, 'runId'), toRef(props, 'revision'))
  const labels: Record<ExportStatus, string> = {
    disabled: '观测未启用', local_only: '仅本地记录', pending: '追踪导出中',
    exported: '运行追踪已导出', degraded: '观测已降级', revoked: '追踪已撤销'
  }
  onActivated(activate)
  onDeactivated(suspend)
  onScopeDispose(dispose)
</script>
