import { ref, onUnmounted } from 'vue'
import { knowledgeIndexApi, type KnowledgeIndexApi } from '@/api/knowledge-index-api'
import type { IndexProfiles, IndexStatus, ReleaseListing } from '@/api/knowledge-index-contract'
import { PendingCommands, MailApiError } from '@/api/mail-agent-request'
import { knowledgeError } from '@/components/knowledge/knowledge-labels'

// Closing a drawer must not lose an unconfirmed publication command.
const sharedCommands = new PendingCommands()
export function useKnowledgeIndex(api: KnowledgeIndexApi = knowledgeIndexApi) {
  const pending = api === knowledgeIndexApi ? sharedCommands : new PendingCommands()
  const profiles = ref<IndexProfiles>({ items: [], chunkers: [] })
  const status = ref<IndexStatus | null>(null)
  const releases = ref<ReleaseListing>({
    head: { release_id: null, epoch: 0, embedding_profile_id: null },
    items: []
  })
  const loading = ref(false),
    busy = ref(false),
    error = ref(''),
    actionError = ref(''),
    notice = ref('')
  let selected = '',
    generation = 0,
    closed = false,
    timer: ReturnType<typeof setTimeout> | undefined
  function stop() {
    clearTimeout(timer)
    timer = undefined
  }
  async function refresh(id = selected) {
    if (closed) return
    if (id !== selected) {
      status.value = null
      actionError.value = ''
      notice.value = ''
    }
    selected = id
    const request = ++generation
    stop()
    loading.value = true
    try {
      const [configuration, history, state] = await Promise.all([
        api.profiles(),
        api.releases(),
        id ? api.status(id) : Promise.resolve(null)
      ])
      if (closed || request !== generation) return
      profiles.value = configuration
      releases.value = history
      status.value = state
      error.value = ''
      if (state?.builds.some((b) => ['queued', 'indexing'].includes(b.status)))
        timer = setTimeout(() => refresh(), 1500)
    } catch (failure) {
      if (!closed && request === generation) {
        error.value = knowledgeError(failure)
        if (status.value?.builds.some((b) => ['queued', 'indexing'].includes(b.status)))
          timer = setTimeout(() => refresh(), 3000)
      }
    } finally {
      if (request === generation) loading.value = false
    }
  }
  async function execute(path: string, body: Record<string, unknown>) {
    if (busy.value) throw new Error('上一项操作还在进行，请稍候。')
    const { expected_version: _version, expected_release_epoch: _epoch, ...identity } = body
    const command = pending.prepare(path, identity, body)
    busy.value = true
    actionError.value = ''
    notice.value = ''
    try {
      const result = await api.command(path, command.payload, command.key)
      pending.complete(path)
      notice.value = '操作已保存。'
      await refresh()
      return result
    } catch (failure) {
      if (failure instanceof MailApiError && failure.status >= 400 && failure.status < 500)
        pending.complete(path)
      actionError.value = knowledgeError(failure)
      await refresh()
      throw failure
    } finally {
      busy.value = false
    }
  }
  function close() {
    closed = true
    ++generation
    stop()
  }
  onUnmounted(close)
  return {
    profiles,
    status,
    releases,
    loading,
    busy,
    error,
    actionError,
    notice,
    refresh,
    execute,
    close
  }
}
