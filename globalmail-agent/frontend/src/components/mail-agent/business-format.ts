import type { BusinessStatus, BusinessResult } from '@/api/business-contract'

export function currencyDigits(currency: string): number | null {
  if (!/^[A-Z]{3}$/.test(currency)) return null
  try {
    return (
      new Intl.NumberFormat('zh-CN', { style: 'currency', currency }).resolvedOptions()
        .maximumFractionDigits ?? null
    )
  } catch {
    return null
  }
}
export function formatMinor(value: unknown, currency: string | null | undefined): string {
  if (value === null || value === undefined) return '未知'
  if (typeof value !== 'number' || !Number.isSafeInteger(value) || value < 0)
    return '金额不可用（超出精确范围或格式有误）'
  const digits = currency ? currencyDigits(currency) : null
  if (digits === null || !currency) return '金额未知（币种未确认）'
  const scale = 10n ** BigInt(digits)
  const integer = BigInt(value)
  const fraction = (integer % scale).toString().padStart(digits, '0')
  return new Intl.NumberFormat('zh-CN', { style: 'currency', currency })
    .formatToParts(integer / scale)
    .map((part) => (part.type === 'fraction' ? fraction : part.value))
    .join('')
}
export function parseMinor(text: string, currency: string): number | null {
  const digits = currencyDigits(currency)
  if (digits === null || !/^\d+(?:\.\d+)?$/.test(text)) return null
  const [whole, fraction = ''] = text.split('.')
  if (fraction.length > digits) return null
  const value = BigInt(whole + fraction.padEnd(digits, '0'))
  return value <= BigInt(Number.MAX_SAFE_INTEGER) ? Number(value) : null
}
export const sourceLabel = (kind: string | null | undefined) =>
  ({
    synthetic: '模拟设定',
    synthetic_scenario: '模拟场景',
    authored_business_journey: '模拟业务初始资料',
    synthetic_replay_test_not_real_history: '合成历史边界案例',
    production_snapshot: '生产快照',
    historical: '历史个案',
    historical_replay: '历史个案',
    mock: '模拟设定',
    authored_simulation_policy: '模拟政策',
    simulation: '本机模拟'
  })[kind ?? ''] ?? '来源未确认'

const fields: Record<string, string> = {
  orders: '订单资料',
  order: '订单资料',
  order_number: '订单号',
  order_line_id: '目标商品',
  target_order_line: '目标商品',
  sku: 'SKU',
  product_name: '商品名称',
  quantity: '数量',
  paid_minor: '实付金额',
  currency: '币种',
  hardware_revision: '硬件版本',
  snapshot_at: '快照时间',
  purchase_at: '购买时间',
  delivered_at: '送达时间',
  policy: '适用政策',
  policy_profile: '适用政策',
  inventory: '库存记录',
  item_id: '商品或配件编号',
  compatibility: '精确适配关系',
  customer_choice: '客户选择',
  address_confirmation: '地址确认',
  source_kind: '来源',
  shipments: '包裹记录',
  updated_at: '更新时间',
  production_order_snapshot: '可信生产订单快照',
  historical_order_snapshot: '历史订单快照',
  order_snapshot: '可用订单快照',
  'inventory.snapshot_at': '库存快照时间',
  'inventory.region_spec': '库存地区规格',
  'inventory.hardware_revision': '库存硬件版本',
  'compatibility.region_spec': '地区适配关系',
  reported_problem: '当前商品的问题依据',
  compensation_ledger: '已有补偿账本',
  compensation_conflict: '既有补偿方案',
  return_window: '退货窗口',
  replacement_window: '换货窗口',
  refund_window: '退款窗口',
  return_receipt: '退件收件记录',
  inspection: '退件质检',
  refund_amount: '退款金额',
  address: '地址确认',
  customer_consent: '客户同意',
  item: '商品或配件',
  policy_currency: '政策币种',
  item_availability: '目标商品库存'
}
export const fieldLabel = (name: string) => fields[name] ?? '未确认的业务字段'
export const missingLabels = (values: string[] = []) =>
  [...new Set(values.map(fieldLabel))].join('、')
const statusLabels: Record<BusinessStatus, string> = {
  ok: '查询完成',
  empty: '当前范围查无记录',
  needs_input: '需要补充或明确资料',
  denied: '查询超出当前会话可访问范围',
  conflict: '资料状态已变化，请刷新后核对',
  unavailable: '当前资料不可用',
  unknown: '字段或业务结果尚未确认',
  error: '业务查询失败，请重试'
}
export function businessStatus<T>(result: BusinessResult<T>): string {
  if (result.reason_code?.startsWith('historical_')) return '当前历史截点没有可用资料'
  if (result.reason_code === 'target_order_line_required') return '请明确当前核对商品'
  if (result.reason_code === 'item_not_registered') return '商品或配件编号未登记，请核对资料'
  if (result.reason_code === 'item_incompatible') return '目标商品或配件不适配当前订单商品'
  if (result.reason_code === 'policy_unavailable') return '没有可用政策，无法核对售后条件'
  return statusLabels[result.status] ?? '业务查询状态未确认'
}
export const statusType = (status: BusinessStatus): 'info' | 'warning' | 'error' =>
  ['error', 'denied'].includes(status) ? 'error' : status === 'ok' ? 'info' : 'warning'
export const businessError = (error: unknown) =>
  error instanceof Error ? error.message : '业务查询失败，输入已保留，请重试。'
export const contextKey = (
  context: { id: string; input_revision: number; row_version: number } | null
) => (context ? `${context.id}:${context.input_revision}:${context.row_version}` : '')
