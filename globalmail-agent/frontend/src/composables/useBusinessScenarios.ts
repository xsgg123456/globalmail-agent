import { ref } from 'vue'
import { businessApi, type BusinessApi } from '@/api/business-api'
import type { BusinessScenario } from '@/api/business-contract'
import { MailApiError, PendingCommands } from '@/api/mail-agent-request'
import { businessError } from '@/components/mail-agent/business-format'

export function useBusinessScenarios(api: BusinessApi = businessApi) {
  const scenarios = ref<BusinessScenario[]>([])
  const selectedId = ref('')
  const loading = ref(false)
  const busy = ref(false)
  const error = ref('')
  const pending = new PendingCommands()
  async function load() {
    loading.value = true
    error.value = ''
    try {
      scenarios.value = (await api.scenarios()).items
    } catch (cause) {
      error.value = businessError(cause)
    } finally {
      loading.value = false
    }
  }
  async function create(): Promise<string | null> {
    if (busy.value || !selectedId.value) return null
    const id = selectedId.value
    const command = pending.prepare(id, { scenario_id: id }, { expected_version: 0 })
    busy.value = true
    error.value = ''
    try {
      const response = await api.createScenario(id, command.payload, command.key)
      if (!response.conversation_id)
        throw new Error('服务未返回新会话，创建结果尚未确认，请重试相同场景。')
      pending.complete(id)
      return response.conversation_id
    } catch (cause) {
      if (cause instanceof MailApiError && cause.status === 409) pending.complete(id)
      error.value = businessError(cause)
      return null
    } finally {
      busy.value = false
    }
  }
  return { scenarios, selectedId, loading, busy, error, load, create }
}
