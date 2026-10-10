import type { DemoConversation, DemoFact } from './types'
import { financialKinds } from './advice'

export function draftFor(mail: DemoConversation, facts: DemoFact[], blocked: boolean) {
  const name = mail.customer.split(' ')[0]
  const details = facts
    .filter((fact) => !['订单', '商品', '实付'].includes(fact.label))
    .map((fact) => fact.value)
    .join('; ')
  let text: string
  if (blocked)
    text =
      'We need to verify your order details before confirming the next steps. Could you share your order number and the store where you purchased the item?'
  else if (mail.business === 'refund') {
    const status = facts.find((item) => item.label === '退款状态')?.value ?? ''
    const state = status.includes('已处理')
      ? 'processed'
      : status.includes('处理中')
        ? 'processing'
        : status.includes('失败')
          ? 'failed'
          : 'not yet verified'
    const amount = facts.find((item) => item.label === '退款金额')?.value
    text = `The existing refund record shows ${amount && amount !== '未知' ? amount + ' as ' : 'a status of '}${state}. This does not confirm that the funds have appeared in your bank account. We are checking the next steps for your case.`
  } else if (mail.business === 'return')
    text = /未查到|未找到|未知/.test(details)
      ? 'We are checking the return records and the rules that apply to your order before confirming the next steps.'
      : 'The order records contain return information. We will check its current instructions before confirming what you need to do next.'
  else if (mail.business === 'replacement')
    text = /未查到|未找到|未知/.test(details)
      ? 'We are checking the replacement records and available options before confirming any arrangement.'
      : 'The order records contain replacement information. We will check its status and the available options before confirming any further arrangement.'
  else if (mail.business === 'spare_part')
    text =
      'Thank you for letting us know. We will verify the exact part and the compatible model before confirming a replacement arrangement.'
  else if (mail.business === 'safety')
    text =
      'Thank you for reporting this. Please stop using the light and keep it disconnected while our support team reviews your case.'
  else if (mail.business === 'logistics')
    text =
      facts.find((item) => item.label === '物流状态')?.value === '已送达'
        ? 'The latest tracking record shows a delivered scan. Please let us know if you have not received the parcel so our support team can check further.'
        : facts.find((item) => item.label === '物流状态')?.value === '运输中'
          ? 'The latest shipping record shows that your parcel is in transit. An exact delivery date has not been confirmed.'
          : 'The latest tracking status needs further verification. Our support team will review the available record before confirming the next steps.'
  else if (mail.business === 'consultation')
    text =
      'The demonstration product information for DEMO-FL-01 lists brightness adjustment as a supported feature.'
  else
    text =
      'Please switch the lamp off, turn it back on and follow the pairing instructions for your model. Let us know whether the lamp flashes and the remote responds.'
  if (/[\u4e00-\u9fff]/.test(mail.messages.at(-1)?.body ?? '')) {
    text = blocked
      ? '当前订单信息尚未核实，客服会继续核对；请补充订单号及购买渠道。'
      : mail.business === 'refund'
        ? `查询到的退款记录为：${details}。这不代表银行卡已经到账，具体下一步由客服核对后确认。`
        : mail.business === 'logistics'
          ? `最新物流记录为：${details}。未核实的信息和后续处理会由客服进一步确认。`
          : financialKinds.includes(mail.business)
            ? '我们会核对订单、已有售后记录及适用方案，再确认具体安排。当前尚未确认退款、换货或补寄执行。'
            : mail.business === 'safety'
              ? '请停止使用并保持断电，客服会进一步核查情况。'
              : mail.business === 'consultation'
                ? '演示产品资料显示，DEMO-FL-01支持亮度调节。'
                : '请根据该型号适用的资料操作，并告知操作结果；如仍未恢复，我们会进一步核查。'
    return `${name}，你好：\n\n${text}\n\n客服团队`
  }
  return `Hi ${name},\n\n${text}\n\nBest regards,\nCustomer Support`
}
