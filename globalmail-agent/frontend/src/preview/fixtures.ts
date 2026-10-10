import type { DemoBusiness, DemoConversation, DemoOrder } from './types'

const cases: [string, string, string, DemoBusiness, string, string][] = [
  [
    'Emma Wilson',
    'OUTON',
    '独立站',
    'troubleshooting',
    'Floor lamp stops responding to the remote',
    'My lamp works with the foot switch, but the remote does not work. I tried new batteries. My order is DEMO-1001.'
  ],
  [
    'Liam Carter',
    'BELEEV',
    '独立站',
    'refund',
    'When will my refund arrive?',
    'I returned my scooter, order DEMO-1002. I would like the refund we discussed. Can you check the status?'
  ],
  [
    'Olivia Chen',
    'OUTONLIFE',
    '独立站',
    'safety',
    'Burning smell from my desk light',
    'There is a burning smell near the adapter. I unplugged the light. My order is DEMO-1003. What should I do?'
  ],
  [
    'Ava Martin',
    'OUTON',
    'Amazon FBA',
    'return',
    'I would like to return my lamp',
    'I bought the lamp on Amazon, order DEMO-1004. It is not suitable for my room. I started a return on Amazon. What should I do next?'
  ],
  [
    'Noah Brown',
    'BELEEV',
    'Amazon FBM',
    'replacement',
    'Can I exchange my scooter for the same model?',
    'My scooter has a problem. I want to exchange it for the same model, order DEMO-1005.'
  ],
  [
    'Lucas Taylor',
    'OUTON',
    '独立站',
    'consultation',
    'Does this lamp support dimming?',
    'Does the OUTON DEMO-FL-01 floor lamp support brightness adjustment?'
  ],
  [
    'Sophia Davis',
    'OUTONLIFE',
    '独立站',
    'logistics',
    'Where is my parcel?',
    'Could you check the shipping status of order DEMO-1007?'
  ],
  [
    'Mia Anderson',
    'BELEEV',
    '独立站',
    'spare_part',
    'The installation screws are missing',
    'The screws were missing from my scooter package. My order is DEMO-1008. Can you send the correct screws?'
  ]
]
export function createConversations(): DemoConversation[] {
  return cases.map(([customer, brand, channel, business, subject, body], index) => {
    const suffix = String(index + 1).padStart(2, '0')
    return {
      id: `demo-mail-${suffix}`,
      customer,
      email: `${customer.split(' ')[0]!.toLowerCase()}@preview.invalid`,
      brand,
      channel,
      business,
      subject,
      status: '等待客户',
      owner: 'agent',
      persistentHuman: false,
      awaitingCustomer: false,
      orderId: `DEMO-${1001 + index}`,
      runId: `demo-run-${suffix}`,
      messages: [
        {
          id: `demo-message-${suffix}`,
          seq: 1,
          sender: 'customer',
          subject,
          body: `Hi,\n\n${body}\n\n${customer.split(' ')[0]}`,
          sent_at: `2026-10-09T02:${String(12 + index * 2).padStart(2, '0')}:00Z`
        }
      ]
    }
  })
}
export function createOrders(): DemoOrder[] {
  return cases.map(([, brand, channel], index) => ({
    id: `DEMO-${1001 + index}`,
    brand,
    channel,
    sku: brand === 'BELEEV' ? 'DEMO-SC-02' : 'DEMO-FL-01',
    product: brand === 'BELEEV' ? '折叠滑板车' : '调光灯具',
    paid: brand === 'BELEEV' ? 'USD 89.99' : 'USD 54.99',
    shipment:
      index === 6 ? '运输中；最后扫描：2026-10-08，目的地分拨中心' : '原包裹已送达 · 2026-10-02',
    shipmentState: index === 6 ? 'in_transit' : 'delivered',
    refund:
      index === 1 ? '处理中；记录 DEMO-REFUND-02' : '当前Mock查询未找到退款记录，未核实站外退款',
    refundAmount: index === 1 ? 'USD 89.99' : '未知',
    returnStatus:
      index === 3
        ? 'Amazon退货请求已受理；标签来自原平台，本预览无可下载标签'
        : index === 1
          ? '退件已收件；质检情况未知'
          : '未查到退货记录',
    exchange:
      index === 4
        ? '原平台已有换货请求 DEMO-EXCHANGE-05，尚未发出'
        : '当前Mock查询未找到换货/补发记录',
    part: index === 0 ? '演示资料确认 DEMO-REMOTE-01 与本灯具适配' : '螺丝规格与型号兼容性尚未确认',
    available: index === 4 ? 8 : 24,
    lookupError: false,
    lookupNotFound: false
  }))
}
