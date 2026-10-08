<template>
  <ElDialog
    :model-value="true"
    :title="document ? '创建资料新版本' : '新建知识资料'"
    width="min(780px, 96vw)"
    :close-on-click-modal="false"
    :close-on-press-escape="!saving"
    :show-close="!saving"
    @close="emit('close')"
  >
    <ElAlert
      title="当前导入仅作为模拟知识。保存后还需解析、人工核对；资料保持未发布。"
      type="info"
      :closable="false"
      class="mb-4"
    />
    <ElAlert v-if="error" :title="error" type="error" :closable="false" class="mb-4" />
    <ElForm label-position="top" :disabled="saving">
      <ElFormItem label="资料标题（必填）"><ElInput v-model="title" maxlength="500" /></ElFormItem>
      <ElFormItem label="资料类型"
        ><ElSelect v-model="type" :disabled="Boolean(document)" class="!w-full"
          ><ElOption
            v-for="(label, key) in typeLabels"
            :key="key"
            :label="label"
            :value="key" /></ElSelect
      ></ElFormItem>
      <ElFormItem label="品牌"
        ><ElSelect v-model="brand" clearable :disabled="Boolean(document)" class="!w-full"
          ><ElOption
            v-for="item in ['OUTON', 'OUTONLIFE', 'BELEEV']"
            :key="item"
            :label="item"
            :value="item" /></ElSelect
      ></ElFormItem>
      <template v-if="!document">
        <ElFormItem label="资料来源（必填）"
          ><ElInput
            v-model="reference"
            placeholder="例如：项目自编模拟安装说明，不要填内部测试字段"
            maxlength="240"
        /></ElFormItem>
        <ElFormItem label="资料原本可用时间（必填）"
          ><ElDatePicker v-model="availableAt" type="datetime" placeholder="选择时间"
        /></ElFormItem>
      </template>
      <ElFormItem
        v-if="type === 'manual_pdf' || (type === 'policy_json' && !policy)"
        label="原文件（PDF / 政策 JSON）"
      >
        <input
          type="file"
          :accept="type === 'manual_pdf' ? '.pdf' : '.json'"
          aria-label="选择知识原件"
          @change="chooseFile"
        />
        <p v-if="document" class="mt-2 text-sm text-g-700"
          >不选新文件则沿用当前原件；更换 PDF 后请重新检查适用页码。</p
        >
      </ElFormItem>
      <template v-else-if="type !== 'policy_json'">
        <ElFormItem label="导入 Markdown 或受控知识 JSON / JSONL（可选）"
          ><input
            type="file"
            accept=".md,.json,.jsonl"
            aria-label="选择文本知识原件"
            @change="chooseFile"
        /></ElFormItem>
        <ElCheckbox v-if="structuredSource && !file" v-model="reuseSource"
          >沿用当前 JSON / JSONL 原件，仅修订标题或适用范围</ElCheckbox
        >
        <ElFormItem v-if="!file && !reuseSource" label="Markdown 正文（必填）"
          ><ElInput
            v-model="content"
            type="textarea"
            :rows="12"
            placeholder="填写完整正文、前提、步骤和警告"
        /></ElFormItem>
      </template>
      <KnowledgePolicyEditor v-if="type === 'policy_json' && policy" v-model="policy" />
      <ElFormItem v-if="pageRange" label="这份资料包含的原件页码">
        <div class="flex flex-wrap items-center gap-2">
          <ElInputNumber
            v-model="pageRange[0]"
            :min="1"
            :max="pageCount || 300"
            :precision="0"
            aria-label="资料起始页"
          />
          <span>至</span
          ><ElInputNumber
            v-model="pageRange[1]"
            :min="1"
            :max="pageCount || 300"
            :precision="0"
            aria-label="资料结束页"
          />
        </div>
      </ElFormItem>
      <ElFormItem label="解析档位"
        ><ElSelect v-model="profile" class="!w-full"
          ><ElOption
            v-for="item in catalog.parser_profiles.filter((p) =>
              type === 'manual_pdf'
                ? p.id.startsWith('mineru_')
                : p.id === (type === 'policy_json' ? 'policy' : 'markdown')
            )"
            :key="item.id"
            :label="item.label + (item.available ? '' : '（本机未就绪）')"
            :value="item.id"
            :disabled="!item.available" /></ElSelect
      ></ElFormItem>
      <ElFormItem label="型号适用范围（保存核对前必须明确）"
        ><KnowledgeBindings
          v-model="bindings"
          :products="catalog.products"
          :brand="brand || null"
          :page-range="pageRange"
          :sections="sections"
      /></ElFormItem>
    </ElForm>
    <template #footer
      ><div class="flex flex-wrap justify-end gap-2"
        ><ElButton :disabled="saving" @click="emit('close')">取消</ElButton
        ><ElButton v-if="document && error" :disabled="saving" @click="acknowledgeVersion"
          >同步最新版本，保留输入</ElButton
        ><ElButton type="primary" :loading="saving" @click="submit">保存为新版本</ElButton></div
      ></template
    >
  </ElDialog>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import type {
    Binding,
    Catalog,
    KnowledgeDocument,
    KnowledgeResult,
    VersionDetail,
    DocumentType,
    UploadResult
  } from '@/api/knowledge-contract'
  import KnowledgeBindings from './KnowledgeBindings.vue'
  import KnowledgePolicyEditor from './KnowledgePolicyEditor.vue'
  import { typeLabels, knowledgeError } from './knowledge-labels'
  const props = defineProps<{
    document: KnowledgeDocument | null
    detail: VersionDetail | null
    catalog: Catalog
    execute: (path: string, payload: Record<string, unknown>) => Promise<KnowledgeResult>
    upload: (file: File) => Promise<UploadResult>
  }>()
  const emit = defineEmits<{ close: [] }>()
  const title = ref(props.document?.title || ''),
    type = ref<DocumentType>(props.document?.document_type || 'troubleshooting_md'),
    brand = ref(props.document?.brand || '')
  const reference = ref(''),
    availableAt = ref<Date>(),
    content = ref(props.detail?.version.format === 'md' ? props.detail.source_text || '' : '')
  const revision = ref(props.document?.row_version || 0),
    bindings = ref<Binding[]>(
      JSON.parse(JSON.stringify(props.detail?.applicabilities || [])) as Binding[]
    )
  const policy = ref<Record<string, unknown> | null>(
    props.detail?.policy
      ? (JSON.parse(JSON.stringify(props.detail.policy.rules)) as Record<string, unknown>)
      : null
  )
  const profile = ref(props.detail?.version.parser_profile_id || 'markdown'),
    file = ref<File>(),
    pageRange = ref<[number, number] | null>(props.detail?.version.page_range || null)
  const saving = ref(false),
    error = ref('')
  const structuredSource = computed(() =>
    Boolean(
      props.document &&
        props.detail &&
        !props.detail.policy &&
        ['json', 'jsonl'].includes(props.detail.version.format)
    )
  )
  const reuseSource = ref(structuredSource.value),
    pageCount = ref(props.detail?.version.page_count || null)
  let uploadedObject = ''
  const sections = computed(() =>
    Array.from(
      new Map(
        (props.detail?.blocks || []).map((block) => [
          block.section_id,
          {
            id: block.section_id,
            label:
              block.type === 'heading'
                ? block.text
                : `${block.page ? '第 ' + block.page + ' 页 · ' : ''}${block.section_id}`
          }
        ])
      ).values()
    )
  )
  watch(type, (value) => {
    profile.value =
      value === 'manual_pdf' ? 'mineru_basic' : value === 'policy_json' ? 'policy' : 'markdown'
    file.value = undefined
    pageRange.value = null
  })
  function chooseFile(event: Event) {
    const selected = (event.target as HTMLInputElement).files?.[0]
    file.value = selected
    if (selected && type.value === 'manual_pdf') pageRange.value = null
  }
  function acknowledgeVersion() {
    revision.value = props.document?.row_version || 0
    error.value = ''
  }
  async function submit() {
    error.value = ''
    if (
      !title.value.trim() ||
      (!props.document && (!reference.value.trim() || !availableAt.value))
    ) {
      error.value = '请填写标题、来源和资料可用时间。'
      return
    }
    if (
      (!props.document &&
        !file.value &&
        (type.value === 'manual_pdf' || type.value === 'policy_json')) ||
      (!['manual_pdf', 'policy_json'].includes(type.value) &&
        !file.value &&
        !reuseSource.value &&
        !content.value.trim())
    ) {
      error.value = '请提供完整正文或原文件。'
      return
    }
    saving.value = true
    try {
      let objectId: string | undefined
      if (file.value) {
        const uploaded = await props.upload(file.value)
        objectId = uploaded.object_id
        if (uploaded.page_count) {
          pageCount.value = uploaded.page_count
          if (uploadedObject !== objectId) {
            pageRange.value =
              uploaded.sha256 === props.detail?.version.source_sha256
                ? props.detail.version.page_range
                : [1, uploaded.page_count]
            uploadedObject = objectId
          }
          if (
            bindings.value.some(
              (b) =>
                b.page_start === null || b.page_end === null || b.page_end > uploaded.page_count!
            )
          ) {
            error.value = '原件已上传，请为每条适用范围填写起止页，再保存。'
            return
          }
        }
      }
      const payload: Record<string, unknown> = {
        expected_version: revision.value,
        title: title.value,
        parser_profile_id: profile.value,
        applicabilities: bindings.value
      }
      if (objectId) payload.object_id = objectId
      else if (policy.value) payload.content = policy.value
      else if (type.value !== 'manual_pdf' && !reuseSource.value) payload.content = content.value
      if (pageRange.value) payload.page_range = pageRange.value
      if (!props.document)
        Object.assign(payload, {
          document_type: type.value,
          brand: brand.value || null,
          source_reference: reference.value,
          available_at: availableAt.value!.toISOString()
        })
      await props.execute(
        props.document
          ? `/knowledge/documents/${props.document.id}/versions`
          : '/knowledge/documents',
        payload
      )
      emit('close')
    } catch (failure) {
      error.value = knowledgeError(failure)
    } finally {
      saving.value = false
    }
  }
</script>
