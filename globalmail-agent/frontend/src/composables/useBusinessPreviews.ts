import { ref, watch, type Ref } from 'vue'
import { businessApi, type BusinessApi } from '@/api/business-api'
import type {
  BusinessContext,
  BusinessResult,
  EligibilityData,
  EligibilityRequest,
  AvailabilityData
} from '@/api/business-contract'
import { businessError, contextKey } from '@/components/mail-agent/business-format'

export function useBusinessPreviews(
  context: Ref<BusinessContext | null>,
  api: BusinessApi = businessApi
) {
  const eligibility = ref<BusinessResult<EligibilityData> | null>(null)
  const availability = ref<BusinessResult<AvailabilityData> | null>(null)
  const eligibilityLoading = ref(false)
  const availabilityLoading = ref(false)
  const eligibilityError = ref('')
  const availabilityError = ref('')
  let eligibilityGeneration = 0
  let availabilityGeneration = 0
  function reset() {
    ++eligibilityGeneration
    ++availabilityGeneration
    eligibility.value = null
    availability.value = null
    eligibilityError.value = ''
    availabilityError.value = ''
    eligibilityLoading.value = false
    availabilityLoading.value = false
  }
  const dispose = watch(() => contextKey(context.value), reset, { flush: 'sync' })
  async function checkEligibility(input: EligibilityRequest) {
    const current = context.value
    if (!current || eligibilityLoading.value) return
    const key = contextKey(current),
      request = ++eligibilityGeneration
    eligibility.value = null
    eligibilityError.value = ''
    eligibilityLoading.value = true
    try {
      const response = await api.eligibility(current.id, input)
      if (request === eligibilityGeneration && key === contextKey(context.value))
        eligibility.value = response
    } catch (cause) {
      if (request === eligibilityGeneration && key === contextKey(context.value))
        eligibilityError.value = businessError(cause)
    } finally {
      if (request === eligibilityGeneration) eligibilityLoading.value = false
    }
  }
  async function checkAvailability(lineId: string, itemId: string) {
    const current = context.value
    if (!current || availabilityLoading.value) return
    const key = contextKey(current),
      request = ++availabilityGeneration
    availability.value = null
    availabilityError.value = ''
    availabilityLoading.value = true
    try {
      const response = await api.availability(current.id, lineId, itemId)
      if (request === availabilityGeneration && key === contextKey(context.value))
        availability.value = response
    } catch (cause) {
      if (request === availabilityGeneration && key === contextKey(context.value))
        availabilityError.value = businessError(cause)
    } finally {
      if (request === availabilityGeneration) availabilityLoading.value = false
    }
  }
  return {
    eligibility,
    availability,
    eligibilityLoading,
    availabilityLoading,
    eligibilityError,
    availabilityError,
    checkEligibility,
    checkAvailability,
    reset,
    dispose
  }
}
