import { ref, watch, type Ref } from 'vue'
import { agentRunApi, type AgentRunApi } from '@/api/agent-run-api'
import type { AgentRunDetail } from '@/api/agent-run-contract'
import type { ConversationDetail } from '@/api/mail-agent-contract'

export function useAgentRunDetails(
  context: Ref<ConversationDetail | null>,
  api: AgentRunApi = agentRunApi
) {
  const expanded = ref<string[]>([])
  const records = ref<Record<string, AgentRunDetail>>({})
  const loading = ref<Record<string, boolean>>({})
  const errors = ref<Record<string, string>>({})
  const requests = new Map<string, number>()
  let generation = 0
  let previousId = ''

  async function refresh(id: string) {
    const conversationId = context.value?.conversation.id
    if (!conversationId || !context.value?.runs.some((run) => run.id === id)) return
    const scope = generation
    const request = (requests.get(id) ?? 0) + 1
    requests.set(id, request)
    loading.value[id] = true
    errors.value[id] = ''
    const current = () =>
      scope === generation &&
      request === requests.get(id) &&
      conversationId === context.value?.conversation.id
    try {
      const response = await api.detail(id)
      if (current()) records.value[id] = response
    } catch (cause) {
      if (current()) {
        delete records.value[id]
        errors.value[id] = cause instanceof Error ? cause.message : '处理记录读取失败，请重试。'
      }
    } finally {
      if (current()) loading.value[id] = false
    }
  }
  const stopContext = watch(
    context,
    () => {
      ++generation
      requests.clear()
      loading.value = {}
      errors.value = {}
      const id = context.value?.conversation.id ?? ''
      if (id !== previousId) {
        records.value = {}
        expanded.value = context.value?.runs.at(-1) ? [context.value.runs.at(-1)!.id] : []
      } else {
        const ids = new Set(context.value?.runs.map((run) => run.id))
        expanded.value = expanded.value.filter((runId) => ids.has(runId))
        const latest = context.value?.runs.at(-1)?.id
        if (latest && !records.value[latest] && !expanded.value.includes(latest))
          expanded.value = [...expanded.value, latest]
        records.value = Object.fromEntries(
          Object.entries(records.value).filter(([runId]) => ids.has(runId))
        )
      }
      previousId = id
      for (const runId of expanded.value) void refresh(runId)
    },
    { immediate: true, flush: 'sync' }
  )
  const stopExpanded = watch(expanded, (ids) => {
    for (const id of ids) if (!records.value[id] && !loading.value[id]) void refresh(id)
  })
  const dispose = () => {
    ++generation
    stopContext()
    stopExpanded()
  }
  return { expanded, records, loading, errors, refresh, dispose }
}
