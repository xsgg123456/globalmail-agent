import { reactive } from 'vue'
import { createConversations, createOrders } from './fixtures'
import { createIncomingRun } from './run-builder'
import { seedJourneys } from './journey'
import { appendToState } from './behavior'
import type { DemoState } from './types'

export function createPreviewState(): DemoState {
  const state: DemoState = {
    conversations: createConversations(),
    orders: createOrders(),
    runs: [],
    drafts: {},
    readPositions: {},
    viewedRuns: {},
    selectedMail: 'demo-mail-02'
  }
  for (const mail of state.conversations) {
    state.runs.push(
      createIncomingRun(
        mail,
        state.orders.find((item) => item.id === mail.orderId),
        mail.messages[0]!,
        1
      )
    )
  }
  seedJourneys(state)
  return state
}
// 只在隔离预览路由加载。记录和数据全部构造，不调用正式业务/模型API。
export const demo = reactive(createPreviewState())
export function resetDemo() {
  Object.assign(demo, createPreviewState())
}
export function appendDemoIncoming(conversationId: string, body: string, at?: string) {
  return appendToState(demo, conversationId, body, at)
}
