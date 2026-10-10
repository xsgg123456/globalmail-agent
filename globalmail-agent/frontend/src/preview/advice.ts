import type { DemoBusiness, DemoConversation, DemoFact, DemoOrder, DemoStep } from './types'
import { tool } from './step-builders'

export const financialKinds: DemoBusiness[] = ['refund', 'return', 'replacement', 'spare_part']
export const businessLabels: Record<DemoBusiness, string> = {
  consultation: '产品咨询',
  troubleshooting: '故障排查',
  logistics: '物流查询',
  refund: '退款',
  return: '退货',
  replacement: '换货',
  spare_part: '补寄配件',
  safety: '安全分流'
}
export function detectBusiness(body: string, fallback: DemoBusiness): DemoBusiness {
  if (/burning|smoke|烧焦|冒烟/i.test(body)) return 'safety'
  if (/refund|退款/i.test(body)) return 'refund'
  if (/tracking|shipping status|物流|配送进度/i.test(body)) return 'logistics'
  if (/replacement remote|screws|missing part|补寄|配件|螺丝/i.test(body)) return 'spare_part'
  if (/exchange|replacement scooter|换货|换同款/i.test(body)) return 'replacement'
  if (/return|退货/i.test(body)) return 'return'
  return fallback
}
export function readonlyEvidence(mail: DemoConversation, order: DemoOrder | undefined, at: string) {
  const facts: DemoFact[] = []
  const steps: DemoStep[] = []
  const unknowns: string[] = []
  function query(
    name: string,
    title: string,
    values: [string, string][],
    input: Record<string, string> = { order_id: mail.orderId }
  ) {
    const source = `Mock · ${mail.channel} · ${name}`
    const observed = values.map(([label, value]) => ({ label, value, source, observedAt: at }))
    facts.push(...observed)
    steps.push(tool(name, name, title, input, { source, queried_at: at, facts: observed }))
  }
  if (mail.business === 'safety') {
    facts.push({
      label: '客户陈述',
      value: mail.messages.at(-1)?.body ?? '暂无可核实的客户陈述',
      source: '本轮客户邮件',
      observedAt: at
    })
    unknowns.push('需要客服核查安全风险和后续处理，不能继续普通排障')
    return { facts, steps, unknowns }
  }
  if (mail.business === 'consultation') {
    query(
      'search_knowledge',
      '检索商品适用资料',
      [['资料', '演示产品资料：DEMO-FL-01支持亮度调节']],
      { sku: 'DEMO-FL-01', query: 'brightness adjustment' }
    )
    return { facts, steps, unknowns }
  }
  if (!order || order.lookupError || order.lookupNotFound) {
    steps.push(
      tool(
        'query_order',
        'query_order',
        '查询订单',
        { order_id: mail.orderId },
        {
          source: 'Mock · 订单接口',
          status: !order || order.lookupNotFound ? 'not_found' : 'query_failed',
          queried_at: at
        }
      )
    )
    unknowns.push(
      order && !order.lookupNotFound
        ? '订单查询失败；金额、政策和执行状态尚未核实'
        : '未找到当前会话关联订单；需要客服核对订单号'
    )
    return { facts, steps, unknowns }
  }
  query('query_order', '查询关联订单与商品', [
    ['订单', order.id],
    ['商品', `${order.brand} · ${order.sku}`],
    ['实付', order.paid]
  ])
  switch (mail.business) {
    case 'refund':
      query('query_refund_records', '只读查询已有退款记录', [
        ['退款状态', order.refund],
        ['退款金额', order.refundAmount]
      ])
      unknowns.push(
        '客户银行卡实际到账情况无法从订单记录确认',
        '未接入支付渠道及站外退款核对，不能认定没有其他退款'
      )
      break
    case 'return':
      query('query_return_records', '只读查询平台退货记录', [['退货状态', order.returnStatus]])
      unknowns.push('退货原因、费用及该订单适用规则需客服核对；本预览不生成退货标签')
      break
    case 'replacement':
      query('query_replacement_records', '查询已有换货与补发记录', [['已有记录', order.exchange]])
      query('query_stock', '只读查看同款库存', [['可用数量', String(order.available)]])
      unknowns.push('库存是查询快照，未预留；退件、差价、地址及原请求状态需要客服核对')
      break
    case 'spare_part':
      query('query_compatible_part', '核对配件适用资料', [['配件适配', order.part]])
      query('query_replacement_records', '查询历史补寄记录', [['已有记录', order.exchange]])
      query('query_stock', '只读查看配件库存', [['可用数量', String(order.available)]])
      unknowns.push('客服需确认具体部件、适配和收件地址；库存未预留，未创建补寄单')
      break
    case 'logistics':
      query('query_shipment', '查询包裹最新状态', [
        [
          '物流状态',
          order.shipmentState === 'in_transit'
            ? '运输中'
            : order.shipmentState === 'delivered'
              ? '已送达'
              : '未知'
        ],
        ['补充物流记录（可能含旧扫描）', order.shipment]
      ])
      if (order.shipmentState === 'unknown')
        unknowns.push('物流工具未提供可核实的当前状态，需客服核对承运商记录')
      break
    case 'troubleshooting':
      query(
        'search_knowledge',
        '检索适用排障资料',
        [['资料', '构造排障资料：该型号可重新配对遥控器；客户已换电池']],
        { sku: order.sku, query: 'remote pairing' }
      )
      break
  }
  return { facts, steps, unknowns }
}
export function recommendation(mail: DemoConversation, unknowns: string[]) {
  if (unknowns.some((value) => value.includes('订单查询失败') || value.includes('未找到')))
    return '查询信息不全，先由客服核对订单与业务系统记录，再决定处理；不要等待Agent补齐才接管。'
  if (mail.business === 'logistics' && unknowns.length)
    return '物流依据不足，由客服核对原承运商记录后回复，不把运输或送达状态作为已核实事实。'
  switch (mail.business) {
    case 'refund':
      return '核对已有退款记录和历史承诺，避免重复退款；区分处理中、已处理和客户实际到账，由客服选择解释或进一步核查。'
    case 'return':
      return '先查看原平台已受理的退货请求，客服核对对应渠道和订单规则后给指引，避免重复创建或承诺退款。'
    case 'replacement':
      return '优先核对原平台已有换货请求，客服确认退件、库存和地址，再决定是否继续；不要重复安排换货。'
    case 'spare_part':
      return '客服核对缺件、型号适配、已有补寄和地址，再决定补寄；建议不等于已批准或已发货。'
    case 'safety':
      return '保持人工处理，核查安全风险及后续安排，不把客户陈述当作确定故障根因。'
    default:
      return '根据适用资料或查询事实回复，无法支持下一步时交给客服。'
  }
}
