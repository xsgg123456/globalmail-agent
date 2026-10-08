import type { BusinessChoice, BusinessDetailData } from '@/api/business-contract'
import { formatMinor } from './business-format'

export function choiceLabel(choice: BusinessChoice) {
  const action =
    {
      refund: '退款',
      return: '退货',
      replacement: '换新',
      spare_part: '补发配件',
      logistics: '查询物流'
    }[choice.action ?? ''] ?? '方案未明确'
  const state =
    choice.accepted === true ? '已同意' : choice.accepted === false ? '未同意' : '是否同意未确认'
  return `${action} · ${state}`
}
export function choiceFields(choice: BusinessChoice, data: BusinessDetailData) {
  const order = data.orders.find((row) =>
    row.lines.some((line) => line.line_id === choice.order_line_id)
  )
  const index = order?.lines.findIndex((line) => line.line_id === choice.order_line_id) ?? -1
  const target =
    order && index >= 0
      ? `${order.display_order_number || order.order_id} · 第${index + 1}项 · ${order.lines[index].sku || 'SKU未知'}`
      : '尚未明确对应商品'
  return [
    {
      label: '对应来信',
      value:
        Number.isSafeInteger(choice.source_message_seq) && (choice.source_message_seq ?? 0) > 0
          ? `第${choice.source_message_seq}封来信`
          : '未明确'
    },
    { label: '对应商品', value: target },
    {
      label: '数量',
      value:
        Number.isSafeInteger(choice.quantity) && (choice.quantity ?? 0) > 0
          ? String(choice.quantity)
          : '未明确'
    },
    { label: '金额', value: formatMinor(choice.amount_minor, choice.currency) },
    { label: '商品或配件编号', value: choice.item_id || choice.part_id || '未明确' },
    {
      label: '此次选择的地址版本',
      value: choice.address_version == null ? '未明确' : String(choice.address_version)
    }
  ]
}
