<template>
  <div class="space-y-3">
    <ElAlert
      title="保存为政策草稿。数值和证据要求会重新生成中文说明；当前生效政策不会因此改变。"
      type="info"
      :closable="false"
    />
    <ElFormItem v-for="field in fields" :key="field.group" :label="field.label">
      <ElInputNumber
        :model-value="numberAt(field.group, field.key)"
        :min="1"
        :max="field.max"
        :precision="0"
        @update:model-value="setNumber(field.group, field.key, $event)"
      />
      <span class="ml-2">{{ field.unit }}</span>
    </ElFormItem>
    <ElFormItem label="部分退款上限">
      <ElInputNumber
        :model-value="numberAt('refund', 'partial_offer_max_basis_points') / 100"
        :min="0.01"
        :max="100"
        :precision="2"
        @update:model-value="
          setNumber(
            'refund',
            'partial_offer_max_basis_points',
            $event === undefined ? undefined : Math.round($event * 100)
          )
        "
      />
      <span class="ml-2">% 的受影响实付份额</span>
    </ElFormItem>
    <ElCollapse v-if="requirements.length">
      <ElCollapseItem title="逐项证据要求" name="evidence">
        <div v-for="rule in requirements" :key="rule.code" class="mb-4">
          <p class="font-medium mb-2">{{ rule.label }}</p>
          <ElSelect
            multiple
            :model-value="rule.kinds"
            aria-label="允许的证据类型"
            class="!w-full"
            @update:model-value="setKinds(rule.code, $event)"
          >
            <ElOption
              v-for="kind in kinds.filter(
                (k) =>
                  !ledger.has(rule.code) ||
                  !['customer_statement', 'visual_observation'].includes(k.id)
              )"
              :key="kind.id"
              :label="kind.label"
              :value="kind.id"
            />
          </ElSelect>
        </div>
      </ElCollapseItem>
    </ElCollapse>
  </div>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  const props = defineProps<{ modelValue: Record<string, unknown> }>()
  const emit = defineEmits<{ 'update:modelValue': [Record<string, unknown>] }>()
  const record = (value: unknown): value is Record<string, unknown> =>
    typeof value === 'object' && value !== null && !Array.isArray(value)
  const fields = [
    {
      group: 'return',
      key: 'window_days_after_delivery',
      label: '签收后退货窗口',
      max: 3650,
      unit: '天'
    },
    {
      group: 'replacement',
      key: 'defect_window_days_after_delivery',
      label: '质量换货窗口',
      max: 3650,
      unit: '天'
    },
    {
      group: 'spare_part',
      key: 'defect_window_days_after_delivery',
      label: '质量补件窗口',
      max: 3650,
      unit: '天'
    },
    {
      group: 'logistics',
      key: 'stale_tracking_days',
      label: '轨迹未更新查件阈值',
      max: 365,
      unit: '天'
    }
  ]
  const kinds = [
    { id: 'tool_fact', label: '工具查询事实' },
    { id: 'verified_fixture', label: '已核对的受控资料' },
    { id: 'human_decision', label: '人工决定' },
    { id: 'customer_statement', label: '客户陈述' },
    { id: 'visual_observation', label: '图片观察' }
  ]
  const ledger = new Set([
    'order_identity',
    'paid_amount',
    'quantity',
    'customer_choice',
    'address',
    'warehouse_receipt',
    'warehouse_inspection',
    'compatibility',
    'inventory',
    'compensation_ledger',
    'delivery_date'
  ])
  function numberAt(group: string, key: string) {
    const row = props.modelValue[group]
    return record(row) && typeof row[key] === 'number' ? row[key] : 0
  }
  function change(group: string, key: string, value: unknown) {
    const row = props.modelValue[group]
    if (record(row))
      emit('update:modelValue', { ...props.modelValue, [group]: { ...row, [key]: value } })
  }
  function setNumber(group: string, key: string, value: number | undefined) {
    change(group, key, value)
  }
  const requirements = computed(() => {
    const rows = props.modelValue.evidence_requirements
    return record(rows)
      ? Object.entries(rows).flatMap(([code, row]) =>
          record(row) && typeof row.label === 'string' && Array.isArray(row.allowed_kinds)
            ? [
                {
                  code,
                  label: row.label,
                  kinds: row.allowed_kinds.filter(
                    (kind): kind is string => typeof kind === 'string'
                  )
                }
              ]
            : []
        )
      : []
  })
  function setKinds(code: string, values: string[]) {
    const rows = props.modelValue.evidence_requirements
    if (!record(rows) || !record(rows[code])) return
    emit('update:modelValue', {
      ...props.modelValue,
      evidence_requirements: { ...rows, [code]: { ...rows[code], allowed_kinds: values } }
    })
  }
</script>
