import type { BusinessDetailData, BusinessRecord } from '@/api/business-contract'
import { formatMinor, sourceLabel, missingLabels } from './business-format'
import { formatMailTime } from './mail-labels'

export const actionLabels: Record<string, string> = {
  refund: '退款',
  return: '退货',
  replacement: '换货',
  spare_part: '补寄配件',
  logistics: '物流查件'
}
const states: Record<string, string> = {
  created: '已创建，履约尚未确认',
  requested: '申请已受理',
  pending: '等待处理',
  accepted: '已受理',
  waiting: '等待条件',
  awaiting_choice: '等待客户选择',
  awaiting_execution: '等待执行',
  processing: '处理中',
  in_progress: '处理中',
  completed: '记录已完成，需核对执行回执',
  succeeded: '执行回执成功',
  failed: '失败',
  unknown: '结果未知',
  cancelled: '已取消',
  shipped: '回执显示已发出',
  in_transit: '运输中',
  delivered: '轨迹显示已送达',
  delayed: '运输延误',
  lost: '物流报告遗失',
  disputed: '结果有争议',
  delivery_exception: '配送异常',
  investigation_requested: '已申请查件',
  awaiting_result: '等待结果',
  label_created: '面单已创建，尚未确认交运',
  not_shipped: '尚未发出',
  received: '已收件',
  inspecting: '质检中'
}
const purposes: Record<string, string> = {
  original: '原订单包裹',
  return: '寄回包裹',
  replacement: '换货补发包裹',
  spare_part: '配件补发包裹',
  reshipment: '补发包裹'
}
export const recordStatus = (value: unknown) =>
  typeof value === 'string' ? (states[value] ?? '状态未确认') : '状态未知'
const textValue = (value: unknown) => (typeof value === 'string' && value ? value : '未知')
export function recordTitle(record: BusinessRecord, kind: string) {
  if (kind === 'shipments') return purposes[textValue(record.purpose)] ?? '包裹用途未确认'
  if (kind === 'returns') return '退件与质检'
  if (kind === 'executions') return '独立执行回执'
  return `${actionLabels[textValue(record.kind)] ?? '售后'}申请`
}
export function recordFields(
  record: BusinessRecord,
  kind: string
): { label: string; value: string }[] {
  const identity =
    record.operation_id ?? record.execution_id ?? record.parcel_id ?? record.return_id
  const rows = [
    {
      label: '记录编号',
      value: textValue(
        kind === 'executions'
          ? record.execution_id
          : kind === 'shipments'
            ? record.parcel_id
            : kind === 'returns'
              ? record.return_id
              : identity
      )
    },
    { label: '状态', value: recordStatus(record.status) },
    { label: '来源', value: sourceLabel(record.source_kind) },
    { label: '更新时间', value: formatMailTime(record.updated_at ?? null) },
    {
      label: '快照时间',
      value: formatMailTime(typeof record.snapshot_at === 'string' ? record.snapshot_at : null)
    },
    {
      label: '实时性',
      value:
        record.is_realtime === true
          ? '实时查询'
          : record.is_realtime === false
            ? '快照资料'
            : '未知'
    }
  ]
  const optional = [
    ['operation_id', '关联申请'],
    ['execution_id', '关联执行单'],
    ['tracking_number', '运单号'],
    ['carrier', '承运商'],
    ['part_id', '配件编号']
  ]
  for (const [key, label] of optional)
    if (record[key]) rows.push({ label, value: textValue(record[key]) })
  if ('quantity' in record)
    rows.push({
      label: '数量',
      value: Number.isSafeInteger(record.quantity) ? String(record.quantity) : '未知'
    })
  if ('amount_minor' in record)
    rows.push({
      label: '金额',
      value: formatMinor(
        record.amount_minor,
        typeof record.currency === 'string' ? record.currency : null
      )
    })
  if (kind === 'returns') {
    if ('inspected_quantity' in record)
      rows.push({
        label: '质检合格数量',
        value: Number.isSafeInteger(record.inspected_quantity)
          ? String(record.inspected_quantity)
          : '未知'
      })
    rows.push({
      label: '收件',
      value: record.received === true ? '已收件' : record.received === false ? '尚未收件' : '未知'
    })
    rows.push({
      label: '质检',
      value:
        { passed: '已通过', failed: '未通过', pending: '等待质检', disputed: '质检有争议' }[
          textValue(record.inspection)
        ] ?? '未知'
    })
  }
  if (Array.isArray(record.unknown_fields)) {
    const fields = record.unknown_fields.filter(
      (field): field is string => typeof field === 'string'
    )
    if (fields.length) rows.push({ label: '资料缺口', value: missingLabels(fields) })
  }
  return rows
}
export function recordsForOrder(data: BusinessDetailData, orderId: string) {
  const operations = data.operations.filter((record) => record.order_id === orderId)
  const operationIds = new Set(operations.map((record) => record.operation_id))
  return {
    operations,
    executions: data.executions.filter(
      (record) =>
        record.order_id === orderId ||
        (record.operation_id && operationIds.has(record.operation_id))
    ),
    shipments: data.shipments.filter((record) => record.order_id === orderId),
    returns: data.returns.filter((record) => record.order_id === orderId)
  }
}
export function recordsForLine(data: BusinessDetailData, orderId: string, lineId: string) {
  const belongs = (record: BusinessRecord) =>
    record.order_id === orderId && (record.order_line_id ?? record.line_id) === lineId
  return {
    operations: data.operations.filter(belongs),
    executions: data.executions.filter(belongs),
    shipments: data.shipments.filter(belongs),
    returns: data.returns.filter(belongs)
  }
}
