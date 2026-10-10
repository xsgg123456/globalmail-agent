import { computed, ref, watch } from 'vue'
import { ElMessageBox } from 'element-plus'
import { agentRunApi } from '@/api/agent-run-api'
import type { ConversationAdvice } from '@/api/agent-run-contract'
import { useMailWorkbench } from './useMailWorkbench'

export function useConversationAdvice(work: ReturnType<typeof useMailWorkbench>, api: Pick<typeof agentRunApi,'advice'> = agentRunApi,
  confirm = () => ElMessageBox.confirm('替换你正在编辑的回复草稿？', '采用 Agent 建议', { confirmButtonText: '替换草稿', cancelButtonText: '保留我的草稿' })) {
  const open = ref(false), snapshot = ref<ConversationAdvice | null>(null), error = ref(''), loading = ref(false)
  let generation = 0
  const current = computed(() => snapshot.value?.advice && !snapshot.value.stale
    && snapshot.value.input_revision === work.conversation.value?.input_revision
    && snapshot.value.run_id === work.detail.value?.runs.at(-1)?.id
    && work.conversation.value?.lifecycle === 'open')
  async function refresh() {
    const id = work.selectedId.value, request = ++generation
    if (!id) { snapshot.value = null; return }
    loading.value = true; error.value = ''
    try {
      const result = await api.advice(id)
      if (request === generation && id === work.selectedId.value) snapshot.value = result
    } catch (failure) {
      if (request === generation) { snapshot.value = null; error.value = failure instanceof Error ? failure.message : '建议读取失败' }
    } finally { if (request === generation) loading.value = false }
  }
  async function adopt() {
    const id = work.selectedId.value, source = snapshot.value?.advice
    if (!source || !current.value || !source.draft) return
    const revision = source.input_revision, runId = source.run_id
    const initialReply = work.humanInput.value.reply
    if (work.humanInput.value.reply.trim() && work.humanInput.value.reply !== source.draft) {
      try { await confirm() }
      catch { return }
    }
    // Recheck server state after the user spends time reviewing the overwrite dialog.
    await refresh(); await work.refreshDetail()
    if (work.humanInput.value.reply !== initialReply) { error.value = '你已继续编辑回复，请重新确认采用。'; return }
    if (error.value || work.detailError.value || id !== work.selectedId.value || !current.value || snapshot.value?.run_id !== runId
      || snapshot.value.input_revision !== revision) { error.value = '信息已更新，请核对最新建议后再采用。'; return }
    work.setHuman({ ...work.humanInput.value, reply: source.draft })
    work.acknowledgeHuman(); open.value = false
  }
  watch(work.selectedId, () => { snapshot.value = null; open.value = false; void refresh() })
  watch([() => work.conversation.value?.input_revision, () => work.detail.value?.runs.at(-1)?.status], refresh)
  return { open, snapshot, error, loading, current, refresh, adopt }
}
