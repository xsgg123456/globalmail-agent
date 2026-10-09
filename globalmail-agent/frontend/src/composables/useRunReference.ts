import { ref, watch, type Ref } from 'vue'
import { agentRunApi, type AgentRunApi } from '@/api/agent-run-api'
import type { RunReference } from '@/api/agent-run-contract'

export interface ReferenceSelection {
  runId: string
  referenceId: string
}
export function useRunReference(
  selection: Ref<ReferenceSelection | null>,
  api: AgentRunApi = agentRunApi
) {
  const result = ref<RunReference | null>(null)
  const loading = ref(false)
  const error = ref('')
  let generation = 0
  async function refresh() {
    const selected = selection.value
    if (!selected) return
    const request = ++generation
    result.value = null
    loading.value = true
    error.value = ''
    try {
      const response = await api.reference(selected.runId, selected.referenceId)
      if (request === generation) result.value = response
    } catch (cause) {
      if (request === generation)
        error.value = cause instanceof Error ? cause.message : '引用检查失败，请重试。'
    } finally {
      if (request === generation) loading.value = false
    }
  }
  const stop = watch(
    selection,
    () => {
      ++generation
      result.value = null
      error.value = ''
      loading.value = false
      void refresh()
    },
    { immediate: true, flush: 'sync' }
  )
  const dispose = () => {
    ++generation
    stop()
  }
  return { result, loading, error, refresh, dispose }
}
