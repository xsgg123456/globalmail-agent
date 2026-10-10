import { ref, watch, type Ref } from 'vue'
import { observabilityApi, type RunObservability } from '../api/observability-api'

export function useRunObservability(
  runId: Readonly<Ref<string | undefined>>,
  revision: Readonly<Ref<unknown>>,
  api = observabilityApi
) {
  const record = ref<RunObservability | null>(null), loading = ref(false), error = ref('')
  let generation = 0, active = true
  async function refresh() {
    const id = runId.value, current = ++generation
    record.value = null; error.value = ''; loading.value = false
    if (!active || !id) return
    loading.value = true
    try {
      const value = await api.run(id)
      if (active && current === generation && runId.value === id) record.value = value
    } catch {
      if (active && current === generation) error.value = '观测状态读取失败，当前邮件与运行记录仍可查看。'
    } finally {
      if (current === generation) loading.value = false
    }
  }
  const stop = watch([runId, revision], refresh, { immediate: true, flush: 'sync' })
  function suspend() { active = false; generation++; record.value = null; loading.value = false; error.value = '' }
  function activate() { active = true; void refresh() }
  function dispose() { suspend(); stop() }
  return { record, loading, error, refresh, suspend, activate, dispose }
}
