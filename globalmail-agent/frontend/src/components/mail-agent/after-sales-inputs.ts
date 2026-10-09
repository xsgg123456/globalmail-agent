import type { SimulationEventName, SimulationInput } from '@/api/after-sales-contract'

export const eventLabels: Record<SimulationEventName, string> = {
  create_execution: '建立模拟执行单', processing: '记录处理中', succeeded: '记录实际模拟成功回执',
  failed: '记录失败（保留待核对占用）', unknown: '记录结果未知',
  cancellation_acknowledged: '记录原取消要求的未派送确认',
  create_corrective_execution: '在原申请下建立发件纠错尝试',
  reconciled_not_executed: '确认未执行并解除本次尝试占用', label_created: '建立退货资料或物流标签',
  shipped: '记录承运商已收件', delivered: '记录物流已送达', return_in_transit: '记录客户已寄回',
  received: '记录仓库已收件', inspected: '记录仓库质检结果', inventory_changed: '更新此申请关联规格库存'
}
export interface SimulationForm {
  event: SimulationEventName | ''
  executionId: string
  receiptRef: string
  trackingNumber: string
  carrier: string
  reason: string
  quantity: string
  onHand: string
  confirmedNotExecuted: boolean
  returnAddress: string
  packingInstructions: string
  postageResponsibility: 'customer' | 'merchant'
  prepaidLabelRef: string
  staffId: string
  correctionOf: string
}
export const emptySimulationForm = (): SimulationForm => ({
  event: '', executionId: '', receiptRef: '', trackingNumber: '', carrier: '', reason: '',
  quantity: '', onHand: '', confirmedNotExecuted: false, returnAddress: '', packingInstructions: '',
  postageResponsibility: 'customer', prepaidLabelRef: '', staffId: '', correctionOf: ''
})
function whole(value: string, minimum: number): number | null {
  if (!/^\d+$/.test(value.trim())) return null
  const number = Number(value)
  return Number.isSafeInteger(number) && number >= minimum ? number : null
}
export function simulationInput(form: SimulationForm, allowed: readonly string[], returnDocuments = false) {
  const errors: string[] = []
  if (!form.event || !allowed.includes(form.event)) errors.push('请刷新并选择当前状态允许的操作。')
  const input = { event: form.event } as SimulationInput
  const values = [
    ['execution_id', form.executionId, 160, !['create_execution', 'inventory_changed'].includes(form.event)],
    ['receipt_ref', form.receiptRef, 240, ['succeeded', 'label_created', 'received', 'inspected', 'reconciled_not_executed', 'cancellation_acknowledged', 'shipped', 'delivered'].includes(form.event)],
    ['tracking_number', form.trackingNumber, 160, ['shipped', 'return_in_transit', 'label_created'].includes(form.event)],
    ['carrier', form.carrier, 80, ['shipped', 'label_created', 'return_in_transit'].includes(form.event)],
    ['reason', form.reason, 500, ['failed', 'unknown', 'reconciled_not_executed', 'cancellation_acknowledged', 'inspected'].includes(form.event)],
    ['return_address', form.returnAddress, 1000, returnDocuments],
    ['packing_instructions', form.packingInstructions, 2000, returnDocuments],
    ['prepaid_label_ref', form.prepaidLabelRef, 240, returnDocuments && form.postageResponsibility === 'merchant']
  ] as const
  for (const [key, value, limit, include] of values) {
    if (!include) continue
    if (value.trim().length > limit) errors.push('记录编号或说明超出长度限制。')
    if (value.trim()) input[key] = value.trim()
  }
  if (returnDocuments) {
    input.postage_responsibility = form.postageResponsibility
    if (!input.receipt_ref || !input.return_address || !input.packing_instructions)
      errors.push('退货授权须填写授权编号、模拟退货地址和包装说明。')
    if (form.postageResponsibility === 'merchant' && !input.prepaid_label_ref)
      errors.push('商家承担邮费时须提供实际模拟预付标签编号。')
    if (form.postageResponsibility === 'merchant' && (!input.carrier || !input.tracking_number))
      errors.push('预付标签须填写承运商和运单号。')
  }
  if (form.event === 'succeeded' && !input.receipt_ref) errors.push('成功结果须填写实际模拟回执编号。')
  if (['shipped', 'delivered'].includes(form.event) && !input.receipt_ref) errors.push('承运商收件和送达须填写实际模拟回执编号。')
  if (['shipped', 'return_in_transit', 'label_created'].includes(form.event) && !returnDocuments && (!input.tracking_number || !input.carrier))
    errors.push('交运记录须填写承运商和运单号。')
  if (['failed', 'unknown', 'reconciled_not_executed', 'cancellation_acknowledged'].includes(form.event) && !input.reason)
    errors.push('请填写失败、未知或对账依据。')
  if (['reconciled_not_executed', 'cancellation_acknowledged'].includes(form.event)) {
    if (!input.receipt_ref) errors.push('确认未执行须填写原尝试的核对回执编号。')
    if (!form.confirmedNotExecuted) errors.push('必须明确确认原执行尝试没有发生。')
    input.confirmed_not_executed = form.confirmedNotExecuted
  }
  if (['received', 'inspected'].includes(form.event)) {
    if (!input.receipt_ref) errors.push('收件和质检须填写实际模拟回执编号。')
    if (form.event === 'inspected' && !['passed', 'failed', 'disputed'].includes(form.reason)) errors.push('请选择实际质检结果。')
    const quantity = whole(form.quantity, 1)
    if (quantity === null) errors.push('收件或质检数量须为正整数。')
    else input.quantity = quantity
  }
  if (form.event === 'inventory_changed') {
    const onHand = whole(form.onHand, 0)
    if (onHand === null) errors.push('库存数量须为非负整数。')
    else input.on_hand = onHand
  }
  if (form.event === 'create_corrective_execution') {
    if (![form.staffId, form.correctionOf, form.receiptRef, form.reason].every(value => value.trim()))
      errors.push('发件纠错须提供记录人、原成功执行单、核查回执和原因。')
    Object.assign(input, { staff_id: form.staffId.trim(), correction_of_execution_id: form.correctionOf.trim(), receipt_ref: form.receiptRef.trim(), reason: form.reason.trim() })
  }
  return { errors, input: errors.length ? null : input }
}
