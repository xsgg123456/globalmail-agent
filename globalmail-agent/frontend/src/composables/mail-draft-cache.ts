import { reactive } from 'vue'
import type { ConversationDetail } from '@/api/mail-agent-contract'
import type { HumanInput, IncomingInput } from '@/components/mail-agent/mail-inputs'

export function createMailDraftCache() {
  const incomingInputs = reactive<Record<string, IncomingInput>>({})
  const humanInputs = reactive<Record<string, HumanInput>>({})
  const humanRevisions = reactive<Record<string, number>>({})
  const reviewIds: Record<string, string> = {}
  const riskContexts: Record<string, string> = {}
  function clear(id: string) {
    delete humanInputs[id]
    delete incomingInputs[id]
    delete humanRevisions[id]
    delete reviewIds[id]
    delete riskContexts[id]
  }
  function hydrate(id: string, result: ConversationDetail) {
      if (!humanInputs[id])
        humanInputs[id] = {
          reply: result.review?.staff_draft ?? '',
          note: result.review?.staff_note ?? '',
          risk_decision: 'keep_active'
        }
      const riskContext = JSON.stringify([
        result.review?.id,
        result.conversation.input_revision,
        result.active_risks
          ?.filter((risk) => risk.status === 'active')
          .map((risk) => risk.id)
          .sort()
      ])
      if (riskContexts[id] !== riskContext) humanInputs[id].risk_decision = 'keep_active'
      riskContexts[id] = riskContext
      if (result.review && reviewIds[id] !== result.review.id) {
        if (!humanInputs[id].reply.trim() && !humanInputs[id].note.trim()) {
          humanInputs[id].reply = result.review.staff_draft ?? ''
          humanInputs[id].note = result.review.staff_note ?? ''
        }
        reviewIds[id] = result.review.id
        if (humanRevisions[id] === undefined || (!humanInputs[id].reply.trim() && !humanInputs[id].note.trim()))
          humanRevisions[id] = result.review.input_revision
      }
      if (!incomingInputs[id]) incomingInputs[id] = { subject: '', body: '' }
  }
  return { incomingInputs, humanInputs, humanRevisions, clear, hydrate }
}
