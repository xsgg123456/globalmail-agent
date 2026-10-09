<template>
  <section class="mt-4 border-t-d pt-3" aria-label="模拟售后控制台">
    <h4 class="text-sm font-medium mb-2">人工模拟控制台</h4>
    <p class="text-xs text-g-700 mb-3">仅记录本机模拟结果，不会支付退款或联系真实仓库。受理申请不代表执行成功。</p>
    <ElForm label-position="top" @submit.prevent="confirmEvent">
      <ElFormItem label="当前可用操作">
        <ElSelect v-model="form.event" placeholder="选择模拟操作" class="w-full" :disabled="busy">
          <ElOption v-for="event in operation.allowed_events" :key="event" :value="event" :label="eventLabels[event]" />
        </ElSelect>
      </ElFormItem>
      <template v-if="form.event === 'create_corrective_execution'">
        <ElFormItem label="记录人"><ElInput v-model="form.staffId" :disabled="busy" maxlength="160" /></ElFormItem>
        <ElFormItem label="原成功执行单编号"><ElInput v-model="form.correctionOf" :disabled="busy" maxlength="160" /></ElFormItem>
        <ElFormItem label="发件差错核查回执"><ElInput v-model="form.receiptRef" :disabled="busy" maxlength="240" /></ElFormItem>
        <ElFormItem label="差错与纠正原因"><ElInput v-model="form.reason" type="textarea" :disabled="busy" maxlength="500" /></ElFormItem>
      </template>
      <ElFormItem v-if="form.event && form.event !== 'create_execution' && form.event !== 'inventory_changed'" label="执行单编号（多笔时必填）">
        <ElInput v-model="form.executionId" :disabled="busy" maxlength="160" />
      </ElFormItem>
      <ElFormItem v-if="['succeeded', 'label_created', 'received', 'inspected', 'reconciled_not_executed', 'cancellation_acknowledged', 'shipped', 'delivered'].includes(form.event)" :label="returnDocuments ? '退货授权编号' : '实际模拟回执或标签编号'">
        <ElInput v-model="form.receiptRef" :disabled="busy" maxlength="240" />
      </ElFormItem>
      <template v-if="returnDocuments">
        <ElFormItem label="模拟退货地址"><ElInput v-model="form.returnAddress" type="textarea" :disabled="busy" maxlength="1000" /></ElFormItem>
        <ElFormItem label="包装说明"><ElInput v-model="form.packingInstructions" type="textarea" :disabled="busy" maxlength="2000" /></ElFormItem>
        <ElFormItem label="邮费承担方">
          <ElSelect v-model="form.postageResponsibility" :disabled="busy" class="w-full">
            <ElOption value="customer" label="客户" /><ElOption value="merchant" label="商家" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem v-if="form.postageResponsibility === 'merchant'" label="实际模拟预付标签编号">
          <ElInput v-model="form.prepaidLabelRef" :disabled="busy" maxlength="240" />
        </ElFormItem>
      </template>
      <template v-if="['shipped', 'label_created', 'return_in_transit'].includes(form.event)">
        <ElFormItem label="承运商"><ElInput v-model="form.carrier" :disabled="busy" maxlength="80" /></ElFormItem>
        <ElFormItem label="运单号"><ElInput v-model="form.trackingNumber" :disabled="busy" maxlength="160" /></ElFormItem>
      </template>
      <ElFormItem v-if="['failed', 'unknown', 'reconciled_not_executed', 'cancellation_acknowledged'].includes(form.event)" label="失败、未知或对账依据">
        <ElInput v-model="form.reason" type="textarea" :disabled="busy" maxlength="500" />
      </ElFormItem>
      <ElFormItem v-if="form.event === 'inspected'" label="实际质检结果">
        <ElSelect v-model="form.reason" :disabled="busy" class="w-full">
          <ElOption value="passed" label="通过" /><ElOption value="failed" label="未通过" /><ElOption value="disputed" label="有争议" />
        </ElSelect>
      </ElFormItem>
      <ElCheckbox v-if="['reconciled_not_executed', 'cancellation_acknowledged'].includes(form.event)" v-model="form.confirmedNotExecuted" :disabled="busy" class="mb-3">
        已核对原执行尝试，确认未实际执行
      </ElCheckbox>
      <ElFormItem v-if="['received', 'inspected'].includes(form.event)" label="实际收件或质检数量">
        <ElInput v-model="form.quantity" :disabled="busy" inputmode="numeric" />
      </ElFormItem>
      <ElFormItem v-if="form.event === 'inventory_changed'" label="此申请精确规格的当前库存">
        <ElInput v-model="form.onHand" :disabled="busy" inputmode="numeric" />
      </ElFormItem>
      <ElAlert v-if="validationError" :title="validationError" type="warning" :closable="false" class="mb-3" />
      <ElButton native-type="submit" :loading="busy" :disabled="!form.event">确认模拟记录</ElButton>
    </ElForm>
    <ElCollapse class="mt-3">
      <ElCollapseItem title="备用：核对已有执行单关联" name="link">
        <p class="text-xs text-g-700 mb-2">仅核对同一分支、申请和份额的已有执行单，不会新建执行或生成成功回执。</p>
        <ElInput v-model="linkId" placeholder="现有执行单编号" :disabled="busy" maxlength="160" class="mb-2" />
        <ElButton :loading="busy" :disabled="!linkId.trim()" @click="confirmLink">确认已有关联</ElButton>
      </ElCollapseItem>
    </ElCollapse>
  </section>
