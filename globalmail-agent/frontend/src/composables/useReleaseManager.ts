import { ref } from 'vue'
import { knowledgeApi, type KnowledgeApi } from '@/api/knowledge-api'
import { knowledgeIndexApi, type KnowledgeIndexApi } from '@/api/knowledge-index-api'
import type { IndexBuild } from '@/api/knowledge-index-contract'
import { knowledgeError } from '@/components/knowledge/knowledge-labels'
export interface ReleaseCandidate {
  documentId: string
  title: string
  version: number
  versions: Record<string, number>
  builds: IndexBuild[]
}
export function useReleaseManager(
  api: KnowledgeApi = knowledgeApi,
  indexApi: KnowledgeIndexApi = knowledgeIndexApi
) {
  const candidates = ref<ReleaseCandidate[]>([]),
    loading = ref(false),
    error = ref('')
  let generation = 0
  async function load() {
    const request = ++generation
    loading.value = true
    error.value = ''
    candidates.value = []
    try {
      const documents = [],
        seen = new Set<string>()
      let cursor = ''
      do {
        const page = await api.list({ cursor })
        documents.push(...page.items)
        cursor = page.next_cursor || ''
        if (cursor && seen.has(cursor)) throw new Error('资料分页未前进，请刷新后重试。')
        seen.add(cursor)
      } while (cursor)
      const values = await Promise.all(
        documents.map(async (doc) => {
          const detail = await api.document(doc.id)
          const states = await Promise.all(detail.versions.map((v) => indexApi.status(v.id)))
          return {
            documentId: doc.id,
            title: doc.title,
            version: doc.current_version_number,
            versions: Object.fromEntries(detail.versions.map((v) => [v.id, v.number])),
            builds: states.flatMap((s) => s.builds.filter((b) => b.eligible))
          }
        })
      )
      if (request === generation) candidates.value = values
    } catch (failure) {
      if (request === generation) error.value = knowledgeError(failure)
    } finally {
      if (request === generation) loading.value = false
    }
  }
  function cancel() {
    ++generation
  }
  return { candidates, loading, error, load, cancel }
}
