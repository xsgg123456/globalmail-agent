<template>
  <div
    ref="container"
    class="flex-1 min-h-0 overflow-y-auto p-4 border-t-d"
    aria-label="当前可见邮件"
  >
    <ElEmpty v-if="!messages.length" description="当前截点没有邮件" :image-size="80" />
    <article
      v-for="message in messages"
      :key="message.id"
      class="flex gap-2 items-start w-full mb-6"
      :class="message.sender !== 'customer' ? 'flex-row-reverse' : ''"
    >
      <ElAvatar :size="32" class="shrink-0">{{
        message.sender === 'customer' ? '客' : '服'
      }}</ElAvatar>
      <div class="min-w-0 max-w-[90%] flex-1">
        <div class="flex flex-wrap gap-2 items-center mb-2 text-xs text-g-700">
          <ElTag size="small" :type="message.sender === 'customer' ? 'info' : 'success'">{{
            senderLabels[message.sender]
          }}</ElTag>
          <span>{{ formatMailTime(message.sent_at) }}</span>
          <span>第 {{ message.seq }} 封</span>
        </div>
        <div
          class="py-3 px-4 rounded-md text-sm leading-relaxed text-g-900"
          :class="message.sender === 'customer' ? 'bg-active-color' : 'bg-theme/15'"
        >
          <p class="font-medium mb-2 break-words">{{ message.subject || '（无主题）' }}</p>
          <p class="whitespace-pre-wrap break-words">{{ message.body }}</p>
          <div v-if="message.attachments?.length" class="flex flex-wrap gap-2 mt-3">
            <div v-for="image in message.attachments" :key="image.attachment_id" class="w-28 min-w-0">
              <ElImage v-if="!['revoked', 'cancelled', 'missing', 'unsupported'].includes(image.status)"
                :src="attachmentApi.thumbnailUrl(image)" :alt="image.filename" fit="contain"
                loading="lazy" class="h-20 w-28 rounded border-d">
                <template #placeholder><span class="text-xs">加载中</span></template>
                <template #error><span class="text-xs">无法预览</span></template>
              </ElImage>
              <ElButton size="small" class="w-full mt-1" :title="image.filename"
                :disabled="image.status === 'revoked'" @click="$emit('image', image)">
                <span class="max-w-20 truncate">{{ image.filename }}</span>
              </ElButton>
              <p class="text-xs mt-1 break-words">{{ imageStatusLabels[image.status] ?? image.status }}</p>
            </div>
          </div>
        </div>
      </div>
    </article>
  </div>
</template>
<script setup lang="ts">
  import { ref, watch, nextTick } from 'vue'
  import type { MailMessage } from '@/api/mail-agent-contract'
  import { formatMailTime } from './mail-labels'
  import { imageStatusLabels, type ImageAttachment } from '@/api/attachment-contract'
  import { attachmentApi } from '@/api/attachment-api'
  defineEmits<{ image: [value: ImageAttachment] }>()
  const props = defineProps<{
    messages: MailMessage[]
    conversationId: string
    scrollSignal: number
  }>()
  const container = ref<HTMLElement>()
  const senderLabels = {
    customer: '客户来信',
    historical_staff: '历史客服',
    simulated_agent: '模拟 Agent · 本机已发送',
    simulated_human: '模拟人工 · 本机已发送'
  }
  async function scrollToBottom(force = false) {
    const previous = container.value
    if (
      !force &&
      previous &&
      previous.scrollHeight - previous.scrollTop - previous.clientHeight >= 48
    )
      return
    await nextTick()
    const node = container.value
    if (node) node.scrollTop = node.scrollHeight
  }
  watch(
    () => props.messages.at(-1)?.id,
    () => {
      void scrollToBottom()
    }
  )
  watch(
    () => props.conversationId,
    () => {
      void scrollToBottom(true)
    }
  )
  watch(
    () => props.scrollSignal,
    () => {
      void scrollToBottom(true)
    }
  )
</script>
