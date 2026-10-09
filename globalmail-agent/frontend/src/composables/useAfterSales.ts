import { computed, ref, shallowRef, watch, type Ref } from 'vue'
import { afterSalesApi, type AfterSalesApi } from '@/api/after-sales-api'
import { MailApiError, PendingCommands } from '@/api/mail-agent-request'
import type { AfterSalesContext, LedgerResult, OperationRecord, SimulationInput } from '@/api/after-sales-contract'
import { businessError } from '@/components/mail-agent/business-format'

export function useAfterSales(context: Ref<AfterSalesContext>, api: AfterSalesApi = afterSalesApi) {
  const result = ref<LedgerResult | null>(null)
  const loading = ref(false)
  const busy = ref(false)
  const error = ref('')
  const actionError = ref('')
  const notice = ref('')
  type RetryCommand = { kind: 'event' | 'link' | 'fact'; branch: string; id: string; operation: string;
    action: string; key: string; payload: Record<string, unknown> }
  const retryCommand = shallowRef<RetryCommand | null>(null)
  const canRetry = computed(() => Boolean(retryCommand.value && context.value.mode === 'interactive_simulation' &&
    retryCommand.value.id === context.value.id && data.value?.branch_id === retryCommand.value.branch))
  const data = computed(() => result.value?.data ?? null)
  let scopeGeneration = 0
  let readGeneration = 0
  let previousId = ''
  let pending = new PendingCommands()
  async function refresh() {
    const id = context.value.id
    const request = ++readGeneration
    const scope = scopeGeneration
    loading.value = true
    error.value = ''
    try {
      const value = await api.listing(id)
      if (scope !== scopeGeneration || request !== readGeneration || id !== context.value.id) return
      result.value = value
    } catch (cause) {
      if (scope === scopeGeneration && request === readGeneration) error.value = businessError(cause)
    } finally {
      if (scope === scopeGeneration && request === readGeneration) loading.value = false
    }
  }
  async function submit(kind: 'event' | 'link', operation: OperationRecord, input: SimulationInput | { execution_id: string }) {
    const ledger = data.value
    if (busy.value || !ledger?.branch_id || context.value.mode !== 'interactive_simulation') return false
    if (retryCommand.value) {
      actionError.value = '原请求结果尚未确认，请先核对原请求结果。'
      return false
    }
    const current = ledger.operations.find(row => row.operation_id === operation.operation_id)
    if (!current || current.version !== operation.version) {
      actionError.value = '申请已变化，请刷新后核对。'
      return false
    }
    const id = context.value.id
    const action = `${kind}:${current.operation_id}`
    const prepared = pending.prepare(action, { id, branch: ledger.branch_id, operation: current.operation_id, input }, {
      conversation_id: id, expected_version: ledger.conversation_version,
      operation_id: current.operation_id, expected_operation_version: current.version, ...input
    })
    return execute({ kind, branch: ledger.branch_id, id, operation: current.operation_id,
      action, key: prepared.key, payload: prepared.payload })
  }
  async function retry() {
    if (busy.value || !canRetry.value || !retryCommand.value) return false
    return execute(retryCommand.value)
  }
  async function submitFact(input: Record<string, unknown>) {
    const ledger = data.value
    if (busy.value || retryCommand.value || !ledger?.branch_id || context.value.mode !== 'interactive_simulation') return false
    const id = context.value.id
    const action = `fact:${String(input.source_event_id)}`
    const prepared = pending.prepare(action, { id, branch: ledger.branch_id, input }, {
      ...input, conversation_id: id, expected_version: ledger.conversation_version
    })
    return execute({ kind: 'fact', branch: ledger.branch_id, id, operation: '', action,
      key: prepared.key, payload: prepared.payload })
  }
  async function execute(command: RetryCommand) {
    const { id, operation, action } = command
    const scope = scopeGeneration
    retryCommand.value = command
    busy.value = true
    actionError.value = ''
    notice.value = ''
    try {
      const response = await api[command.kind](command.branch, command.payload, command.key)
      if (scope !== scopeGeneration || id !== context.value.id) return false
      if (response.conversation_id !== id || command.kind !== 'fact' && response.operation_id !== operation)
        throw new Error('响应关联不匹配，请刷新核验原申请。')
      pending.complete(action)
      retryCommand.value = null
      notice.value = '模拟记录已保存，请以刷新后的申请和执行回执核对进度。'
      await refresh()
      return true
    } catch (cause) {
      if (scope === scopeGeneration && id === context.value.id) {
        actionError.value = businessError(cause)
        if (cause instanceof MailApiError && cause.status >= 400 && cause.status < 500) {
          pending.complete(action)
          retryCommand.value = null
        }
      }
      return false
    } finally {
      if (scope === scopeGeneration) busy.value = false
    }
  }
  const stopScope = watch(() => `${context.value.id}:${context.value.mode}`, () => {
    ++scopeGeneration
    ++readGeneration
    previousId = context.value.id
    pending = new PendingCommands()
    retryCommand.value = null
    result.value = null
    loading.value = busy.value = false
    error.value = actionError.value = notice.value = ''
    void refresh()
  }, { immediate: true, flush: 'sync' })
  const stopVersion = watch(() => [context.value.row_version, context.value.input_revision], () => {
    if (previousId === context.value.id) void refresh()
  })
  function dispose() {
    ++scopeGeneration
    ++readGeneration
    stopScope()
    stopVersion()
  }
  return { result, data, loading, busy, error, actionError, notice, canRetry, retryCommand, refresh, submit, submitFact, retry, dispose }
}
