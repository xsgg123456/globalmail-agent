<template>
  <div class="p-4 border-t-d">
    <template v-if="historical">
      <p class="text-sm text-g-700 mb-3"
        >已加载 {{ replay?.position ?? 0 }} /
        {{ replay?.total_customer_messages ?? 0 }} 封客户来信</p
      >
      <p v-if="replay?.as_of" class="text-xs text-g-700 mb-3"
        >当前截点：{{ formatMailTime(replay.as_of) }}</p
      >
      <ElButton
        type="primary"
        :loading="busy"
        :disabled="activeRun || humanReview || replay?.finished"
        @click="$emit('next')"
      >
        {{ replay?.finished ? '回放已结束' : '加载下一封来信' }}
      </ElButton>
      <p class="mt-2 text-xs text-g-700">{{
        activeRun
          ? '当前任务结束后可推进下一截点。'
          : humanReview
            ? '请先完成本轮人工审阅，再推进下一截点。'
            : '回放结束不等于客户问题已解决；未来邮件只在推进后显示。'
      }}</p>
    </template>
    <ElForm
      v-else
      label-position="top"
      :model="modelValue"
      :disabled="busy"
      @submit.prevent="submit"
    >
      <ElFormItem label="来信主题（可选）" :error="errors.subject">
        <ElInput
          :model-value="modelValue.subject"
          :maxlength="500"
          placeholder="留空表示客户未提供主题"
          @update:model-value="update('subject', $event)"
        />
      </ElFormItem>
      <ElFormItem label="客户来信正文" required :error="errors.body">
        <ElInput
          ref="bodyInput"
          :model-value="modelValue.body"
          type="textarea"
          :rows="4"
          :maxlength="20000"
          show-word-limit
          resize="vertical"
          placeholder="保留换行，点击按钮添加来信"
          @update:model-value="update('body', $event)"
        />
      </ElFormItem>
      <div class="flex-cb flex-wrap gap-2">
        <p class="text-xs text-g-700">{{
          humanReview
            ? '人工接管中，新来信只记录，不启动 Agent。'
            : '有效来信保存后自动处理；所有回复仅在本机模拟，不投递真实邮箱。'
        }}</p>
        <ElButton type="primary" native-type="submit" :loading="busy">添加客户来信</ElButton>
      </div>
      <p v-if="resolved" class="text-xs text-g-700 mt-2"
        >新增来信将重开原会话，保留人工结案记录。</p
      >
    </ElForm>
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue'
  import type { InputInstance } from 'element-plus'
  import type { ReplayCursor } from '@/api/mail-agent-contract'
  import { validateIncoming, type IncomingInput } from './mail-inputs'
  import { formatMailTime } from './mail-labels'
  const props = defineProps<{
    modelValue: IncomingInput
    historical: boolean
    replay: ReplayCursor | null
    busy: boolean
    activeRun: boolean
    humanReview: boolean
    resolved: boolean
  }>()
  const emit = defineEmits<{ 'update:modelValue': [value: IncomingInput]; submit: []; next: [] }>()
  const errors = ref<Record<string, string>>({})
  const bodyInput = ref<InputInstance>()
  function update(field: keyof IncomingInput, value: string) {
    emit('update:modelValue', { ...props.modelValue, [field]: value })
  }
  function submit() {
    errors.value = validateIncoming(props.modelValue)
    if (Object.keys(errors.value).length) {
      bodyInput.value?.focus()
      return
    }
    emit('submit')
  }
</script>
