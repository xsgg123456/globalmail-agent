import { computed, reactive, ref } from 'vue'
import { mailApi, type MailApi } from '@/api/mail-agent'
import type { ConversationDetail, Conversation, ActionResult } from '@/api/mail-agent-contract'
import { MailApiError, PendingCommands } from '@/api/mail-agent-request'
import { validateHuman } from '@/components/mail-agent/mail-inputs'
import type { HumanInput, IncomingInput } from '@/components/mail-agent/mail-inputs'
import { imageBindings } from '@/api/attachment-contract'
export function useMailWorkbench(api: MailApi = mailApi) {
  const items = ref<Conversation[]>([])
  const mode = ref('')
  const state = ref('')
  const cursors = ref<(string | undefined)[]>([undefined])
  const page = ref(1)
  const nextCursor = ref<string | null>(null)
  const selectedId = ref('')
  const detail = ref<ConversationDetail | null>(null)
  const listLoading = ref(false)
  const detailLoading = ref(false)
  const busy = ref(false)
  const listError = ref('')
  const detailError = ref('')
  const actionError = ref('')
  const actionNotice = ref('')
  const scrollSignal = ref(0)
  const incomingInputs = reactive<Record<string, IncomingInput>>({})
  const humanInputs = reactive<Record<string, HumanInput>>({})
  const humanRevisions = reactive<Record<string, number>>({})
  const reviewIds = reactive<Record<string, string>>({})
  const riskContexts: Record<string, string> = {}
  const incomingInput = computed(
    () => incomingInputs[selectedId.value] ?? { subject: '', body: '' }
  )
  const humanInput = computed(
    () => humanInputs[selectedId.value] ?? { reply: '', note: '', risk_decision: 'keep_active' }
  )
  const humanStale = computed(() =>
    Boolean(
      detail.value?.review &&
        humanRevisions[selectedId.value] !== detail.value.conversation.input_revision
    )
  )
  const conversation = computed(() => detail.value?.conversation ?? null)
  const pending = new PendingCommands()
  let listGeneration = 0
  let detailGeneration = 0

  const errorMessage = (error: unknown) =>
    error instanceof Error ? error.message : '本地服务请求失败，请重试。'
  async function refreshList() {
    const generation = ++listGeneration
    listLoading.value = true
    listError.value = ''
    try {
      const result = await api.list(mode.value, state.value, cursors.value[page.value - 1])
      if (generation !== listGeneration) return
      items.value = result.items
      nextCursor.value = result.next_cursor
    } catch (error) {
      if (generation === listGeneration) listError.value = errorMessage(error)
    } finally {
      if (generation === listGeneration) listLoading.value = false
    }
  }
  async function refreshDetail(showLoading = false) {
    const id = selectedId.value
    if (!id) return
    const generation = ++detailGeneration
    if (showLoading) detailLoading.value = true
    detailError.value = ''
    try {
      const result = await api.detail(id)
      if (id !== selectedId.value || generation !== detailGeneration) return
      detail.value = result
      if (!humanInputs[id])
        humanInputs[id] = {
          reply: result.review?.draft ?? '',
          note: result.review?.note ?? '',
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
          humanInputs[id].reply = result.review.draft
          humanInputs[id].note = result.review.note
        }
        reviewIds[id] = result.review.id
        humanRevisions[id] = result.review.input_revision
      }
      if (!incomingInputs[id]) incomingInputs[id] = { subject: '', body: '' }
    } catch (error) {
      if (id === selectedId.value && generation === detailGeneration)
        detailError.value = errorMessage(error)
    } finally {
      if (generation === detailGeneration) detailLoading.value = false
    }
  }
  async function select(id: string) {
    if (humanInputs[selectedId.value]) humanInputs[selectedId.value].risk_decision = 'keep_active'
    if (humanInputs[id]) humanInputs[id].risk_decision = 'keep_active'
    selectedId.value = id
    detail.value = null
    actionError.value = ''
    actionNotice.value = ''
    await refreshDetail(true)
  }
  async function filter(field: 'mode' | 'state', value: string) {
    if (field === 'mode') mode.value = value
    else state.value = value
    page.value = 1
    cursors.value = [undefined]
    await refreshList()
  }
  async function paginate(next: boolean) {
    if (next && nextCursor.value) {
      cursors.value[page.value] = nextCursor.value
      page.value += 1
    } else if (!next && page.value > 1) page.value -= 1
    else return
    await refreshList()
  }
  async function command(
    path: string,
    input: Record<string, unknown>,
    notice: string,
    reviewVersion = false,
    method = 'POST'
  ) {
    const snapshot = detail.value
    if (!snapshot || busy.value) return false
    const id = snapshot.conversation.id
    const version = reviewVersion ? snapshot.review?.version : snapshot.conversation.row_version
    if (version === undefined) return false
    const payload: Record<string, unknown> = { ...input, expected_version: version }
    const prepared = pending.prepare(path, input, payload)
    busy.value = true
    actionError.value = ''
    actionNotice.value = ''
    try {
      await api.command(path, prepared.payload, prepared.key, method)
      pending.complete(path)
      if (id === selectedId.value) {
        actionNotice.value = notice
        await refreshDetail()
      }
      await refreshList()
      return true
    } catch (error) {
      if (error instanceof MailApiError && error.status === 409) {
        pending.complete(path)
        if (id === selectedId.value) await refreshDetail()
      }
      if (id === selectedId.value) actionError.value = errorMessage(error)
      return false
    } finally {
      busy.value = false
    }
  }
  async function createOrImport(
    path: '/conversations' | '/imports',
    input: Record<string, unknown>
  ): Promise<ActionResult | null> {
    if (busy.value) return null
    const prepared = pending.prepare(path, input, { ...input, expected_version: 0 })
    busy.value = true
    try {
      const result = await api.command(path, prepared.payload, prepared.key)
      pending.complete(path)
      await filter('mode', '')
      if (result.conversation_id) await select(result.conversation_id)
      actionNotice.value =
        path === '/imports'
          ? '案例校验通过，已导入真实历史前缀。'
          : '模拟来信已保存，后续处理按当前会话状态进行。'
      return result
    } catch (error) {
      if (error instanceof MailApiError && error.status === 409) pending.complete(path)
      throw error
    } finally {
      busy.value = false
    }
  }
  async function append() {
    const id = selectedId.value
    const input = incomingInput.value
    const payload = { ...input, ...(input.attachments ? { attachments: imageBindings(input.attachments) } : {}) }
    const success = await command(`/conversations/${id}/messages`, payload, '客户来信已保存。')
    if (success) {
      incomingInputs[id] = { subject: '', body: '' }
      scrollSignal.value += 1
    }
  }
  async function completeHuman() {
    const id = selectedId.value
    const input = humanInput.value
    const errors = validateHuman(input, true)
    if (Object.keys(errors).length) {
      actionError.value = Object.values(errors)[0]
      return
    }
    const historical = detail.value?.conversation.mode === 'historical_replay'
    const success = await command(
      `/conversations/${id}/human-replies`,
      {
        body: input.reply,
        note: input.note,
        risk_decision: input.risk_decision ?? 'keep_active',
        expected_input_revision: humanRevisions[id]
      },
      historical
        ? '本轮审阅已独立保存，没有加入真实历史邮件。'
        : '人工回复已在本机模拟发送，等待客户新来信。'
    )
    if (success) {
      humanInputs[id] = { reply: '', note: '', risk_decision: 'keep_active' }
      scrollSignal.value += 1
    }
  }
  const saveHuman = () =>
    command(
      `/human-reviews/${detail.value?.review?.id}`,
      {
        draft: humanInput.value.reply,
        note: humanInput.value.note,
        expected_input_revision: humanRevisions[selectedId.value]
      },
      '人工草稿已保存，仍保持接管。',
      true,
      'PATCH'
    )
  const takeover = () =>
    command(
      `/conversations/${selectedId.value}/takeover`,
      { reason: '客服主动接管' },
      '已接管会话，Agent 自主处理已暂停。'
    )
  const nextReplay = () =>
    command(`/conversations/${selectedId.value}/replay/next`, {}, '当前历史截点已更新。')
  const close = () =>
    command(
      `/conversations/${selectedId.value}/close`,
      { note: humanInput.value.note },
      '已人工确认结案。'
    )
  const stop = (id: string) => command(`/runs/${id}/stop`, {}, '当前任务已停止。')
  const retry = (id: string) =>
    command(`/runs/${id}/retry`, {}, '已显式建立同一处理轮次的重试任务。')
  return {
    items,
    mode,
    state,
    page,
    nextCursor,
    selectedId,
    detail,
    conversation,
    listLoading,
    detailLoading,
    busy,
    listError,
    detailError,
    actionError,
    actionNotice,
    incomingInput,
    humanInput,
    humanStale,
    scrollSignal,
    refreshList,
    refreshDetail,
    select,
    filter,
    paginate,
    createOrImport,
    append,
    completeHuman,
    saveHuman,
    takeover,
    nextReplay,
    close,
    stop,
    retry,
    setIncoming: (value: IncomingInput) => {
      incomingInputs[selectedId.value] = value
    },
    setHuman: (value: HumanInput) => {
      humanInputs[selectedId.value] = value
    },
    acknowledgeHuman: () => {
      if (detail.value) humanRevisions[selectedId.value] = detail.value.conversation.input_revision
    }
  }
}
