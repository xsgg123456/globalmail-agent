<template>
  <ElCollapse>
    <ElCollapseItem
      v-for="group in groups"
      :key="group.kind"
      :name="group.kind"
      :title="`${group.label}（${group.records.length}）`"
    >
      <p v-if="!group.records.length" class="text-xs text-g-700"
        >当前没有可见记录，不能据此认定已执行。</p
      >
      <ElCard v-for="(record, index) in group.records" :key="index" shadow="never" class="mb-3">
        <p class="text-sm font-medium mb-2">{{ recordTitle(record, group.kind) }}</p>
        <dl class="text-xs leading-relaxed">
          <div
            v-for="(row, rowIndex) in recordFields(record, group.kind)"
            :key="rowIndex"
            class="mb-2"
          >
            <dt class="text-g-700">{{ row.label }}</dt
            ><dd class="break-all">{{ row.value }}</dd>
          </div>
        </dl>
      </ElCard>
    </ElCollapseItem>
  </ElCollapse>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  import type { BusinessRecord } from '@/api/business-contract'
  import { recordFields, recordTitle } from './business-records'
  const props = defineProps<{
    records: {
      operations: BusinessRecord[]
      executions: BusinessRecord[]
      shipments: BusinessRecord[]
      returns: BusinessRecord[]
    }
  }>()
  const groups = computed(() => [
    { kind: 'operations', label: '内部申请', records: props.records.operations },
    { kind: 'executions', label: '执行回执', records: props.records.executions },
    { kind: 'shipments', label: '原件、退件与补发件物流', records: props.records.shipments },
    { kind: 'returns', label: '退件与质检', records: props.records.returns }
  ])
</script>
