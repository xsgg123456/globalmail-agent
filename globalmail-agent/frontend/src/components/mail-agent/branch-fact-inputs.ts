export const factLabels = { inventory_snapshot: '库存快照', address_confirmation: '客户地址确认', original_shipment: '原订单物流更新', inspection_correction: '更正未通过或有争议的质检', return_documents: '更新退件资料', service_note: '人工业务核查记录' }
export const emptyBranchFact = () => ({ event: 'inventory_snapshot' as keyof typeof factLabels, sourceId: crypto.randomUUID(), orderLine: '', version: '0', staff: '', receipt: '', reason: '', item: '', region: '', hardware: '', snapshot: '', onHand: '', message: '', quote: '', confirmed: false, resource: '', resourceVersion: '', carrier: '', tracking: '', status: 'shipped', inspection: 'passed', quantity: '', address: '', packing: '', postage: 'customer', prepaid: '' })
export function branchFactInput(form: ReturnType<typeof emptyBranchFact>) {
  const integer = (value: string, min: number) => /^\d+$/.test(value.trim()) && Number.isSafeInteger(Number(value)) && Number(value) >= min
  if (![form.orderLine, form.staff, form.receipt, form.reason].every(value => value.trim()) || !integer(form.version, 0))
    return { error: '请填写订单行、记录人、回执、依据和非负原事实版本。', input: null }
  const input: Record<string, unknown> = { event: form.event, source_event_id: form.sourceId, order_line_id: form.orderLine.trim(), expected_business_version: Number(form.version), business_version: Number(form.version) + 1, staff_id: form.staff.trim(), receipt_ref: form.receipt.trim(), reason: form.reason.trim() }
  if (form.event === 'inventory_snapshot') {
    if (![form.item, form.region, form.hardware, form.snapshot].every(value => value.trim()) || !integer(form.onHand, 0) || !/(Z|[+-]\d{2}:\d{2})$/.test(form.snapshot) || !Number.isFinite(Date.parse(form.snapshot)))
      return { error: '库存须填写精确商品、市场、硬件版本、含时区的时间及实有数量。', input: null }
    Object.assign(input, { item_id: form.item.trim(), region_spec: form.region.trim(), hardware_revision: form.hardware.trim(), snapshot_at: form.snapshot, on_hand: Number(form.onHand) })
  }
  if (form.event === 'address_confirmation') {
    if (!form.message.trim() || !form.quote.trim()) return { error: '地址记录须提供客户消息及逐字原话。', input: null }
    Object.assign(input, { confirmed: form.confirmed, selection_ref: { message_id: form.message.trim(), quote: form.quote } })
  }
  if (['original_shipment', 'inspection_correction', 'return_documents'].includes(form.event)) {
    if (!form.resource.trim() || !integer(form.resourceVersion, 1)) return { error: '请核对原资源编号和正整数版本。', input: null }
    Object.assign(input, { resource_id: form.resource.trim(), expected_resource_version: Number(form.resourceVersion) })
  }
  if (['original_shipment', 'return_documents'].includes(form.event)) Object.assign(input, { carrier: form.carrier.trim() || null, tracking_number: form.tracking.trim() || null })
  if (form.event === 'original_shipment') input.status = form.status
  if (form.event === 'inspection_correction') {
    if (!integer(form.quantity, 1)) return { error: '实际受检数量须为正整数。', input: null }
    Object.assign(input, { inspection: form.inspection, quantity: Number(form.quantity) })
  }
  if (form.event === 'return_documents') Object.assign(input, { return_address: form.address.trim(), packing_instructions: form.packing.trim(), postage_responsibility: form.postage, prepaid_label_ref: form.prepaid.trim() || null })
  return { error: '', input }
}