</template>
<script setup lang="ts">
  import { computed, reactive, ref } from 'vue'
  import { ElMessageBox } from 'element-plus'
  import type { OperationRecord, SimulationInput } from '@/api/after-sales-contract'
  import { emptySimulationForm, eventLabels, simulationInput } from './after-sales-inputs'
  const props = defineProps<{
    operation: OperationRecord
    busy: boolean
    hasExecution: boolean
    submit: (kind: 'event' | 'link', operation: OperationRecord, input: SimulationInput | { execution_id: string }) => Promise<boolean>
  }>()
  const emit = defineEmits<{ changed: [] }>()
  const form = reactive(emptySimulationForm())
  const linkId = ref('')
  const validationError = ref('')
  const returnDocuments = computed(() => form.event === 'label_created' &&
    (['return', 'refund'].includes(props.operation.kind) || props.operation.kind === 'replacement' && !props.hasExecution))
  async function confirmEvent() {
    if (props.busy) return
    const checked = simulationInput(form, props.operation.allowed_events, returnDocuments.value)
    validationError.value = checked.errors.join(' ')
    if (!checked.input) return
    const operation = props.operation
    const eventLabel = checked.input.event === 'inspected'
      ? `${eventLabels.inspected} · ${checked.input.reason === 'passed' ? '通过' : checked.input.reason === 'failed' ? '未通过' : '有争议'}`
      : eventLabels[checked.input.event]
    try {
      await ElMessageBox.confirm(`${eventLabel}：${operation.operation_id}。资料将写入当前分支的真实模拟账本。`, '确认模拟操作',
        { confirmButtonText: '确认记录', cancelButtonText: '取消', type: 'warning' })
    } catch { return }
    if (props.busy || operation.operation_id !== props.operation.operation_id || operation.version !== props.operation.version) {
      validationError.value = '确认期间申请已变化，请刷新核对。'
      return
    }
    if (await props.submit('event', operation, checked.input)) {
      Object.assign(form, emptySimulationForm())
      emit('changed')
    }
  }
  async function confirmLink() {
    const executionId = linkId.value.trim()
    if (!executionId || props.busy) return
    const operation = props.operation
    try {
      await ElMessageBox.confirm(`核对执行单 ${executionId} 与申请 ${operation.operation_id} 的现有关系。`, '确认已有关联',
        { confirmButtonText: '确认核对', cancelButtonText: '取消' })
    } catch { return }
    if (props.busy || operation.operation_id !== props.operation.operation_id || operation.version !== props.operation.version) return
    if (await props.submit('link', operation, { execution_id: executionId })) {
      linkId.value = ''
      emit('changed')
    }
  }
</script>
