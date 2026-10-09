<template>
  <ElDrawer :model-value="Boolean(image)" title="客户图片与证据" size="min(520px, 100vw)"
    @update:model-value="!$event && $emit('close')">
    <template v-if="image">
      <p class="text-sm break-all mb-2">{{ image.filename }}</p>
      <ElTag class="mb-3">{{ imageStatusLabels[image.status] ?? image.status }}</ElTag>
      <ElAlert v-if="image.failure_reason" :title="'本轮分析失败：' + image.failure_reason" type="warning" :closable="false" class="mb-3" />
      <p v-if="['failed', 'missing', 'unsupported', 'unreadable'].includes(image.status)" class="text-sm mb-3">
        技术失败请在处理面板显式重试；缺失、不支持或不可读请通过新来信重发清晰的JPEG、PNG或静态WebP。
      </p>
      <ElAlert v-if="error" :title="error" type="error" :closable="false" class="mb-3" />
      <p v-if="loading" role="status">正在读取原图和证据…</p>
      <img v-if="url" :src="url" :alt="image.filename" class="w-full max-h-96 object-contain mb-4" />
      <p v-if="page?.coverage" class="text-sm mb-2">覆盖：{{ page.coverage }}</p>
      <p v-if="page?.quality" class="text-sm mb-2">质量：{{ page.quality }}</p>
      <ElEmpty v-if="page && !page.items.length" description="尚未产生有效分析或人工修订" :image-size="60" />
      <div v-for="item in page?.items ?? []" :key="item.evidence_id" class="border-d rounded p-3 mb-3 text-sm">
        <ElTag size="small" :type="item.manual ? 'success' : 'info'">{{ labels[item.kind] ?? item.kind }}{{ item.manual ? ' · 人工修订' : '' }}</ElTag>
        <p class="whitespace-pre-wrap break-words mt-2">{{ item.value ?? item.raw_text ?? '未知' }}</p>
        <p v-if="item.raw_text" class="text-xs text-g-700 mt-1">原始读数：{{ item.raw_text }}</p>
        <p v-if="item.ambiguous_characters?.length" class="text-xs text-g-700">歧义：{{ item.ambiguous_characters.join('、') }}</p>
        <p v-if="item.reason" class="text-xs mt-1">修订依据：{{ item.reason }}</p>
        <p class="text-xs text-g-700 mt-2">位置：整图{{ item.location.type !== 'full_image' ? '（见来源位置记录）' : '' }}</p>
      </div>
      <template v-if="image.status !== 'revoked' && conversation.mode === 'interactive_simulation'">
        <p v-if="!manual" class="text-xs text-g-700 mb-3">请先在处理面板显式接管会话，再更正图片证据。</p>
        <ElForm v-if="manual && !['missing', 'unsupported'].includes(image.status)" label-position="top" @submit.prevent="correct">
          <ElFormItem label="更正类型"><ElSelect v-model="kind" class="w-full">
            <ElOption label="候选字段" value="field_candidate" /><ElOption label="可见观察" value="observation" />
            <ElOption label="原因推测" value="hypothesis" />
          </ElSelect></ElFormItem>
          <ElFormItem v-if="kind === 'field_candidate'" label="字段"><ElSelect v-model="fieldKey" class="w-full">
            <ElOption v-for="(label, key) in fields" :key="key" :label="label" :value="key" />
          </ElSelect></ElFormItem>
          <ElFormItem label="人工更正内容"><ElInput v-model="value" type="textarea" :maxlength="2000" /></ElFormItem>
          <ElFormItem label="核对依据"><ElInput v-model="reason" type="textarea" :maxlength="1000" /></ElFormItem>
          <ElButton type="primary" :loading="busy" native-type="submit">保存更正，保持人工接管</ElButton>
        </ElForm>
        <div class="border-t-d mt-6 pt-4">
          <ElButton type="danger" plain :loading="busy" @click="revoke">撤销这张图片证据</ElButton>
          <p class="text-xs text-g-700 mt-2">撤销后立即禁止读取及旧结果提交。完整副本删除在后续阶段实现。</p>
        </div>
      </template>
    </template>
  </ElDrawer>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref, watch } from 'vue'
  import { ElMessageBox } from 'element-plus'
  import { attachmentApi } from '@/api/attachment-api'
  import { imageStatusLabels, type ImageAttachment, type VisualEvidencePage } from '@/api/attachment-contract'
  import type { Conversation } from '@/api/mail-agent-contract'
  import { PendingCommands, MailApiError } from '@/api/mail-agent-request'
  const props = defineProps<{ image: ImageAttachment | null; conversation: Conversation }>()
  const emit = defineEmits<{ close: []; changed: [] }>()
  const page = ref<VisualEvidencePage | null>(null)
  const url = ref('')
  const loading = ref(false), busy = ref(false), error = ref('')
  const kind = ref('observation'), value = ref(''), reason = ref('')
  const fieldKey = ref('order_number')
  const fields = { order_number: '订单号', sku: 'SKU', model: '型号', error_code: '错误码', other: '其他' }
  const pending = new PendingCommands()
  let generation = 0
  const labels: Record<string, string> = { field_candidate: '候选字段', observation: '可见观察', hypothesis: '原因推测', uncertainty: '不确定项', risk_flag: '疑似安全风险' }
  const manual = computed(() => ['human_review', 'human_wait_customer'].includes(props.conversation.processing_owner))
  function release() { if (url.value) URL.revokeObjectURL(url.value); url.value = '' }
  async function load() {
    const image = props.image, current = ++generation
    release(); page.value = null; error.value = ''; loading.value = false
    if (!image || image.status === 'revoked') return
    loading.value = true
    try {
      const [blob, evidence] = await Promise.allSettled([attachmentApi.preview(image, false), attachmentApi.evidence(image)])
      if (current !== generation) return
      if (blob.status === 'fulfilled') url.value = URL.createObjectURL(blob.value)
      if (evidence.status === 'fulfilled') page.value = evidence.value
      error.value = [blob, evidence].filter((r): r is PromiseRejectedResult => r.status === 'rejected')
        .map((r) => r.reason instanceof Error ? r.reason.message : '读取失败').join('；')
    } catch (cause) { if (current === generation) error.value = cause instanceof Error ? cause.message : '证据读取失败' }
    finally { if (current === generation) loading.value = false }
  }
  watch(() => [props.image?.attachment_id, props.image?.evidence_epoch, props.image?.status, props.conversation.id], load, { immediate: true })
  watch(() => [props.image?.attachment_id, props.conversation.id], () => {
    value.value = ''; reason.value = ''; kind.value = 'observation'; fieldKey.value = 'order_number'
  })
  async function mutate(action: 'corrections' | 'revoke') {
    const image = props.image, current = generation
    if (!image || busy.value) return
    const payload = { expected_version: props.conversation.row_version, expected_input_revision: props.conversation.input_revision,
      evidence_revision: page.value?.evidence_revision ?? image.evidence_epoch, ...(action === 'corrections' ? {
        kind: kind.value, field_key: fieldKey.value, value: value.value, reason: reason.value } : {}) }
    const path = image.attachment_id + action
    const prepared = pending.prepare(path, payload, payload)
    busy.value = true; error.value = ''
    try {
      await attachmentApi.mutate(image.attachment_id, action, prepared.payload, prepared.key)
      pending.complete(path)
      if (current === generation) { emit('changed'); emit('close'); value.value = ''; reason.value = '' }
    } catch (cause) {
      if (cause instanceof MailApiError && cause.status === 409) {
        pending.complete(path); if (current === generation) emit('changed')
      }
      if (current === generation) error.value = cause instanceof Error ? cause.message : '操作失败，内容已保留'
    } finally { busy.value = false }
  }
  function correct() {
    if (!manual.value) return
    if (!value.value.trim() || !reason.value.trim()) { error.value = '请填写更正内容和核对依据'; return }
    void mutate('corrections')
  }
  async function revoke() {
    try {
      await ElMessageBox.confirm('撤销后图片及其派生证据立即失效，当前自动处理将停止。确认撤销？', '撤销图片证据',
        { type: 'warning', confirmButtonText: '确认撤销', cancelButtonText: '取消' })
      await mutate('revoke')
    } catch { /* 用户取消 */ }
  }
  onBeforeUnmount(() => { generation++; release() })
</script>
