import { computed, ref, watch, type Ref } from 'vue'
import { businessApi, type BusinessApi } from '@/api/business-api'
import type { BusinessContext, BusinessDetailData, BusinessResult } from '@/api/business-contract'
import { businessError, contextKey } from '@/components/mail-agent/business-format'

export function useBusinessDetails(
  context: Ref<BusinessContext | null>,
  api: BusinessApi = businessApi
) {
  const orderNumber = ref('')
  const selectedLine = ref('')
  const result = ref<BusinessResult<BusinessDetailData> | null>(null)
  const loading = ref(false)
  const error = ref('')
  const inputError = ref('')
  let generation = 0
  let previousId = ''
  const data = computed(() => result.value?.data ?? null)
  const lines = computed(() =>
    (data.value?.orders ?? []).flatMap((order) => order.lines.map((line) => ({ order, line })))
  )
  const target = computed(() =>
    lines.value.find((entry) => entry.line.line_id === selectedLine.value)
  )
  async function refresh() {
    const current = context.value
    if (!current) return
    const key = contextKey(current)
    const request = ++generation
    loading.value = true
    error.value = ''
    try {
      const response = await api.detail(current.id, orderNumber.value.trim(), selectedLine.value)
      if (request !== generation || key !== contextKey(context.value)) return
      result.value = response
      selectedLine.value = response.data?.selected_line_id ?? ''
    } catch (cause) {
      if (request === generation && key === contextKey(context.value))
        error.value = businessError(cause)
    } finally {
      if (request === generation) loading.value = false
    }
  }
  async function search() {
    inputError.value = orderNumber.value.trim().length > 100 ? '订单号最多100个字符' : ''
    if (inputError.value) return
    selectedLine.value = ''
    result.value = null
    await refresh()
  }
  async function chooseLine(id: string) {
    selectedLine.value = id
    result.value = null
    await refresh()
  }
  const dispose = watch(
    () => contextKey(context.value),
    () => {
      ++generation
      result.value = null
      error.value = ''
      loading.value = false
      if (previousId !== context.value?.id) {
        orderNumber.value = ''
        selectedLine.value = ''
        inputError.value = ''
      }
      previousId = context.value?.id ?? ''
      void refresh()
    },
    { immediate: true, flush: 'sync' }
  )
  return {
    orderNumber,
    selectedLine,
    result,
    data,
    lines,
    target,
    loading,
    error,
    inputError,
    refresh,
    search,
    chooseLine,
    dispose
  }
}
