import { computed, onMounted, onActivated, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import type { AgentRunDetail } from '@/api/agent-run-contract'
import { agentRunApi } from '@/api/agent-run-api'
import { useMailWorkbench } from './useMailWorkbench'
import { useConversationEvents } from './useConversationEvents'
import { conversationRounds, executionSteps } from '@/components/agent-runtime/run-presentation'
import { agentReadingPositions } from './agent-reading-state'

export function useAgentConsole() {
  const route = useRoute(), router = useRouter(), work = useMailWorkbench()
  const loadedRecord = ref<AgentRunDetail | null>(null), error = ref(''), loading = ref(false)
  let generation = 0
  const rounds = computed(() => conversationRounds(work.detail.value?.runs ?? []))
  const run = computed(() => route.query.run_id
    ? work.detail.value?.runs.find((item) => item.id === route.query.run_id)
    : work.detail.value?.runs.at(-1))
  const record = computed(() => loadedRecord.value?.run.id === run.value?.id ? loadedRecord.value : null)
  const steps = computed(() => record.value?.run.id === run.value?.id ? executionSteps(record.value!) : [])
  const step = computed(() => steps.value.find((item) => item.id === route.query.step_id) ?? steps.value[0])
  async function refreshRun() {
    if (route.path !== '/agent-runs') return
    const id = run.value?.id, current = ++generation
    if (!id) {
      loadedRecord.value = null; loading.value = false
      if (route.query.run_id) error.value = '指定运行不存在或不属于当前会话，请重新选择轮次。'
      return
    }
    loading.value = true; error.value = ''
    try {
      const value = await agentRunApi.detail(id)
      if (current === generation && run.value?.id === id) loadedRecord.value = value
    } catch (failure) {
      if (current === generation) { loadedRecord.value = null; error.value = failure instanceof Error ? failure.message : '运行记录读取失败' }
    } finally { if (current === generation) loading.value = false }
  }
  async function selectConversation(id: string) {
    await router.replace({ path: '/agent-runs', query: { conversation_id: id } })
  }
  function selectRun(id: string) {
    void router.replace({ path: '/agent-runs', query: { conversation_id: work.selectedId.value, run_id: id } })
  }
  function selectStep(id: string) {
    void router.replace({ path: '/agent-runs', query: { conversation_id: work.selectedId.value, run_id: run.value?.id, step_id: id } })
  }
  function openMail(messageId?: string | null) {
    void router.push({ path: '/workbench', query: { conversation_id: work.selectedId.value, message_id: messageId ?? undefined } })
  }
  onBeforeRouteLeave(() => {
    if (run.value) agentReadingPositions[work.selectedId.value] = {runId:run.value.id,stepId:step.value?.id}
  })
  async function synchronize() {
    if (route.path !== '/agent-runs') return
    const id = typeof route.query.conversation_id === 'string' ? route.query.conversation_id : work.selectedId.value
    if (id && id !== work.selectedId.value) await work.select(id)
    else if (id) await work.refreshDetail()
    if (route.path !== '/agent-runs') return
    if (!route.query.run_id && work.detail.value?.runs.at(-1)) {
      const saved = agentReadingPositions[work.selectedId.value]
      const remembered = saved && work.detail.value.runs.some(item=>item.id === saved.runId)
      await router.replace({ path:'/agent-runs', query:{...route.query,conversation_id:work.selectedId.value,run_id:remembered ? saved.runId : work.detail.value.runs.at(-1)!.id,step_id:remembered ? saved.stepId : undefined} })
    }
    await refreshRun()
  }
  watch(() => [route.query.conversation_id, route.query.run_id], synchronize)
  onActivated(synchronize)
  watch(() => run.value?.id, refreshRun)
  const events = useConversationEvents(work.conversation, async () => {
    await work.refreshDetail(); await work.refreshList(); await refreshRun()
  })
  onMounted(async () => {
    await work.refreshList()
    if (!route.query.conversation_id && typeof route.query.run_id === 'string') {
      try {
        const value = await agentRunApi.detail(route.query.run_id)
        if (value.run.conversation_id) await router.replace({ path: '/agent-runs', query: { ...route.query, conversation_id: value.run.conversation_id } })
      } catch (failure) { error.value = failure instanceof Error ? failure.message : '运行读取失败' }
    }
    if (!work.selectedId.value && !route.query.conversation_id && work.items.value[0])
      await selectConversation(work.items.value[0].id)
    await synchronize()
  })
  return { work, record, error, loading, rounds, run, steps, step, events,
    refreshRun, selectConversation, selectRun, selectStep, openMail }
}
