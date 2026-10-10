import type { MailMessage } from '@/api/mail-agent-contract'
import type { DemoConversation, DemoOrder, DemoRun } from './types'
import { businessLabels, financialKinds, readonlyEvidence, recommendation } from './advice'
import { draftFor } from './reply-drafts'
import { model, check, commit, timeSteps } from './step-builders'

export function demoTime(at: string) {
  return new Date(Date.parse(at) + 8 * 3600_000).toISOString().slice(11, 19)
}
export function snapshotMessages(messages: MailMessage[]) {
  return messages.map(({ id, seq, sender, body }) => ({ id, seq, sender, body }))
}
export function createIncomingRun(
  mail: DemoConversation,
  order: DemoOrder | undefined,
  trigger: MailMessage,
  round: number
) {
  const persistent = mail.persistentHuman || financialKinds.includes(mail.business)
  const { facts, steps, unknowns } = readonlyEvidence(mail, order, trigger.sent_at)
  const missing = unknowns.some((item) => item.includes('订单查询失败') || item.includes('未找到'))
  const internal = persistent || mail.business === 'safety' || unknowns.length > 0
  const mode = internal
    ? mail.owner === 'human' && persistent
      ? 'human-assist'
      : 'handoff'
    : 'automatic'
  const runId =
    round === 1 ? mail.runId : `demo-run-${mail.id.slice(-2)}-${String(round).padStart(2, '0')}`
  const draft = draftFor(mail, facts, missing)
  const suggestion = recommendation(mail, unknowns)
  const correspondence = snapshotMessages(mail.messages)
  const run: DemoRun = {
    id: runId,
    conversationId: mail.id,
    round,
    mode,
    triggerMessageId: trigger.id,
    trigger: `客户来信 · 第${mail.messages.filter((item) => item.sender === 'customer').length}封`,
    title: `${businessLabels[mail.business]} · ${mode === 'automatic' ? '有据回复' : mode === 'handoff' ? '只读核查并转人工' : '持续人工 · 内部辅助'}`,
    status: internal ? (mode === 'handoff' ? '待人工接管' : '人工接管中') : '等待客户',
    startedAt: demoTime(trigger.sent_at),
    duration: '6.2s · 演示',
    tokens: 2806,
    steps: [
      model(
        'understand',
        '理解当前来信与历史往来',
        '只使用本轮触发时已可见的邮件，包含此前人工回复',
        {
          correspondence,
          trigger_message_id: trigger.id,
          owner: mail.owner,
          persistent_human: persistent
        },
        {
          intent: mail.business,
          order_id: mail.orderId,
          next: internal ? 'internal_review' : 'readonly_reply'
        }
      ),
      check(
        'authority',
        '处理权限校验',
        internal ? '仅只读查询和内部辅助；客服决定并发送' : '普通问题可根据查询结果回复',
        {
          authority: internal ? 'human' : 'agent',
          automatic_reply: !internal,
          business_writes: false
        }
      ),
      ...steps,
      model(
        'review',
        internal ? '整理给客服的建议与草稿' : '核验回复依据',
        internal
          ? '事实、缺口、建议和未发送草稿分开保存，不创建售后申请'
          : '核验客户回复与资料或查询事实一致',
        { correspondence, facts, unknowns, target: internal ? '客服内部' : '客户邮件' },
        { facts, unknowns, recommendation: suggestion, draft, automatic_reply: !internal },
        `【预览构造的思考摘要】\n${suggestion}\n${internal ? '处理权属于客服。即使客户确认方案或客服已回复，也不获得售后写入或自动发送权限。' : '依据本轮可见资料起草回复，不承诺未核实的业务结果。'}`
      ),
      commit(
        'commit',
        internal ? '保存内部建议和未发送草稿；无Agent客户邮件' : '保存演示客户回复，等待反馈',
        {
          target: internal ? 'internal_advice' : 'customer_message',
          automatic_reply: !internal,
          business_writes: false
        }
      )
    ]
  }
  timeSteps(run)
  if (internal) {
    mail.adviceStale = false
    mail.owner = 'human'
    mail.persistentHuman = persistent
    mail.awaitingCustomer = false
    mail.advice = {
      runId,
      triggerMessageId: trigger.id,
      reason: persistent
        ? '商业售后需要客服决定'
        : mail.business === 'safety'
          ? '安全风险需要客服核查'
          : '查询信息不足',
      facts,
      unknowns,
      recommendation: suggestion,
      draft
    }
  } else {
    mail.owner = 'agent'
    mail.advice = undefined
    const reply: MailMessage = {
      id: `${runId}-reply`,
      seq: mail.messages.length + 1,
      sender: 'simulated_agent',
      subject: `Re: ${mail.subject}`,
      body: draft,
      sent_at: new Date(Date.parse(trigger.sent_at) + 10_000).toISOString()
    }
    mail.messages.push(reply)
    run.outputMessageId = reply.id
  }
  mail.status = run.status
  mail.runId = run.id
  return run
}
