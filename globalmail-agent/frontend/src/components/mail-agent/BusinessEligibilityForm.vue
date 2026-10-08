<template>
  <section aria-label="核对售后条件" class="mt-4">
    <h4 class="text-sm font-medium mb-3">核对售后条件</h4>
    <ElAlert
      title="政策未发布，仅供核对；不能执行售后"
      type="warning"
      :closable="false"
      show-icon
      class="mb-3"
    />
    <p v-if="!selectedLine" class="text-xs text-g-700 mb-3"
      >尚未明确目标商品；试查会返回需要补充的条件。</p
    >
    <ElForm
      :model="form"
      label-position="top"
      :disabled="eligibilityLoading"
      @submit.prevent="submit"
    >
      <ElFormItem label="核对业务">
        <ElSelect v-model="form.action" aria-label="核对业务">
          <ElOption
            v-for="(label, action) in actionLabels"
            :key="action"
            :label="label"
            :value="action"
          />
        </ElSelect>
      </ElFormItem>
      <ElFormItem label="受影响数量" required :error="errors.quantity">
        <ElInput
          v-model="form.quantity"
          inputmode="numeric"
          aria-label="受影响数量"
          @blur="validate"
        />
      </ElFormItem>
      <ElFormItem label="币种（可选）" :error="errors.currency">
        <ElInput
          v-model="form.currency"
          :maxlength="3"
          placeholder="例如 USD"
          aria-label="核对币种"
          @blur="validate"
        />
      </ElFormItem>
      <ElFormItem label="核对金额（可选，按币种金额）" :error="errors.amount">
        <ElInput
          v-model="form.amount"
          :maxlength="50"
          inputmode="decimal"
          placeholder="例如 USD 12.50 填 12.50"
          aria-label="核对金额"
          @blur="validate"
        />
        <p class="text-xs text-g-700 mt-2">留空由政策核对可退余额；这里只试查，不提交退款申请。</p>
      </ElFormItem>
      <ElFormItem label="目标商品或配件编号（可选）" :error="errors.itemId">
        <ElInput
          v-model="form.itemId"
          :maxlength="100"
          placeholder="精确 SKU 或配件编号"
          aria-label="资格目标编号"
          @blur="validate"
        />
      </ElFormItem>
      <ElButton native-type="submit" :loading="eligibilityLoading">核对条件（只读）</ElButton>
    </ElForm>
    <ElAlert
      v-if="eligibilityError"
      :title="eligibilityError"
      type="error"
      :closable="false"
      show-icon
      class="mt-3"
    />
    <template v-if="eligibility">
      <ElAlert
        :title="businessStatus(eligibility)"
        :type="statusType(eligibility.status)"
        :closable="false"
        show-icon
        class="mt-3"
      />
      <template v-if="eligibility.data">
        <p class="text-sm font-medium mt-3"
          >核对结论：{{ outcomeLabels[eligibility.data.outcome] || '结论未确认' }}</p
        >
        <p class="text-xs text-g-700 mt-2">政策版本：{{ eligibility.data.version || '未知' }}</p>
        <p v-if="form.action === 'refund'" class="text-sm mt-2"
          >当前剩余可退余额：{{
            formatMinor(eligibility.data.remaining_refund_minor, form.currency || currency)
          }}</p
        >
        <ul class="mt-3 space-y-2 text-xs">
          <li
            v-for="(condition, index) in eligibility.data.conditions"
            :key="index"
            class="break-words"
          >
            {{ condition.label }}：{{ conditionLabel(condition.status) }}
          </li>
        </ul>
        <p v-if="eligibility.data.missing_fields.length" class="text-xs text-g-700 mt-3"
          >资料缺口：{{ missingLabels(eligibility.data.missing_fields) }}</p
        >
      </template>
      <p class="text-xs text-g-700 mt-3"
        >核对时间：{{
          formatMailTime(eligibility.observed_at)
        }}。客户选择、地址与证据仅取服务端已验证资料。</p
      >
    </template>
  </section>
</template>
<script setup lang="ts">
  import { reactive, ref, toRef, watch } from 'vue'
  import type { BusinessContext } from '@/api/business-contract'
  import { useBusinessPreviews } from '@/composables/useBusinessPreviews'
  import { eligibilityInput, type EligibilityInput } from './business-eligibility-input'
  import { actionLabels } from './business-records'
  import { businessStatus, statusType, formatMinor, missingLabels } from './business-format'
  import { formatMailTime } from './mail-labels'
  const props = defineProps<{
    context: BusinessContext
    selectedLine: string
    currency: string | null
  }>()
  const form = reactive<EligibilityInput>({
    action: 'refund',
    quantity: '1',
    amount: '',
    currency: props.currency || '',
    itemId: ''
  })
  const errors = ref<Record<string, string>>({})
  const { eligibility, eligibilityLoading, eligibilityError, checkEligibility, reset } =
    useBusinessPreviews(toRef(props, 'context'))
  const outcomeLabels: Record<string, string> = {
    eligible: '计算条件满足，尚不能执行',
    needs_input: '资料不完整，需要补充',
    wait: '等待业务条件',
    requires_review: '需人工核对',
    ineligible: '当前不符合条件'
  }
  const conditionLabel = (status: string) =>
    ({
      fulfilled: '已满足',
      needs_input: '缺少资料',
      wait: '等待条件',
      requires_review: '需人工核对',
      ineligible: '未满足'
    })[status] ?? '尚未确认'
  watch(
    () => [props.selectedLine, props.currency],
    () => {
      form.currency = props.currency || ''
      reset()
    }
  )
  watch(form, reset, { flush: 'sync' })
  function validate() {
    errors.value = eligibilityInput(form, props.selectedLine).errors
  }
  async function submit() {
    const input = eligibilityInput(form, props.selectedLine)
    errors.value = input.errors
    if (Object.keys(input.errors).length) return
    await checkEligibility(input.request)
  }
</script>
