<template>
  <div class="space-y-4">
    <ElAlert
      title="请逐项对照原件，核对前提、步骤、单位、图片含义和适用型号。核对通过后仍未发布。"
      type="info"
      :closable="false"
    />
    <ElAlert
      v-if="stale"
      title="解析内容或适用范围已经变化。备注已保留，请重新核对后再确认。"
      type="warning"
      :closable="false"
    />
    <ElButton v-if="stale" :disabled="busy" @click="acknowledge">已重新核对当前结果</ElButton>
    <ElAlert
      v-for="(diagnostic, index) in detail.diagnostics"
      :key="index"
      :title="`${diagnostic.page ? '第 ' + diagnostic.page + ' 页：' : ''}${diagnostic.message}`"
      :type="diagnostic.blocks_review ? 'error' : 'warning'"
      :closable="false"
      show-icon
    />
    <KnowledgeBlocks
      :blocks="detail.blocks"
      :assets="detail.assets"
      v-model:excluded="excluded"
      :selectable="current && detail.version.status === 'needs_review' && !busy"
    />
    <ElForm label-position="top" :disabled="busy">
      <ElFormItem label="人工核对备注（必填）"
        ><ElInput
          v-model="note"
          type="textarea"
          :rows="3"
          maxlength="5000"
          placeholder="写清核对了哪些步骤、表格、图片和型号；发现什么差异"
      /></ElFormItem>
      <ElFormItem v-if="excluded.length" label="排除原因（必填）"
        ><ElInput
          v-model="reason"
          type="textarea"
          :rows="2"
          maxlength="5000"
          placeholder="说明为什么排除；缺关键图片时，请同时排除依赖图片的步骤"
      /></ElFormItem>
      <ElCheckbox v-model="confirmed"
        >我已对照原件核对保留内容，确认型号范围；已明确排除不能作为完整依据的内容</ElCheckbox
      >
    </ElForm>
    <ElAlert v-if="error" :title="error" type="error" :closable="false" />
    <ElButton
      type="primary"
      :loading="busy"
      :disabled="
        !current ||
        detail.version.status !== 'needs_review' ||
        !detail.source_available ||
        stale ||
        !confirmed ||
        !note.trim() ||
        (excluded.length > 0 && !reason.trim())
      "
      @click="submit"
      >保存人工核对</ElButton
    >
    <p v-if="detail.review" class="whitespace-pre-wrap text-sm"
      >已核对：{{ detail.review.note
      }}<span v-if="detail.review.exclusion_reason"
        >\n排除原因：{{ detail.review.exclusion_reason }}</span
      ></p
    >
  </div>
</template>
<script setup lang="ts">
  import { ref, watch } from 'vue'
  import type { VersionDetail, KnowledgeResult } from '@/api/knowledge-contract'
  import KnowledgeBlocks from './KnowledgeBlocks.vue'
  import { knowledgeError } from './knowledge-labels'
  const props = defineProps<{
    detail: VersionDetail
    current: boolean
    busy: boolean
    execute: (path: string, body: Record<string, unknown>) => Promise<KnowledgeResult>
  }>()
  const note = ref(''),
    reason = ref(''),
    excluded = ref<string[]>([]),
    confirmed = ref(false),
    stale = ref(false),
    error = ref('')
  const snapshot = () => ({
    expected_version: props.detail.version.row_version,
    source_sha256: props.detail.version.source_sha256,
    parse_sha256: props.detail.version.parse_sha256,
    applicability_sha256: props.detail.version.applicability_sha256
  })
  let reviewed = snapshot()
  const digest = () =>
    JSON.stringify([
      props.detail.version.source_sha256,
      props.detail.version.parse_sha256,
      props.detail.version.applicability_sha256,
      props.detail.version.parse_generation
    ])
  watch(digest, () => {
    if (note.value || confirmed.value || excluded.value.length) {
      stale.value = true
      confirmed.value = false
    } else reviewed = snapshot()
  })
  watch(
    () => props.detail.version.row_version,
    () => {
      if (!stale.value) reviewed = snapshot()
    }
  )
  function acknowledge() {
    reviewed = snapshot()
    stale.value = false
    confirmed.value = false
    excluded.value = excluded.value.filter((id) =>
      props.detail.blocks.some((block) => block.id === id)
    )
  }
  async function submit() {
    error.value = ''
    try {
      await props.execute(`/knowledge/versions/${props.detail.version.id}/review`, {
        ...reviewed,
        note: note.value,
        excluded_block_ids: excluded.value,
        exclusion_reason: excluded.value.length ? reason.value : null
      })
    } catch (failure) {
      error.value = knowledgeError(failure)
      stale.value = true
      confirmed.value = false
    }
  }
</script>
