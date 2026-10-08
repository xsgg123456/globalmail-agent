<template>
  <section aria-label="订单与业务详情" class="border-t-d pt-4 mb-5 min-w-0">
    <div class="flex-cb flex-wrap gap-2 mb-3">
      <h3 class="text-sm font-medium">订单与业务详情</h3>
      <ElButton size="small" :loading="loading" @click="refresh">刷新业务</ElButton>
    </div>
    <ElForm label-position="top" @submit.prevent="search">
      <ElFormItem label="精确订单号（可选）" :error="inputError">
        <ElInput
          v-model="orderNumber"
          :maxlength="100"
          placeholder="留空查询当前会话已知订单"
          aria-label="精确订单号"
        />
      </ElFormItem>
      <ElButton native-type="submit" :loading="loading">查询当前会话订单</ElButton>
      <p class="text-xs text-g-700 mt-2 mb-3">支持脱敏和模拟编号；只查询当前会话允许访问的订单。</p>
    </ElForm>
    <ElAlert v-if="error" :title="error" type="error" :closable="false" show-icon class="mb-3" />
    <ElSkeleton v-if="loading && !result" :rows="3" animated />
    <template v-if="result">
      <ElAlert
        :title="businessStatus(result)"
        :type="statusType(result.status)"
        :closable="false"
        show-icon
        class="mb-3"
      />
      <p class="text-xs text-g-700 mb-2"
        >来源：{{ sourceLabel(result.source_kind) }}{{ result.simulation ? ' · 模拟资料' : '' }}</p
      >
      <p class="text-xs text-g-700 mb-3">查询时间：{{ formatMailTime(result.observed_at) }}</p>
      <template v-if="data">
        <p v-if="data.as_of" class="text-xs text-g-700 mb-3"
          >当前截点：{{ formatMailTime(data.as_of) }}</p
        >
        <ElAlert
          v-if="data.missing_fields.length"
          :title="`资料缺口：${missingLabels(data.missing_fields)}`"
          type="warning"
          :closable="false"
          class="mb-3"
        />
        <ElEmpty
          v-if="!data.orders.length"
          description="没有可用订单；缺失资料保持未知"
          :image-size="50"
        />
        <ElForm v-if="lines.length" label-position="top">
          <ElFormItem label="当前核对商品" required>
            <ElSelect
              :model-value="selectedLine"
              clearable
              aria-label="当前核对商品"
              placeholder="多商品时请明确选择"
              @update:model-value="chooseLine"
            >
              <ElOption
                v-for="entry in lines"
                :key="entry.line.line_id"
                :value="entry.line.line_id"
                :label="`${entry.order.display_order_number || entry.order.order_id} · 第${entry.order.lines.indexOf(entry.line) + 1}项 · ${entry.line.product_name || '商品名称未知'} · ${entry.line.sku || 'SKU未知'}`"
              />
            </ElSelect>
          </ElFormItem>
        </ElForm>
        <BusinessOrderCard
          v-for="order in data.orders"
          :key="order.order_id"
          :order="order"
          :data="data"
          :selected-line="selectedLine"
        />
        <BusinessCustomerChoices v-if="data.orders.length" :data="data" />
        <ElCollapse v-if="data.policy" class="mt-3">
          <ElCollapseItem name="policy" :title="`政策说明 · ${data.policy.version} · 未发布`">
            <p class="text-xs text-g-700 mb-2">来源：{{ sourceLabel(data.policy.source_kind) }}</p>
            <p class="text-xs text-g-700 mb-2"
              >可用时间：{{ formatMailTime(data.policy.available_at) }}</p
            >
            <p class="text-xs text-g-700 mb-3">政策未发布，仅供核对；不能执行售后。</p>
            <p class="text-sm whitespace-pre-wrap break-words">{{
              data.policy.description || '没有可读政策说明'
            }}</p>
          </ElCollapseItem>
        </ElCollapse>
        <ElCollapse v-if="data.orders.length" class="mt-4">
          <ElCollapseItem name="previews" title="核对售后条件、适配与库存（只读）">
            <BusinessEligibilityForm
              :context="context"
              :selected-line="selectedLine"
              :currency="target?.order.currency ?? null"
            />
            <BusinessAvailabilityForm :context="context" :selected-line="selectedLine" />
          </ElCollapseItem>
        </ElCollapse>
      </template>
      <ElEmpty v-else description="当前没有可展示的业务资料" :image-size="50" />
    </template>
  </section>
</template>
<script setup lang="ts">
  import { toRef } from 'vue'
  import type { BusinessContext } from '@/api/business-contract'
  import { useBusinessDetails } from '@/composables/useBusinessDetails'
  import { businessStatus, statusType, sourceLabel, missingLabels } from './business-format'
  import { formatMailTime } from './mail-labels'
  import BusinessOrderCard from './BusinessOrderCard.vue'
  import BusinessEligibilityForm from './BusinessEligibilityForm.vue'
  import BusinessAvailabilityForm from './BusinessAvailabilityForm.vue'
  import BusinessCustomerChoices from './BusinessCustomerChoices.vue'
  const props = defineProps<{ context: BusinessContext }>()
  const {
    orderNumber,
    selectedLine,
    result,
    data,
    lines,
    target,
    loading,
    error,
    inputError,
    refresh,
    search,
    chooseLine
  } = useBusinessDetails(toRef(props, 'context'))
</script>
