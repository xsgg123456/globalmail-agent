import { ref, watch, onScopeDispose, onActivated, onDeactivated, type Ref } from 'vue'
import type { Conversation } from '@/api/mail-agent-contract'
import { ConversationEventSession } from './conversation-event-session'

export function useConversationEvents(
  conversation: Ref<Conversation | null>,
  refresh: () => Promise<void>,
  invalidate: () => void = () => {}
) {
  const state = ref('未选择会话')
  const session = new ConversationEventSession((url) => new EventSource(url))
  let refreshPending = false
  let dirty = false
  let active = true
  function reconnect() {
    session.close()
    if (!active) return
    const current = conversation.value
    if (!current) {
      state.value = '未选择会话'
      return
    }
    session.connect(
      current,
      async () => {
        invalidate()
        dirty = true
        if (refreshPending) return
        refreshPending = true
        try {
          while (dirty) {
            dirty = false
            await refresh()
          }
        } finally {
          refreshPending = false
        }
      },
      (value) => {
        state.value = value
      }
    )
  }
  watch(
    () => (conversation.value ? `${conversation.value.id}/${conversation.value.branch_id}` : ''),
    reconnect,
    { immediate: true }
  )
  onScopeDispose(() => session.close())
  onActivated(() => { active = true; reconnect() })
  onDeactivated(() => { active = false; dirty = false; session.close() })
  return { state, reconnect }
}
