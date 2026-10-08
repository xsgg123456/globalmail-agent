<template>
  <section aria-label="人工处理">
    <h3 class="text-sm font-medium mb-3">人工处理</h3>
    <template v-if="conversation.lifecycle === 'resolved'">
      <ElAlert
        title="已人工结案"
        description="后续新客户来信将重开本会话。"
        type="success"
        :closable="false"
        show-icon
      />
    </template>
    <template v-else-if="conversation.processing_owner === 'human_wait_customer'">
      <ElAlert
        title="人工回复已完成，等待客户新来信"
        description="不会立即多发一封 Agent 邮件；下一封新来信自动恢复处理资格。"
        type="info"
        :closable="false"
        show-icon
      />
      <ElButton class="mt-3" :disabled="busy" @click="$emit('takeover')">再次人工接管</ElButton>
    </template>
    <template v-else-if="review?.status === 'open'">
      <ElAlert
        :title="review.reason || '客服主动接管'"
        type="warning"
        :closable="false"
        show-icon
        class="mb-3"
      />
      <p class="text-xs text-g-700 mb-3"
        >已接收
        {{ messageCount }} 封可见邮件。模型摘要和业务查询在后续阶段接入，请核对中间邮件区。</p
      >
      <div v-if="stale" class="mb-4" aria-live="polite">
        <ElAlert
          title="接管期间已有新输入，草稿仍保留"
          description="请核对中间邮件区的最新内容，再确认本回复仍适用。"
          type="warning"
          :closable="false"
          show-icon
        />
        <ElButton class="mt-2" :disabled="busy" @click="$emit('acknowledge')"
          >我已核对最新邮件</ElButton
        >
      </div>
      <ElForm
        :model="modelValue"
        :disabled="busy"
        label-position="top"
        @submit.prevent="submit(true)"
      >
        <ElFormItem
          :label="historical ? '本轮审阅回复' : '人工回复正文'"
          required
          :error="errors.reply"
        >
          <ElInput
            ref="replyInput"
            :model-value="modelValue.reply"
            type="textarea"
            :rows="5"
            :maxlength="20000"
            resize="vertical"
            @update:model-value="update('reply', $event)"
          />
        </ElFormItem>
        <ElFormItem label="人工备注（可选）" :error="errors.note">
          <ElInput
            :model-value="modelValue.note"
            type="textarea"
            :rows="3"
            :maxlength="5000"
            resize="vertical"
            @update:model-value="update('note', $event)"
          />
        </ElFormItem>
        <div class="flex flex-wrap gap-2">
          <ElButton :loading="busy" @click="submit(false)">保存草稿</ElButton>
          <ElButton type="primary" native-type="submit" :loading="busy" :disabled="stale">{{
            historical ? '保存本轮审阅' : '完成回复并模拟发送'
          }}</ElButton>
        </div>
      </ElForm>
      <p class="text-xs text-g-700 mt-3">{{
        historical
          ? '审阅结果单独保存，不加入真实历史邮件前缀。'
          : '保存草稿保持接管；完成回复后等待下一封客户来信。'
      }}</p>
    </template>
    <template v-else>
      <p class="text-sm text-g-700 mb-3">可主动接管此会话，接管后 Agent 暂停，新来信继续记录。</p>
      <ElButton :loading="busy" @click="$emit('takeover')">人工接管</ElButton>
    </template>
    <ElCollapse v-if="!historical && history.length" class="mt-4">
      <ElCollapseItem
        v-for="record in history"
        :key="record.id"
        :name="record.id"
        title="人工回复与备注 · 本机模拟"
      >
        <p v-if="record.reply" class="text-sm whitespace-pre-wrap break-words">{{
          record.reply
        }}</p>
        <p v-if="record.note" class="text-sm whitespace-pre-wrap break-words mt-2"
          >备注：{{ record.note }}</p
        >
      </ElCollapseItem>
    </ElCollapse>
    <div v-if="conversation.lifecycle === 'open'" class="border-t-d mt-5 pt-4">
      <p class="text-xs text-g-700 mb-2">只有人工确认才会将客户问题标为已解决。</p>
      <ElButton type="danger" plain :disabled="busy" @click="$emit('close')">人工确认结案</ElButton>
    </div>
  </section>
</template>
<script setup lang="ts">
  import { ref } from 'vue'
  import type { InputInstance } from 'element-plus'
  import type { Conversation, HumanReview } from '@/api/mail-agent-contract'
  import { validateHuman, type HumanInput } from './mail-inputs'
  const props = defineProps<{
    conversation: Conversation
    review: HumanReview | null
    history: HumanReview[]
    modelValue: HumanInput
    historical: boolean
    busy: boolean
    stale: boolean
    messageCount: number
  }>()
  const emit = defineEmits<{
    'update:modelValue': [value: HumanInput]
    takeover: []
    save: []
    complete: []
    close: []
    acknowledge: []
  }>()
  const errors = ref<Record<string, string>>({})
  const replyInput = ref<InputInstance>()
  function update(field: keyof HumanInput, value: string) {
    emit('update:modelValue', { ...props.modelValue, [field]: value })
  }
  function submit(completion: boolean) {
    if (props.busy || (completion && props.stale)) return
    errors.value = validateHuman(props.modelValue, completion)
    if (Object.keys(errors.value).length) {
      replyInput.value?.focus()
      return
    }
    if (completion) emit('complete')
    else emit('save')
  }
</script>
