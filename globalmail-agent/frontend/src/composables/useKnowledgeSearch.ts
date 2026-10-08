import { ref, onUnmounted } from 'vue'
import { knowledgeIndexApi, type KnowledgeIndexApi } from '@/api/knowledge-index-api'
import type { SearchInput, SearchResult } from '@/api/knowledge-index-contract'
import { knowledgeError } from '@/components/knowledge/knowledge-labels'

export function useKnowledgeSearch(api: KnowledgeIndexApi = knowledgeIndexApi) {
  const result = ref<SearchResult | null>(null),
    input = ref<SearchInput | null>(null)
  const busy = ref(false),
    error = ref(''),
    eligibility = ref<Record<string, string>>({})
  let generation = 0,
    closed = false
  async function search(command: SearchInput) {
    if (busy.value || closed) return
    const request = ++generation
    const frozen = JSON.parse(JSON.stringify(command)) as SearchInput
    input.value = frozen
    busy.value = true
    error.value = ''
    result.value = null
    eligibility.value = {}
    try {
      const output = await api.search(frozen)
      if (!closed && generation === request) result.value = output
    } catch (failure) {
      if (!closed && generation === request) error.value = knowledgeError(failure)
    } finally {
      if (!closed && generation === request) busy.value = false
    }
  }
  async function check(id: string) {
    const request = generation
    try {
      const value = await api.reference(id)
      if (!closed && request === generation)
        eligibility.value[id] = value.eligible
          ? '引用仍有效。'
          : '引用已停用或来源不完整，请重新试查。'
    } catch (failure) {
      if (!closed && request === generation) eligibility.value[id] = knowledgeError(failure)
    }
  }
  function close() {
    closed = true
    ++generation
  }
  onUnmounted(close)
  return { result, input, busy, error, eligibility, search, check, close }
}
