import { displayValue, fieldLabel } from '@/components/agent-runtime/presentation'

const labels: Record<string,string> = {
  orders:'订单',lines:'商品',returns:'退件',operations:'售后申请',executions:'执行记录',
  customer_choices:'客户已表达的选择',attempted_steps:'已尝试步骤',status:'状态',inspection:'质检',
  accepted:'客户已同意',policy_authorized:'政策授权已核实',is_realtime:'实时数据',
  snapshot_at:'数据快照时间',updated_at:'更新时间',unknown_fields:'未提供的字段',
  amount_minor:'金额（最小货币单位）',on_hand:'现有库存',reserved:'已预留',available:'可用库存',
  display_order_number:'订单号',channel:'渠道',fulfillment:'履约方式',payment_status:'支付状态',
  paid_minor:'实付（最小货币单位）',refund_status:'退款状态',carrier:'承运商',tracking_number:'追踪号'
}
const hidden = new Set(['source_hash','source_ref','source_kind','source_snapshot','limitation',
  'order_line_id','line_id','order_id','source_message_id','source_message_seq','evidence_ref','version'])

export function observationFields(value: unknown, prefix = ''): {key:string;label:string;value:string}[] {
  if (Array.isArray(value)) {
    if (!value.length) return [{key:prefix,label:prefix,value:'查询未返回记录'}]
    if (value.every(item=>typeof item !== 'object')) return [{key:prefix,label:prefix,value:value.join('、')}]
    return value.flatMap((item,index)=>observationFields(item,`${prefix} ${index+1}`))
  }
  if (typeof value === 'object' && value !== null) return Object.entries(value).filter(([key])=>!hidden.has(key))
    .flatMap(([key,item])=>observationFields(item,[prefix,labels[key]??fieldLabel(key)].filter(Boolean).join(' · ')))
  return [{key:prefix,label:prefix,value:displayValue(value)}]
}
