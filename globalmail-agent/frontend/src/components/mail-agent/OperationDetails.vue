<template>
  <section class="border-t-d pt-4 mb-4 min-w-0" aria-label="售后申请与模拟执行">
    <ElCollapse>
      <ElCollapseItem title="售后申请与模拟执行" name="operations">
        <div class="flex flex-wrap gap-2 mb-3"><ElButton :loading="loading" :disabled="busy" @click="refresh">刷新售后记录</ElButton></div>
        <ElAlert v-if="error" :title="error" type="error" :closable="false" class="mb-3" />
        <ElAlert v-if="actionError" :title="actionError" type="error" :closable="false" class="mb-3" />
        <ElAlert v-if="notice" :title="notice" type="success" :closable="false" class="mb-3" />
        <div v-if="canRetry" class="mb-3">
          <p class="text-xs text-g-700 mb-2">原请求结果待核对：{{ retryCommand?.operation }}。核对前请保留当前输入。</p>
          <ElButton :loading="busy" @click="confirmRetry">核对原请求结果</ElButton>
        </div>
        <ElEmpty v-if="!loading && !error && !data?.operations.length" description="当前没有可见售后申请" :image-size="50" />
        <template v-if="data">
          <BranchFactControl v-if="context.mode === 'interactive_simulation' && data.branch_id" :key="`${context.id}:${retryVersion}`" :busy="busy || canRetry" :submit="submitFact" @changed="$emit('changed')" />
          <BusinessLedger :records="data" />
          <p v-if="context.mode !== 'interactive_simulation'" class="text-xs text-g-700 mt-3">历史模式仅查看，不能修改模拟账本。</p>
          <template v-else-if="data.branch_id && data.operations.length">
            <ElForm label-position="top" class="mt-3">
              <ElFormItem label="选择当前申请">
                <ElSelect v-model="selectedId" class="w-full" :disabled="busy" placeholder="选择申请">
                  <ElOption v-for="row in data.operations" :key="row.operation_id" :value="row.operation_id"
                    :label="`${actionLabels[row.kind] ?? '售后'} · ${recordStatus(row.status)} · ${row.operation_id}`" />
                </ElSelect>
              </ElFormItem>
            </ElForm>
            <ScenarioControl v-if="selected" :key="`${context.id}:${selected.operation_id}:${retryVersion}`" :operation="selected" :busy="busy || canRetry" :has-execution="hasExecution" :submit="submit" @changed="$emit('changed')" />
          </template>
        </template>
      </ElCollapseItem>
    </ElCollapse>
  </section>
</template>
<script setup lang="ts">
  import { computed, onScopeDispose, ref, toRef, watch } from 'vue'
  import { ElMessageBox } from 'element-plus'
  import type { AfterSalesContext } from '@/api/after-sales-contract'
  import { useAfterSales } from '@/composables/useAfterSales'
  import BusinessLedger from './BusinessLedger.vue'
  import ScenarioControl from './ScenarioControl.vue'
  import BranchFactControl from './BranchFactControl.vue'
  import { actionLabels, recordStatus } from './business-records'
  const props = defineProps<{ context: AfterSalesContext }>()
  const emit = defineEmits<{ changed: [] }>()
  const { data, loading, busy, error, actionError, notice, canRetry, retryCommand, refresh, submit, submitFact, retry, dispose } = useAfterSales(toRef(props, 'context'))
  const retryVersion = ref(0)
  async function confirmRetry() {
    if (busy.value || !canRetry.value) return
    const original = retryCommand.value
    try {
      await ElMessageBox.confirm('将按原参数和原请求编号核对结果，不会新建另一笔命令。', '核对原请求结果',
        { confirmButtonText: '确认核对', cancelButtonText: '取消' })
    } catch { return }
    if (original !== retryCommand.value || !canRetry.value) return
    if (await retry()) { ++retryVersion.value; emit('changed') }
  }
  onScopeDispose(dispose)
  const selectedId = ref('')
  const selected = computed(() => data.value?.operations.find(row => row.operation_id === selectedId.value))
  const hasExecution = computed(() => Boolean(data.value?.executions.some(row =>
    row.operation_id === selectedId.value && row.confirmed_not_executed !== true)))
  watch(() => data.value?.operations.map(row => row.operation_id), ids => {
    if (ids && !ids.includes(selectedId.value)) selectedId.value = ids[0] ?? ''
  })
</script>
