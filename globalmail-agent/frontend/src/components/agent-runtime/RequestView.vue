<template>
  <div class="space-y-5">
    <div v-if="messages.length">
      <div class="flex-cb mb-3"
        ><h4 class="text-sm font-medium">发送给模型的内容</h4
        ><span class="text-xs text-g-700">{{ messages.length }} 条消息 · 实际请求</span></div
      >
      <article v-for="(message, index) in messages" :key="index" class="prompt-block mb-3">
        <div class="flex-cb gap-2 px-4 py-3 border-b-d bg-active-color"
          ><div class="flex items-center gap-2"
            ><ArtSvgIcon
              :icon="message.role === 'system' ? 'ri:shield-keyhole-line' : 'ri:chat-3-line'"
              class="text-theme"
            /><h5 class="text-xs font-medium">{{
              roleLabels[message.role] ?? message.role
            }}</h5></div
          ><span class="text-xs text-g-700 font-mono">{{ message.role }}</span></div
        >
        <p class="p-4 text-sm text-g-900 leading-[1.8] whitespace-pre-wrap break-words">{{
          message.content
        }}</p>
      </article>
    </div>
    <DataBlock
      :value="parameters"
      :title="messages.length ? '请求参数' : '节点输入'"
      :raw-label="messages.length ? '查看参数 JSON' : '查看原始输入 JSON'"
    />
    <ElCollapse v-if="record.tools" class="request-collapse"
      ><ElCollapseItem title="工具定义 · Schema" name="tools">
        <pre class="request-code">{{ pretty(record.tools) }}</pre>
      </ElCollapseItem></ElCollapse
    >
    <ElCollapse v-if="record.response_schema" class="request-collapse"><ElCollapseItem title="输出格式 · Schema" name="schema"><pre class="request-code">{{ pretty(record.response_schema) }}</pre></ElCollapseItem></ElCollapse>
    <ElCollapse v-if="messages.length" class="request-collapse"
      ><ElCollapseItem title="查看完整原始请求 JSON" name="request">
        <pre class="request-code">{{ pretty(input) }}</pre>
      </ElCollapseItem></ElCollapse
    >
  </div>
</template>
<script setup lang="ts">
  import { computed } from 'vue'
  import { asRecord, pretty } from './presentation'
  import DataBlock from './DataBlock.vue'
  const props = defineProps<{ input: unknown }>()
  const roleLabels: Record<string, string> = {
    system: '系统提示词',
    developer: '开发者提示词',
    user: '用户输入与上下文',
    assistant: '模型回复',
    tool: '工具返回'
  }
  const record = computed(() => asRecord(props.input))
  const messages = computed(() =>
    (Array.isArray(record.value.messages) ? record.value.messages : []).map((value) => {
      const message = asRecord(value)
      return {
        role: String(message.role ?? 'message'),
        content: typeof message.content === 'string' ? message.content : pretty(message.content)
      }
    })
  )
  const parameters = computed(() =>
    Object.fromEntries(
      Object.entries(record.value).filter(([key]) => !['messages', 'tools', 'response_schema'].includes(key))
    )
  )
</script>
<style scoped>
  .prompt-block {
    border: 1px solid var(--art-card-border);
    border-radius: 8px;
    overflow: hidden;
  }
  .request-collapse {
    border-top: none;
    --el-collapse-header-height: 40px;
  }
  .request-code {
    padding: 16px;
    background: var(--el-fill-color-light);
    border-radius: 6px;
    white-space: pre-wrap;
    overflow-wrap: anywhere;
    font:
      12px/1.7 ui-monospace,
      SFMono-Regular,
      Consolas,
      monospace;
  }
</style>
