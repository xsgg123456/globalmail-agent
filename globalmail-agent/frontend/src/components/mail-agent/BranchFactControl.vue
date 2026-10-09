<template>
  <ElCollapse class="mt-3">
    <ElCollapseItem title="连续业务事实与更正" name="branch-facts">
      <p class="text-xs text-g-700 mb-3">填写当前实际核对的模拟事实和原始凭证。缺规格、客户来源或资源版本时，服务器会拒绝记录。</p>
      <ElForm label-position="top" @submit.prevent="confirm">
        <ElFormItem label="事实类型"><ElSelect v-model="form.event" class="w-full" :disabled="busy">
          <ElOption v-for="(label, value) in labels" :key="value" :value="value" :label="label" />
        </ElSelect></ElFormItem>
        <ElFormItem label="实际订单行编号"><ElInput v-model="form.orderLine" :disabled="busy" maxlength="160" /></ElFormItem>
        <ElFormItem label="原事实版本（首次为 0）"><ElInput v-model="form.version" :disabled="busy" inputmode="numeric" /></ElFormItem>
        <ElFormItem label="记录人"><ElInput v-model="form.staff" :disabled="busy" maxlength="160" /></ElFormItem>
        <ElFormItem label="实际模拟回执编号"><ElInput v-model="form.receipt" :disabled="busy" maxlength="240" /></ElFormItem>
        <ElFormItem label="核对依据或更正原因"><ElInput v-model="form.reason" type="textarea" :disabled="busy" maxlength="1000" /></ElFormItem>
        <template v-if="form.event === 'inventory_snapshot'">
          <ElFormItem label="商品或配件内部编号"><ElInput v-model="form.item" :disabled="busy" /></ElFormItem>
          <ElFormItem label="市场规格"><ElInput v-model="form.region" :disabled="busy" /></ElFormItem>
          <ElFormItem label="硬件版本"><ElInput v-model="form.hardware" :disabled="busy" /></ElFormItem>
          <ElFormItem label="含时区的快照时间"><ElInput v-model="form.snapshot" :disabled="busy" placeholder="2026-10-08T10:00:00+08:00" /></ElFormItem>
          <ElFormItem label="实有库存"><ElInput v-model="form.onHand" :disabled="busy" inputmode="numeric" /></ElFormItem>
        </template>
        <template v-if="form.event === 'address_confirmation'">
          <ElFormItem label="客户来源消息编号"><ElInput v-model="form.message" :disabled="busy" /></ElFormItem>
          <ElFormItem label="逐字客户原话"><ElInput v-model="form.quote" type="textarea" :disabled="busy" /></ElFormItem>
          <ElCheckbox v-model="form.confirmed" :disabled="busy">客户已明确确认当前地址</ElCheckbox>
        </template>
        <template v-if="['original_shipment', 'inspection_correction', 'return_documents'].includes(form.event)">
          <ElFormItem label="原包裹或退件编号"><ElInput v-model="form.resource" :disabled="busy" /></ElFormItem>
          <ElFormItem label="原资源版本"><ElInput v-model="form.resourceVersion" :disabled="busy" inputmode="numeric" /></ElFormItem>
        </template>
        <template v-if="['original_shipment', 'return_documents'].includes(form.event)">
          <ElFormItem label="承运商"><ElInput v-model="form.carrier" :disabled="busy" /></ElFormItem>
          <ElFormItem label="运单号"><ElInput v-model="form.tracking" :disabled="busy" /></ElFormItem>
        </template>
        <ElFormItem v-if="form.event === 'original_shipment'" label="实际物流状态"><ElSelect v-model="form.status" class="w-full" :disabled="busy">
          <ElOption value="label_created" label="已建标签" /><ElOption value="shipped" label="承运商已收件" /><ElOption value="delivered" label="已送达" />
        </ElSelect></ElFormItem>
        <template v-if="form.event === 'inspection_correction'">
          <ElFormItem label="本次质检结果"><ElSelect v-model="form.inspection" class="w-full" :disabled="busy">
            <ElOption value="passed" label="通过" /><ElOption value="failed" label="未通过" /><ElOption value="disputed" label="有争议" />
          </ElSelect></ElFormItem>
          <ElFormItem label="实际受检数量"><ElInput v-model="form.quantity" :disabled="busy" inputmode="numeric" /></ElFormItem>
        </template>
        <template v-if="form.event === 'return_documents'">
          <ElFormItem label="模拟退货地址"><ElInput v-model="form.address" type="textarea" :disabled="busy" /></ElFormItem>
          <ElFormItem label="包装说明"><ElInput v-model="form.packing" type="textarea" :disabled="busy" /></ElFormItem>
          <ElFormItem label="原邮费承担方"><ElSelect v-model="form.postage" class="w-full" :disabled="busy">
            <ElOption value="customer" label="客户" /><ElOption value="merchant" label="商家" />
          </ElSelect></ElFormItem>
          <ElFormItem v-if="form.postage === 'merchant'" label="新的模拟预付标签编号"><ElInput v-model="form.prepaid" :disabled="busy" /></ElFormItem>
        </template>
        <ElAlert v-if="error" :title="error" type="warning" :closable="false" class="my-3" />
        <ElButton native-type="submit" :loading="busy" class="mt-3">核对并记录事实</ElButton>
      </ElForm>
    </ElCollapseItem>
  </ElCollapse>
</template>
<script setup lang="ts">
  import { reactive, ref } from 'vue'
  import { ElMessageBox } from 'element-plus'
  import { branchFactInput, emptyBranchFact, factLabels } from './branch-fact-inputs'
  const props = defineProps<{ busy: boolean; submit: (input: Record<string, unknown>) => Promise<boolean> }>()
  const emit = defineEmits<{ changed: [] }>()
  const form = reactive(emptyBranchFact())
  const labels = factLabels
  const error = ref('')
  async function confirm() {
    if (props.busy) return
    const parsed = branchFactInput(form)
    error.value = parsed.error
    if (!parsed.input) return
    try { await ElMessageBox.confirm(`将按凭证记录“${labels[form.event]}”。更正保留原资料和结果，不能替代客户授权。`, '核对模拟事实', { confirmButtonText: '确认记录', cancelButtonText: '取消' }) } catch { return }
    if (await props.submit(parsed.input)) { form.sourceId = crypto.randomUUID(); emit('changed') }
  }
</script>
