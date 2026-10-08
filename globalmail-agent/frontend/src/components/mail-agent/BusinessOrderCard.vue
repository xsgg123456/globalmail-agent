<template>
  <ElCard shadow="never" class="mb-3 min-w-0">
    <template #header
      ><p class="text-sm font-medium break-all"
        >订单：{{ order.display_order_number || order.order_id }}</p
      ></template
    >
    <div class="flex flex-wrap gap-1 mb-3">
      <ElTag size="small" type="info">{{ sourceLabel(order.source_kind) }}</ElTag>
      <ElTag size="small" type="info">{{
        order.is_realtime === true
          ? '实时查询'
          : order.is_realtime === false
            ? '快照资料'
            : '实时性未知'
      }}</ElTag>
    </div>
    <p class="text-xs text-g-700 mb-2"
      >{{ order.brand || '品牌未知' }} · {{ order.market || '地区未知' }}</p
    >
    <p class="text-xs text-g-700 mb-2">快照：{{ formatMailTime(order.snapshot_at) }}</p>
    <p class="text-xs text-g-700 mb-2">购买：{{ formatMailTime(order.purchase_at ?? null) }}</p>
    <p class="text-xs text-g-700 mb-3">送达：{{ formatMailTime(order.delivered_at ?? null) }}</p>
    <p class="text-sm mb-2">订单实付：{{ formatMinor(order.paid_minor, order.currency) }}</p>
    <p class="text-xs mb-2">已退款：{{ formatMinor(order.refunded_minor, order.currency) }}</p>
    <p class="text-xs mb-3"
      >处理中退款：{{ formatMinor(order.pending_refund_minor, order.currency) }}</p
    >
    <p v-if="order.unknown_fields?.length" class="text-xs text-g-700 mb-3"
      >订单缺口：{{ missingLabels(order.unknown_fields) }}</p
    >
    <ElCollapse>
      <ElCollapseItem
        v-for="(line, index) in order.lines"
        :key="line.line_id"
        :name="line.line_id"
        :title="`${selectedLine === line.line_id ? '当前目标 · ' : ''}第${index + 1}项 · ${line.product_name || '商品名称未知'} · ${line.sku || 'SKU未知'}`"
      >
        <p class="text-sm mb-2">SKU：{{ line.sku || '未知' }}</p>
        <p class="text-sm mb-2">数量：{{ safeQuantity(line.quantity) }}</p>
        <p class="text-sm mb-2">本行实付：{{ formatMinor(line.paid_minor, order.currency) }}</p>
        <p class="text-xs text-g-700 mb-2">硬件版本：{{ line.hardware_revision || '未知' }}</p>
        <p v-if="line.unknown_fields?.length" class="text-xs text-g-700"
          >缺口：{{ missingLabels(line.unknown_fields) }}</p
        >
        <p class="text-xs font-medium mt-3 mb-2">第{{ index + 1 }}项的申请与物流</p>
        <BusinessLedger :records="recordsForLine(data, order.order_id, line.line_id)" />
      </ElCollapseItem>
    </ElCollapse>
  </ElCard>
</template>
<script setup lang="ts">
  import type { BusinessOrder, BusinessDetailData } from '@/api/business-contract'
  import BusinessLedger from './BusinessLedger.vue'
  import { sourceLabel, formatMinor, missingLabels } from './business-format'
  import { formatMailTime } from './mail-labels'
  import { recordsForLine } from './business-records'
  defineProps<{ order: BusinessOrder; data: BusinessDetailData; selectedLine: string }>()
  const safeQuantity = (value: number | null) =>
    Number.isSafeInteger(value) && value !== null && value > 0 ? value : '未知'
</script>
