import { ref, onMounted, onUnmounted } from 'vue'
import { knowledgeApi, type KnowledgeApi } from '@/api/knowledge-api'
import type {
  Catalog,
  DocumentDetail,
  KnowledgeDocument,
  VersionDetail
} from '@/api/knowledge-contract'
import { knowledgeError } from '@/components/knowledge/knowledge-labels'
import { useKnowledgeCommands } from './useKnowledgeCommands'
export function useKnowledgeWorkbench(api: KnowledgeApi = knowledgeApi) {
  const items = ref<KnowledgeDocument[]>([]),
    catalog = ref<Catalog>({ products: [], parser_profiles: [] })
  const document = ref<DocumentDetail | null>(null),
    detail = ref<VersionDetail | null>(null)
  const filters = ref({ type: '', brand: '', sku: '', status: '', publication: '', cursor: '' })
  const nextCursor = ref<string | null>(null),
    cursors = ref<string[]>([''])
  const loading = ref(false),
    detailLoading = ref(false),
    busy = ref(false)
  const error = ref(''),
    actionError = ref(''),
    detailError = ref(''),
    catalogError = ref(''),
    notice = ref('')
  const selectedId = ref(''),
    versionId = ref('')
  const commands = useKnowledgeCommands(api)
  let listGeneration = 0,
    selectionGeneration = 0,
    detailGeneration = 0,
    timer: ReturnType<typeof setTimeout> | undefined,
    closed = false
  function stopPolling() {
    if (timer) clearTimeout(timer)
    timer = undefined
  }
  async function refreshList() {
    const generation = ++listGeneration
    loading.value = true
    error.value = ''
    try {
      const result = await api.list({ ...filters.value })
      if (closed || generation !== listGeneration) return
      items.value = result.items
      nextCursor.value = result.next_cursor
    } catch (failure) {
      if (!closed && generation === listGeneration) error.value = knowledgeError(failure)
    } finally {
      if (generation === listGeneration) loading.value = false
    }
  }
  async function refreshDetail() {
    const generation = selectionGeneration,
      did = selectedId.value,
      vid = versionId.value
    if (!did || closed) return
    const requestGeneration = ++detailGeneration
    stopPolling()
    try {
      const [doc, parsed] = await Promise.all([api.document(did), api.version(vid)])
      if (
        closed ||
        generation !== selectionGeneration ||
        requestGeneration !== detailGeneration ||
        did !== selectedId.value ||
        vid !== versionId.value
      )
        return
      document.value = doc
      detail.value = parsed
      detailError.value = ''
      if (parsed.jobs.some((job) => ['queued', 'running'].includes(job.status))) {
        stopPolling()
        timer = setTimeout(refreshDetail, 1500)
      }
    } catch (failure) {
      if (!closed && generation === selectionGeneration && requestGeneration === detailGeneration) {
        detailError.value = knowledgeError(failure)
        if (detail.value?.jobs.some((job) => ['queued', 'running'].includes(job.status)))
          timer = setTimeout(refreshDetail, 3000)
      }
    }
  }
  async function select(did: string, vid: string) {
    stopPolling()
    ++selectionGeneration
    selectedId.value = did
    versionId.value = vid
    document.value = null
    detail.value = null
    actionError.value = ''
    detailError.value = ''
    notice.value = ''
    detailLoading.value = true
    const generation = selectionGeneration
    await refreshDetail()
    if (generation === selectionGeneration) detailLoading.value = false
  }
  function closeDetail() {
    stopPolling()
    ++selectionGeneration
    selectedId.value = ''
    versionId.value = ''
    document.value = null
    detail.value = null
  }
  async function execute(path: string, payload: Record<string, unknown>) {
    if (busy.value) throw new Error('上一项操作还在进行，请稍候。')
    busy.value = true
    actionError.value = ''
    notice.value = ''
    try {
      const result = await commands.command(path, payload)
      notice.value = '操作已保存。新版本核对、构建并发布后才会生效。'
      await refreshList()
      if (result.document_id && result.version_id)
        await select(result.document_id, result.version_id)
      else await refreshDetail()
      return result
    } catch (failure) {
      actionError.value = knowledgeError(failure)
      await refreshDetail()
      throw failure
    } finally {
      busy.value = false
    }
  }
  async function filter() {
    filters.value.cursor = ''
    cursors.value = ['']
    await refreshList()
  }
  async function paginate(forward: boolean) {
    if (forward && nextCursor.value) cursors.value.push(nextCursor.value)
    else if (!forward && cursors.value.length > 1) cursors.value.pop()
    filters.value.cursor = cursors.value.at(-1) || ''
    await refreshList()
  }
  onMounted(async () => {
    try {
      catalog.value = await api.catalog()
    } catch (failure) {
      catalogError.value = knowledgeError(failure)
    }
    await refreshList()
  })
  onUnmounted(() => {
    closed = true
    ++listGeneration
    ++selectionGeneration
    stopPolling()
  })
  return {
    items,
    catalog,
    document,
    detail,
    filters,
    nextCursor,
    cursors,
    loading,
    detailLoading,
    busy,
    error,
    actionError,
    detailError,
    catalogError,
    notice,
    selectedId,
    versionId,
    refreshList,
    refreshDetail,
    select,
    closeDetail,
    execute,
    filter,
    paginate,
    upload: commands.upload
  }
}
