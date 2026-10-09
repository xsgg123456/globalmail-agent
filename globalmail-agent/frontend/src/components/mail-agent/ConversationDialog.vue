<template>
  <ElDialog
    :model-value="modelValue"
    :title="kind === 'create' ? '新建模拟会话' : '导入历史案例'"
    width="min(560px, 94vw)"
    :close-on-click-modal="false"
    :close-on-press-escape="!busy"
    :show-close="!busy"
    @update:model-value="$emit('update:modelValue', $event)"
  >
    <ElAlert v-if="error" :title="error" type="error" show-icon :closable="false" class="mb-4" />
    <ElForm
      v-if="kind === 'create'"
      :model="form"
      :disabled="busy"
      label-position="top"
      @submit.prevent="submit"
    >
      <ElFormItem label="客户演示邮箱" required :error="errors.sender_email">
        <ElInput
          ref="emailInput"
          v-model="form.sender_email"
          type="email"
          autocomplete="email"
          :maxlength="320"
          placeholder="customer@example.test"
        />
        <p class="text-xs text-g-700 mt-2">同一演示邮箱后续来信进入原会话，使用 .test 邮箱即可。</p>
      </ElFormItem>
      <ElFormItem label="来信主题（可选）" :error="errors.subject"
        ><ElInput v-model="form.subject" :maxlength="500"
      /></ElFormItem>
      <ElFormItem label="首封客户来信（有图片时可留空）" :error="errors.body"
        ><ElInput
          v-model="form.body"
          type="textarea"
          :rows="6"
          :maxlength="20000"
          show-word-limit
          resize="vertical"
      /></ElFormItem>
      <ImageUpload :model-value="form.attachments ?? []" :sender-email="form.sender_email" :disabled="busy"
        @update:model-value="form.attachments = $event" @loading="imageLoading = $event" />
    </ElForm>
    <template v-else>
      <p class="text-sm text-g-800 mb-3"
        >导入客户与客服的真实历史往来，按客户来信逐封回放。不会加载未来事件或参考答案。</p
      >
      <ElButton :loading="sampleLoading" @click="downloadExample" class="mb-4"
        >下载案例样例</ElButton
      >
      <ElForm label-position="top">
        <ElFormItem label="历史案例 JSON 文件" required :error="errors.file">
          <input
            id="mail-case-file"
            type="file"
            accept=".json,application/json"
            aria-label="历史案例 JSON 文件"
            :disabled="busy"
            class="w-full text-sm text-g-800"
            @change="chooseFile"
          />
        </ElFormItem>
      </ElForm>
      <p class="text-xs text-g-700"
        >最多 5
        MiB。请按样例整理邮件，保留发送时间和来源编号；系统会校验文件，不读取文件内的路径或链接。</p
      >
      <ElAlert
        v-if="fileName"
        :title="`已选择：${fileName}`"
        :description="`待校验 ${messageCount} 封邮件；客户身份未验证时作为独立案例回放。`"
        type="info"
        :closable="false"
        class="mt-4"
      />
    </template>
    <p class="text-xs text-g-700 mt-4"
      >关闭窗口会保留未提交内容；上传不调用模型，来信保存后按当前处理权运行，本机模拟回复。</p
    >
    <template #footer>
      <div class="flex justify-end flex-wrap gap-2">
        <ElButton :disabled="busy" @click="$emit('update:modelValue', false)">取消</ElButton>
        <ElButton type="primary" :loading="busy" :disabled="imageLoading" @click="submit">{{
          kind === 'create' ? '创建并保存来信' : '校验并导入'
        }}</ElButton>
      </div>
    </template>
  </ElDialog>
</template>
<script setup lang="ts">
  import { computed, reactive, ref, watch } from 'vue'
  import ImageUpload from './ImageUpload.vue'
  import { imageBindings } from '@/api/attachment-contract'
  import { attachmentApi } from '@/api/attachment-api'
  import type { InputInstance } from 'element-plus'
  import { mailApi } from '@/api/mail-agent'
  import { validateNewConversation, readImportFile, type NewConversationInput } from './mail-inputs'
  const props = defineProps<{
    modelValue: boolean
    kind: 'create' | 'import'
    busy: boolean
    submitCommand: (
      path: '/conversations' | '/imports',
      input: Record<string, unknown>
    ) => Promise<unknown>
  }>()
  const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
  const form = reactive<NewConversationInput>({ sender_email: '', subject: '', body: '' })
  const emailInput = ref<InputInstance>()
  const errors = ref<Record<string, string>>({})
  const error = ref('')
  const imageLoading = ref(false)
  watch(() => form.sender_email, () => {
    const old = form.attachments ?? []
    form.attachments = []
    old.forEach((image) => { void attachmentApi.cancel(image.attachment_id).catch(() => {}) })
  })
  const fileName = ref('')
  const fileData = ref<Record<string, unknown> | null>(null)
  const sampleLoading = ref(false)
  const messageCount = computed(() =>
    Array.isArray(fileData.value?.messages) ? fileData.value.messages.length : 0
  )
  async function chooseFile(event: Event) {
    const input = event.target as HTMLInputElement
    const file = input.files?.[0]
    fileData.value = null
    fileName.value = ''
    errors.value = {}
    error.value = ''
    if (!file) return
    try {
      const data = await readImportFile(file)
      if (typeof data !== 'object' || data === null || Array.isArray(data))
        throw new Error('案例文件应为一个 JSON 对象，请参照样例')
      fileData.value = data as Record<string, unknown>
      fileName.value = file.name
    } catch (cause) {
      errors.value.file = cause instanceof Error ? cause.message : '文件无法读取，请重新选择'
    }
  }
  async function downloadExample() {
    sampleLoading.value = true
    error.value = ''
    try {
      const example = await mailApi.example()
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(example, null, 2)], { type: 'application/json' })
      )
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = '历史案例样例.json'
      anchor.click()
      URL.revokeObjectURL(url)
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '样例下载失败，请重试'
    } finally {
      sampleLoading.value = false
    }
  }
  async function submit() {
    if (props.busy || imageLoading.value) return
    error.value = ''
    if (props.kind === 'create') {
      errors.value = validateNewConversation(form)
      if (Object.keys(errors.value).length) {
        emailInput.value?.focus()
        return
      }
    } else if (!fileData.value) {
      errors.value.file = '请选择符合样例格式的案例文件'
      return
    }
    try {
      const result = await props.submitCommand(
        props.kind === 'create' ? '/conversations' : '/imports',
        props.kind === 'create' ? { ...form, attachments: imageBindings(form.attachments) } : { ...fileData.value }
      )
      if (!result) return
      if (props.kind === 'create') Object.assign(form, { sender_email: '', subject: '', body: '', attachments: [] })
      else {
        fileData.value = null
        fileName.value = ''
      }
      emit('update:modelValue', false)
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : '提交失败，输入已保留，请重试'
    }
  }
</script>
