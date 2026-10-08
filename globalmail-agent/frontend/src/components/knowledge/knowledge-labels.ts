import { MailApiError } from '@/api/mail-agent-request'
export const typeLabels: Record<string, string> = {
  manual_pdf: '产品说明 PDF',
  troubleshooting_md: '排障 SOP',
  case_md: '案例卡',
  policy_json: '售后政策'
}
export const stateLabels: Record<string, string> = {
  draft: '草稿',
  parsing: '解析中',
  needs_review: '待人工核对',
  reviewed: '已核对，未发布',
  failed: '失败',
  cancelled: '已取消',
  queued: '排队中',
  running: '正在解析',
  completed: '解析完成',
  interrupted: '已中断'
}
export const stageLabels: Record<string, string> = {
  queued: '等待解析',
  parsing: '读取原件',
  retry_wait: '等待自动重试',
  needs_review: '等待人工核对',
  failed: '解析失败',
  cancelled: '人工取消',
  superseded: '已有新版本'
}
const errors: Record<string, string> = {
  source_unavailable: '原件暂不可用，请恢复完整原件或替换新文件后重试。',
  object_integrity_error: '原件内容与登记记录不一致，请恢复完整原件或替换新文件后重试。',
  object_not_found: '原件登记不存在，请检查资料并替换新文件。',
  parser_configuration_changed: '解析配置已经更新，请重新解析以使用当前配置。',
  local_model_missing: '本机缺少所需模型，请先完成解析环境安装。',
  local_model_mismatch: '本机模型与固定版本不一致，请按安装说明核对模型文件。',
  incomplete_applicability: '还没有完整的型号适用范围，请先修订适用范围。',
  unbound_section: '有内容尚未绑定型号，请修订适用范围或明确排除。',
  incomplete_parse: '有缺页、缺图或未完整解析的内容，请补齐、重新解析，或明确排除相关内容。',
  parser_unavailable: '本机解析环境或模型还未就绪，请查看 parser-worker 的安装说明。',
  invalid_page_scope: '页码范围超出了当前原件，请检查起止页。',
  invalid_sku_scope: '型号与品牌不匹配，请选择资料实际适用的型号。',
  active_pdf_content: '这个 PDF 含自动动作或附件，请上传不含这些内容的知识原件。',
  encrypted_pdf: 'PDF 已加密，请上传可直接读取的原件。',
  pdf_page_limit: 'PDF 必须有 1 至 300 页。',
  file_too_large: '文件不能超过 50 MiB。',
  invalid_pdf: '文件不是有效的 PDF。',
  invalid_knowledge_schema: '文件结构不受支持。请上传知识 Markdown、PDF 或受支持的政策文件。',
  exclusion_reason_required: '排除内容需要写清原因。',
  parse_not_completed: '解析尚未完成，不能保存人工核对。',
  review_digest_mismatch: '内容已经变化，请重新对照当前原件、解析结果和适用范围。',
  version_superseded: '这份资料已有新版本，请选择当前版本操作。',
  parser_timeout: '解析超过 15 分钟，已停止本次进程。',
  parser_failed: '本地解析失败。',
  worker_interrupted: '服务中断，等待重新解析。',
  parser_output_invalid: '解析结果格式不完整，请重新解析。',
  user_cancelled: '任务已由人工取消。',
  new_version: '任务因创建新版本而取消。'
}
export function knowledgeError(error: unknown): string {
  if (!(error instanceof MailApiError))
    return error instanceof Error ? error.message : '操作失败，请重试。'
  if (errors[error.category]) return errors[error.category]
  if (error.status === 409) return '资料或任务状态已经更新，请重新核对后提交。输入已保留。'
  if (error.status === 422)
    return '输入未通过校验，请检查资料格式、来源、页码和型号范围。输入已保留。'
  if (error.status === 404) return '资料或任务不存在，请刷新列表。'
  if (error.status === 503) return '本地依赖暂不可用，请查看运行状态后重试。'
  if (error.category === 'timeout' || error.category === 'network')
    return '请求结果还未确认，请重试同一操作。输入已保留。'
  return '操作失败，请刷新或重试。'
}
export const labelState = (value: string) => stateLabels[value] || '状态待确认'
export const labelStage = (value: string) => stageLabels[value] || '阶段待确认'
export const jobError = (code: string) =>
  errors[code] || '本地解析或依赖检查失败，请重新解析或查看运行状态。'
