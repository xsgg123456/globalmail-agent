<template>
  <section aria-label="当前案件记忆" class="border-t-d pt-4 mb-5">
    <h3 class="text-sm font-medium mb-2">当前案件记忆</h3>
    <p v-if="!detail.issues.length && !detail.facts.length" class="text-sm text-g-700"
      >尚无已保存的案件事项或事实。</p
    >
    <ElCollapse v-else>
      <ElCollapseItem
        name="issues"
        :title="`案件事项 ${detail.issues.length} · 事实 ${detail.facts.length}`"
      >
        <p v-for="issue in detail.issues" :key="issue.id" class="text-sm break-words mb-2"
          >{{ issue.issue_key }} · {{ issue.status }} · 第 {{ issue.version }} 版</p
        >
        <article v-for="fact in detail.facts" :key="fact.id" class="border-d rounded p-3 mb-3">
          <ElTag size="small" type="info">{{ factKinds[fact.kind] || fact.kind }}</ElTag>
          <p class="text-sm whitespace-pre-wrap break-words mt-2">{{ fact.value }}</p>
          <p class="text-xs text-g-700 break-all mt-2"
            >来源消息：{{ fact.source_message_id || '未关联消息' }} · 可见序号
            {{ fact.visible_seq }}</p
          >
        </article>
      </ElCollapseItem>
    </ElCollapse>
  </section>
</template>
<script setup lang="ts">
  import type { ConversationDetail } from '@/api/mail-agent-contract'
  defineProps<{ detail: ConversationDetail }>()
  const factKinds: Record<string, string> = {
    customer_report: '客户陈述',
    historical_claim: '历史声称',
    human_decision: '人工决定',
    model_inference: '模型推断',
    tool_fact: '工具事实',
    visual_observation: '视觉观察'
  }
</script>
