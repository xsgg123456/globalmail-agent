<template>
  <div class="mb-4">
    <label class="text-sm text-g-800 block mb-2">客户图片（可选，最多4张）</label>
    <input type="file" accept="image/jpeg,image/png,image/webp" multiple aria-label="客户图片"
      :disabled="disabled || loading" class="w-full text-sm" @change="choose" />
    <p class="text-xs text-g-700 mt-2">单张10 MiB，合计20 MiB；上传预览不启动分析，图片随来信提交。</p>
    <p v-if="loading" class="text-sm mt-2" role="status">正在上传图片…</p>
    <ElAlert v-if="error" :title="error" type="error" :closable="false" class="mt-2" />
    <div class="flex flex-wrap gap-3 mt-3">
      <div v-for="image in modelValue" :key="image.attachment_id" class="w-28 min-w-0">
        <img v-if="urls[image.attachment_id]" :src="urls[image.attachment_id]" :alt="image.filename"
          class="h-20 w-28 object-contain rounded border-d" />
        <p class="text-xs break-all mt-1">{{ image.filename }}</p>
        <ElButton size="small" :disabled="disabled || loading" @click="remove(image)">移除暂存</ElButton>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { onBeforeUnmount, ref, watch } from 'vue'
  import { attachmentApi } from '@/api/attachment-api'
  import { validateImages, type ImageAttachment } from '@/api/attachment-contract'
  import { MailApiError } from '@/api/mail-agent-request'
  import { PendingImageUploads } from './pending-image-uploads'
  const props = defineProps<{ modelValue: ImageAttachment[]; conversationId?: string; senderEmail?: string; disabled?: boolean }>()
  const emit = defineEmits<{ 'update:modelValue': [value: ImageAttachment[]]; loading: [value: boolean] }>()
  const loading = ref(false)
  const error = ref('')
  const urls = ref<Record<string, string>>({})
  let generation = 0
  const pending = new PendingImageUploads()
  const message = (cause: unknown) => cause instanceof Error ? cause.message : '图片请求失败，输入已保留'
  function release() {
    Object.values(urls.value).forEach(URL.revokeObjectURL)
    urls.value = {}
  }
  watch(() => [props.conversationId, props.senderEmail], () => { generation++; release(); error.value = '' })
  watch(() => props.modelValue, async (images) => {
    const current = generation
    for (const image of images) {
      if (urls.value[image.attachment_id]) continue
      try {
        const blob = await attachmentApi.preview(image)
        if (current === generation) urls.value[image.attachment_id] = URL.createObjectURL(blob)
      } catch (cause) { if (current === generation) error.value = message(cause) }
    }
    for (const id of Object.keys(urls.value)) if (!images.some((image) => image.attachment_id === id)) {
      URL.revokeObjectURL(urls.value[id]); delete urls.value[id]
    }
  }, { immediate: true })
  async function choose(event: Event) {
    const input = event.target as HTMLInputElement
    const files = Array.from(input.files ?? [])
    input.value = ''
    if (!files.length || loading.value) return
    error.value = validateImages(files, props.modelValue)
    if (error.value) return
    if (!props.conversationId && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(props.senderEmail ?? '')) {
      error.value = '请先填写有效客户邮箱，再上传图片'; return
    }
    const current = generation
    const images = [...props.modelValue]
    const target = props.conversationId ? { conversation_id: props.conversationId } : { sender_email: props.senderEmail }
    loading.value = true; emit('loading', true)
    try {
      for (const file of files) {
        const prepared = await pending.prepare(file, target)
        let image: ImageAttachment
        try { image = await attachmentApi.upload(file, target, prepared.key) }
        catch (cause) {
          if (cause instanceof MailApiError && cause.status && cause.status < 500) pending.complete(prepared.identity)
          throw cause
        }
        pending.complete(prepared.identity)
        if (current !== generation) { await attachmentApi.cancel(image.attachment_id); return }
        images.push(image)
        emit('update:modelValue', [...images])
      }
    } catch (cause) { if (current === generation) error.value = message(cause) }
    finally { loading.value = false; emit('loading', false) }
  }
  async function remove(image: ImageAttachment) {
    try {
      await attachmentApi.cancel(image.attachment_id)
      emit('update:modelValue', props.modelValue.filter((row) => row.attachment_id !== image.attachment_id))
    } catch (cause) { error.value = message(cause) }
  }
  onBeforeUnmount(() => { generation++; release() })
</script>
