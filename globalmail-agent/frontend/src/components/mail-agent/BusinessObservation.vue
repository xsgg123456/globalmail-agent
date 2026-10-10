<template>
  <section class="p-3 rounded-md border-d mb-3">
    <div class="flex-cb flex-wrap gap-2 mb-2"><h4 class="text-sm font-medium">{{ titles[tool.name] ?? tool.name }}</h4><ElTag v-if="result.simulation === true" size="small" type="warning" effect="plain">模拟业务数据</ElTag></div>
    <p class="text-xs text-g-700 mb-3">{{ formatMailTime(String(result.observed_at ?? tool.created_at)) }} · {{ result.source_kind ?? '来源未记录' }}</p>
    <p v-if="result.status !== 'ok'" class="text-sm mb-2">{{ result.reason_code ?? tool.reason_code ?? tool.status }}</p>
    <dl class="space-y-2 text-sm"><div v-for="item in fields.slice(0,24)" :key="item.key" class="flex justify-between gap-4"><dt class="text-g-700 shrink-0">{{ item.label }}</dt><dd class="text-right break-all">{{ item.value }}</dd></div></dl>
    <p v-if="fields.length > 24" class="text-xs text-g-700 mt-3">其余字段可在完整回执中查看。</p>
    <ElCollapse class="mt-3"><ElCollapseItem title="查看完整查询回执" name="raw"><pre class="text-xs leading-relaxed whitespace-pre-wrap break-all">{{ pretty(tool.result) }}</pre></ElCollapseItem></ElCollapse>
  </section>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  import type { AgentToolCall } from '@/api/agent-run-contract'
  import { asRecord, pretty } from '@/components/agent-runtime/presentation'
  import { observationFields } from './observation-fields'
  import { formatMailTime } from './mail-labels'
  const props = defineProps<{tool:AgentToolCall}>()
  const result = computed(()=>asRecord(props.tool.result))
  const fields = computed(()=>observationFields(result.value.data))
  const titles:Record<string,string> = {get_order_snapshot:'订单查询',get_after_sales_context:'已有售后记录',get_shipment_status:'物流查询',get_item_availability:'库存查询',get_operation_status:'已有处理进度',search_reference:'知识与政策依据'}
</script>
