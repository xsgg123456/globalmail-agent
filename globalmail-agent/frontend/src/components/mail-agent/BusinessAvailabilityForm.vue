<template>
  <section aria-label="适配与库存试查" class="mt-4">
    <h4 class="text-sm font-medium mb-3">适配与库存试查</h4>
    <ElForm label-position="top" :disabled="availabilityLoading" @submit.prevent="submit">
      <ElFormItem label="精确商品或配件编号" required :error="inputError">
        <ElInput
          v-model="itemId"
          :maxlength="100"
          placeholder="输入精确 SKU 或配件编号"
          aria-label="库存目标编号"
        />
        <p class="text-xs text-g-700 mt-2"
          >商品填上方 SKU；配件填资料中的 SIM 演练配件编号，不能按名称或 SKU 前缀猜适配。</p
        >
      </ElFormItem>
      <ElButton native-type="submit" :loading="availabilityLoading" :disabled="!selectedLine"
        >查询适配与库存</ElButton
      >
      <p class="text-xs text-g-700 mt-2">{{
        selectedLine ? '可用库存不表示已锁库或已创建补发单。' : '请先在上方明确目标商品。'
      }}</p>
    </ElForm>
    <ElAlert
      v-if="availabilityError"
      :title="availabilityError"
      type="error"
      :closable="false"
      show-icon
      class="mt-3"
    />
    <template v-if="availability">
      <ElAlert
        :title="businessStatus(availability)"
        :type="statusType(availability.status)"
        :closable="false"
        show-icon
        class="mt-3"
      />
      <template v-if="availability.data">
        <p class="text-sm mt-3"
          >适配：{{
            availability.data.compatible === true
              ? '精确关系支持适配'
              : availability.data.compatible === false
                ? '不适配当前商品'
                : '适配关系未知'
          }}</p
        >
        <p class="text-sm mt-2"
          >可用数量：{{
            availability.data.available_quantity === 0
              ? '0（缺货）'
              : quantityLabel(availability.data.available_quantity)
          }}</p
        >
        <p class="text-xs text-g-700 mt-2"
          >现有 {{ quantityLabel(availability.data.on_hand) }} · 已占用
          {{ quantityLabel(availability.data.reserved) }}</p
        >
        <p class="text-xs text-g-700 mt-2"
          >来源：{{ sourceLabel(availability.data.source_kind) }}</p
        >
        <p class="text-xs text-g-700 mt-2"
          >快照：{{ formatMailTime(availability.data.snapshot_at) }}</p
        >
        <p v-if="availability.data.missing_fields.length" class="text-xs text-g-700 mt-2"
          >资料缺口：{{ missingLabels(availability.data.missing_fields) }}</p
        >
      </template>
    </template>
  </section>
</template>
<script setup lang="ts">
  import { ref, toRef, watch } from 'vue'
  import type { BusinessContext } from '@/api/business-contract'
  import { useBusinessPreviews } from '@/composables/useBusinessPreviews'
  import { businessStatus, statusType, sourceLabel, missingLabels } from './business-format'
  import { formatMailTime } from './mail-labels'
  const props = defineProps<{ context: BusinessContext; selectedLine: string }>()
  const itemId = ref(''),
    inputError = ref('')
  const { availability, availabilityLoading, availabilityError, checkAvailability, reset } =
    useBusinessPreviews(toRef(props, 'context'))
  watch(() => props.selectedLine, reset)
  watch(itemId, reset, { flush: 'sync' })
  const quantityLabel = (value: number | null) =>
    value !== null && Number.isSafeInteger(value) && value >= 0 ? String(value) : '未知'
  async function submit() {
    inputError.value = !itemId.value.trim()
      ? '请输入精确商品或配件编号'
      : itemId.value.trim().length > 100
        ? '编号最多100个字符'
        : ''
    if (inputError.value || !props.selectedLine) return
    await checkAvailability(props.selectedLine, itemId.value.trim())
  }
</script>
