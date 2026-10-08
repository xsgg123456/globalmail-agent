import type { BusinessAction, EligibilityRequest } from '@/api/business-contract'
import { currencyDigits, parseMinor } from './business-format'

export interface EligibilityInput {
  action: BusinessAction
  quantity: string
  amount: string
  currency: string
  itemId: string
}
export function eligibilityInput(form: EligibilityInput, lineId: string) {
  const errors: Record<string, string> = {}
  const quantity = Number(form.quantity)
  if (!/^\d+$/.test(form.quantity) || !Number.isSafeInteger(quantity) || quantity < 1)
    errors.quantity = '数量必须为精确范围内的正整数'
  const currency = form.currency.trim().toUpperCase()
  if (currency && currencyDigits(currency) === null)
    errors.currency = '请填写三字母币种代码，例如 USD'
  let amount: number | null = null
  if (form.amount.trim()) {
    amount = parseMinor(form.amount.trim(), currency)
    if (amount === null) errors.amount = '请输入符合币种精度的非负金额，金额须在精确范围内'
  }
  if (form.itemId.trim().length > 100) errors.itemId = '商品或配件编号最多100个字符'
  const request: EligibilityRequest = {
    action: form.action,
    order_line_id: lineId || null,
    quantity,
    amount_minor: amount,
    currency: currency || null,
    item_id: form.itemId.trim() || null
  }
  return { errors, request }
}
