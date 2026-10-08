<template>
  <ElCollapse class="mb-3">
    <ElCollapseItem name="customer-choice" title="已取得的客户选择与地址确认">
      <p class="text-xs text-g-700 mb-3">以下来自当前可见资料；试填核对表单不会改变客户选择。</p>
      <p v-if="!data.customer_choices.length" class="text-sm mb-3">尚未取得明确的客户选择。</p>
      <ElCard
        v-for="(choice, index) in data.customer_choices"
        :key="index"
        shadow="never"
        class="mb-3"
      >
        <p class="text-sm font-medium mb-2">{{ choiceLabel(choice) }}</p>
        <dl class="text-xs leading-relaxed">
          <div v-for="row in choiceFields(choice, data)" :key="row.label" class="mb-2">
            <dt class="text-g-700">{{ row.label }}</dt
            ><dd class="break-all">{{ row.value }}</dd>
          </div>
        </dl>
        <p class="text-xs text-g-700">来源：{{ sourceLabel(choice.source_kind) }}</p>
      </ElCard>
      <template v-if="data.address_confirmation">
        <p class="text-sm mb-2"
          >地址：{{
            data.address_confirmation.confirmed === true
              ? '已确认'
              : data.address_confirmation.confirmed === false
                ? '尚未确认'
                : '确认状态未知'
          }}</p
        >
        <p class="text-xs mb-2"
          >当前地址版本：{{ data.address_confirmation.version ?? '未明确' }}</p
        >
        <p class="text-xs mb-2">地区：{{ data.address_confirmation.market || '未明确' }}</p>
        <p class="text-xs text-g-700 mb-2"
          >来源：{{ sourceLabel(data.address_confirmation.source_kind) }}</p
        >
        <p class="text-xs text-g-700">发货前还需核对此次选择是否对应当前地址版本。</p>
      </template>
      <p v-else class="text-sm">尚未取得当前地址确认。</p>
    </ElCollapseItem>
  </ElCollapse>
</template>
<script setup lang="ts">
  import type { BusinessDetailData } from '@/api/business-contract'
  import { sourceLabel } from './business-format'
  import { choiceLabel, choiceFields } from './business-choices'
  defineProps<{ data: BusinessDetailData }>()
</script>
