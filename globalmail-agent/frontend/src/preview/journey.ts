import type { DemoState } from './types'
import { appendToState, sendHumanReply, updateMockOrder } from './behavior'

export function seedJourneys(state: DemoState) {
  appendToState(
    state,
    'demo-mail-01',
    'I tried pairing again. The remote still does not work. Can you help with a replacement remote?',
    '2026-10-09T02:35:00Z'
  )
  sendHumanReply(
    state,
    'demo-mail-01',
    'Hi Emma,\n\nI will check the correct remote and any previous replacement record. Could you confirm whether your shipping address is still the same?\n\nCustomer Support',
    '2026-10-09T02:40:00Z'
  )
  appendToState(
    state,
    'demo-mail-01',
    'Yes, the address is the same as order DEMO-1001. Please send the correct remote.',
    '2026-10-09T03:00:00Z'
  )
  updateMockOrder(state, 'DEMO-1001', {
    exchange: '客服在外部业务系统已有补寄记录 DEMO-PART-01；运输中',
    shipment: '补寄包裹 DEMO-REMOTE-TRACK-01 · 运输中',
    shipmentState: 'in_transit'
  })
  sendHumanReply(
    state,
    'demo-mail-01',
    'Hi Emma,\n\nI have checked the shipment arranged by our team. The replacement remote is in transit, with tracking reference DEMO-REMOTE-TRACK-01.\n\nCustomer Support',
    '2026-10-09T03:10:00Z'
  )
  appendToState(
    state,
    'demo-mail-01',
    'Thanks. Can you check the tracking status of the replacement remote?',
    '2026-10-09T03:15:00Z'
  )

  sendHumanReply(
    state,
    'demo-mail-02',
    'Hi Liam,\n\nI am checking the existing refund record for your order. Please do not start another refund request while I verify its status.\n\nCustomer Support',
    '2026-10-09T02:25:00Z'
  )
  appendToState(
    state,
    'demo-mail-02',
    'Thank you. Is the existing refund still processing?',
    '2026-10-09T02:45:00Z'
  )
  updateMockOrder(state, 'DEMO-1002', {
    refund: '支付记录已处理 · DEMO-REFUND-02；不代表客户银行已到账'
  })
  sendHumanReply(
    state,
    'demo-mail-02',
    'Hi Liam,\n\nThe payment record now shows that your USD 89.99 refund has been processed. This does not confirm when your bank will make the funds available.\n\nCustomer Support',
    '2026-10-09T03:00:00Z'
  )
  appendToState(
    state,
    'demo-mail-02',
    'I saw your message, but the money has not appeared in my bank account. Could you check what happens next?',
    '2026-10-09T03:20:00Z'
  )
}
