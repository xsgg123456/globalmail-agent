<template>
  <section aria-label="本轮理解" class="space-y-3">
    <h4 class="text-sm font-medium">诉求与候选事实</h4>
    <p v-if="result.revisions?.length" class="text-xs text-g-700"
      >当前理解 · 已修订 {{ result.revisions.length }} 次，候选选择仍须业务核验</p
    >
    <p class="text-xs text-g-700"
      >回复语言：{{ result.language || '未知' }} · 候选信息以工具与人工核对为准</p
    >
    <article
      v-for="(intent, index) in result.intents"
      :key="index"
      class="border-d rounded p-3 space-y-2"
    >
      <p class="text-sm font-medium break-words"
        >{{ index + 1 }}. {{ businessLabels[intent.business_type] || intent.business_type }}</p
      >
      <p class="text-sm break-words"
        >订单：{{ intent.order_number || '未明确' }} · 商品：{{ intent.target_item || '未明确' }}</p
      >
      <p v-if="intent.requested_solution" class="text-sm break-words"
        >希望方案：{{ intent.requested_solution }}</p
      >
      <p v-if="intent.condition" class="text-sm break-words">条件：{{ intent.condition }}</p>
      <ElTag size="small" :type="intent.consent === 'explicit' ? 'success' : 'info'">{{
        consentLabels[intent.consent]
      }}</ElTag>
      <details v-if="intent.sources.length" class="text-xs text-g-700">
        <summary>查看原文来源</summary>
        <p
          v-for="(source, sourceIndex) in intent.sources"
          :key="sourceIndex"
          class="whitespace-pre-wrap break-words mt-2"
          >{{ source.quote }}<br /><span class="break-all">来源：{{ source.message_id }}</span></p
        >
      </details>
    </article>
    <p v-if="!result.intents.length" class="text-sm text-g-700">本轮没有识别到新的业务诉求。</p>
    <ElAlert
      v-if="result.missing_information.length"
      :title="`待补信息：${result.missing_information.join('、')}`"
      type="warning"
      :closable="false"
    />
    <ElAlert
      v-if="result.risk_flags.length"
      :title="`风险标记：${result.risk_flags.map((flag) => flag.kind).join('、')}`"
      type="warning"
      :closable="false"
    />
    <ElCollapse
      v-if="result.facts.length || result.order_candidates.length || result.risk_flags.length"
    >
      <ElCollapseItem name="sources" title="候选事实与来源记录">
        <pre class="text-xs font-inherit whitespace-pre-wrap break-words">{{
          jsonText({
            order_candidates: result.order_candidates,
            facts: result.facts,
            risk_flags: result.risk_flags
          })
        }}</pre>
      </ElCollapseItem>
    </ElCollapse>
    <ElCollapse v-if="result.revisions?.length">
      <ElCollapseItem name="initial" title="查看初始理解">
        <pre class="text-xs font-inherit whitespace-pre-wrap break-words">{{
          jsonText(result.initial_understanding)
        }}</pre>
      </ElCollapseItem>
      <ElCollapseItem name="revisions" title="理解修订与来源">
        <article
          v-for="revision in result.revisions"
          :key="revision.revision"
          class="space-y-2 mb-3"
        >
          <p class="text-sm font-medium break-words"
            >修订 {{ revision.revision }}：{{ revision.change_reason }}</p
          >
          <pre class="text-xs font-inherit whitespace-pre-wrap break-words">{{
            jsonText({
              intents: revision.understanding.intents,
              missing_information: revision.understanding.missing_information
            })
          }}</pre>
          <details class="text-xs text-g-700">
            <summary>查看修订依据原文</summary>
            <p
              v-for="(source, index) in revision.sources"
              :key="index"
              class="whitespace-pre-wrap break-words mt-2"
              >{{ source.quote }}<br /><span class="break-all"
                >来源：{{ source.message_id }}</span
              ></p
            >
          </details>
        </article>
      </ElCollapseItem>
    </ElCollapse>
  </section>
</template>
<script setup lang="ts">
  import type { UnderstandingResult } from '@/api/agent-run-contract'
  import { jsonText } from './agent-run-format'
  defineProps<{ result: UnderstandingResult }>()
  const consentLabels = {
    none: '未表示执行同意',
    conditional: '条件性要求',
    explicit: '明确选择或同意',
    declined: '明确拒绝'
  }
  const businessLabels: Record<string, string> = {
    product_inquiry: '产品咨询',
    troubleshooting: '产品排障',
    shipment: '物流查询',
    refund: '退款诉求',
    return: '退货诉求',
    replacement: '换货诉求',
    parts: '补件诉求',
    other: '其他诉求'
  }
</script>
