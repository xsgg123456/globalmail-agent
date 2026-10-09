<template>
  <section aria-label="工具调用">
    <h4 class="text-sm font-medium mb-2">工具调用 · {{ tools.length }} 次</h4>
    <p v-if="!tools.length" class="text-sm text-g-700">本轮尚无工具调用记录。</p>
    <ElCollapse v-else>
      <ElCollapseItem
        v-for="tool in tools"
        :key="tool.id"
        :name="tool.id"
        :title="`${tool.name} · ${statuses[tool.status] || tool.status}`"
      >
        <p class="text-xs text-g-700 mb-2">调用时间：{{ formatMailTime(tool.created_at) }}</p>
        <p v-if="tool.reason_code" class="text-sm break-words mb-2">原因：{{ tool.reason_code }}</p>
        <template v-if="tool.result">
          <p class="text-sm mb-2">{{ businessStatus(tool.result) }}</p>
          <p class="text-xs text-g-700 mb-2"
            >来源：{{ sourceLabel(tool.result.source_kind)
            }}{{ tool.result.simulation ? ' · 模拟资料' : '' }} ·
            {{ formatMailTime(tool.result.observed_at) }}</p
          >
        </template>
        <p v-else class="text-sm text-g-700 mb-2">尚无已保存的工具结果。</p>
        <details class="text-xs text-g-700">
          <summary>参数与完整结果</summary>
          <p class="mt-2">这是调用时的历史记录；当前引用资格请打开引用区核验。</p>
          <pre class="font-inherit whitespace-pre-wrap break-words mt-2">{{
            jsonText({ arguments: tool.arguments, result: tool.result })
          }}</pre>
        </details>
      </ElCollapseItem>
    </ElCollapse>
  </section>
</template>
<script setup lang="ts">
  import type { AgentToolCall } from '@/api/agent-run-contract'
  import { businessStatus, sourceLabel } from './business-format'
  import { formatMailTime } from './mail-labels'
  import { jsonText } from './agent-run-format'
  defineProps<{ tools: AgentToolCall[] }>()
  const statuses: Record<string, string> = {
    ok: '成功',
    completed: '完成',
    running: '执行中',
    failed: '失败',
    error: '错误',
    denied: '拒绝',
    empty: '无结果',
    needs_input: '待补信息',
    unavailable: '不可用',
    unknown: '结果未知',
    conflict: '冲突'
  }
</script>
