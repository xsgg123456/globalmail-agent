import type { ConversationEvent } from '../api/mail-agent-contract'

export interface EventScope {
  id: string
  workspace_id: string
  branch_id: string
  mode: string
  next_seq: number
}
export interface EventStream {
  onopen: ((event: Event) => void) | null
  onerror: ((event: Event) => void) | null
  addEventListener(type: string, callback: (event: MessageEvent<string>) => void): void
  close(): void
}
const record = (value: unknown): value is Record<string, unknown> =>
  typeof value === 'object' && value !== null
const publicMode = (mode: unknown) => (mode === 'simulation' ? 'interactive_simulation' : mode)

export function readConversationEvent(
  raw: string,
  scope: EventScope,
  lastSeq: number
): ConversationEvent | null {
  const data: unknown = JSON.parse(raw)
  if (
    !record(data) ||
    data.conversation_id !== scope.id ||
    data.workspace_id !== scope.workspace_id ||
    data.branch_id !== scope.branch_id ||
    publicMode(data.mode) !== scope.mode ||
    !Number.isSafeInteger(data.seq) ||
    Number(data.seq) < 1 ||
    typeof data.kind !== 'string' ||
    !record(data.payload)
  ) {
    throw new Error('事件作用域或格式不匹配')
  }
  if (Number(data.seq) <= lastSeq) return null
  return data as unknown as ConversationEvent
}

export class ConversationEventSession {
  private source: EventStream | null = null
  private generation = 0
  constructor(private makeSource: (url: string) => EventStream) {}
  connect(
    scope: EventScope,
    onUpdate: (event: ConversationEvent) => void,
    onState: (state: string) => void
  ) {
    this.close()
    const generation = this.generation
    let lastSeq = scope.next_seq
    const source = this.makeSource(
      `/api/v1/conversations/${encodeURIComponent(scope.id)}/events?after_seq=${lastSeq}`
    )
    this.source = source
    onState('连接中')
    source.onopen = () => {
      if (generation === this.generation) onState('已连接')
    }
    source.onerror = () => {
      if (generation === this.generation) onState('连接中断，正在补读重连；可手动刷新')
    }
    source.addEventListener('update', (event) => {
      if (generation !== this.generation) return
      try {
        const parsed = readConversationEvent(event.data, scope, lastSeq)
        if (parsed) {
          lastSeq = parsed.seq
          onUpdate(parsed)
        }
      } catch {
        source.close()
        onState('事件校验失败，请刷新会话后重试订阅')
      }
    })
  }
  close() {
    this.generation += 1
    this.source?.close()
    this.source = null
  }
}
