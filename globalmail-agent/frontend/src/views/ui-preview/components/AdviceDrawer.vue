<template>
  <ElDrawer
    v-model="open"
    title="Agent 给客服的建议"
    size="min(520px, 100vw)"
    :destroy-on-close="true"
  >
    <template v-if="advice">
      <ElAlert
        title="仅内部可见 · 草稿未经客服发送不会进入邮件往来"
        type="info"
        :closable="false"
        class="mb-5"
      />
      <p class="text-sm font-medium mb-2">{{ advice.reason }}</p>
      <p class="text-xs text-g-700 mb-5">{{ advice.runId }} · 本轮查询来源均为构造数据</p>
      <h3 class="text-sm font-medium mb-3">查到的事实</h3>
      <ElEmpty v-if="!advice.facts.length" description="尚无可核实的业务事实" :image-size="50" />
      <div
        v-for="fact in advice.facts"
        :key="`${fact.label}:${fact.source}`"
        class="mb-3 p-3 rounded-md bg-active-color"
      >
        <p class="text-xs text-g-700 mb-1">{{ fact.label }}</p>
        <p class="text-sm break-words">{{ fact.value }}</p>
        <p class="text-xs text-g-700 mt-2 break-words"
          >{{ fact.source }} · {{ formatMailTime(fact.observedAt) }}</p
        >
      </div>
      <h3 class="text-sm font-medium mt-5 mb-3">尚未确认</h3>
      <ul class="text-sm text-g-700 space-y-2 list-disc pl-5">
        <li v-for="item in advice.unknowns" :key="item">{{ item }}</li>
        <li v-if="!advice.unknowns.length">没有额外缺口；商业决策仍由客服完成。</li>
      </ul>
      <h3 class="text-sm font-medium mt-5 mb-3">处理建议</h3>
      <p class="text-sm leading-relaxed">{{ advice.recommendation }}</p>
      <h3 class="text-sm font-medium mt-5 mb-3">可选回复草稿</h3>
      <p class="text-sm leading-relaxed whitespace-pre-wrap p-3 rounded-md bg-active-color">{{
        advice.draft
      }}</p>
      <p v-if="!canAdopt" class="text-xs text-g-700 mt-3"
        >本轮已人工回复、信息有更新或已结案，请先核对最新往来。</p
      >
    </template>
    <template #footer>
      <ElButton @click="open = false">关闭</ElButton>
      <ElButton
        type="primary"
        :disabled="!advice || !canAdopt"
        @click="emit('adopt', advice!.draft)"
        >采用草稿，交由我发送</ElButton
      >
    </template>
  </ElDrawer>
</template>
<script setup lang="ts">
  import type { DemoAdvice } from '@/preview/types'
  import { formatMailTime } from '@/components/mail-agent/mail-labels'
  const open = defineModel<boolean>({ default: false })
  defineProps<{ advice?: DemoAdvice; canAdopt: boolean }>()
  const emit = defineEmits<{ adopt: [body: string] }>()
</script>
