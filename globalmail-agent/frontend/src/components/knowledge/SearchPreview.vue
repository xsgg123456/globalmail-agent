<template>
  <div class="space-y-4">
    <p class="text-sm text-g-700">只检索已发布资料。先选精确型号和用途，再查看证据及原件位置。</p>
    <div class="flex flex-wrap gap-3">
      <ElSelect
        v-model="sku"
        filterable
        placeholder="选择精确型号"
        aria-label="试查型号"
        class="!w-[280px] max-w-full"
      >
        <ElOption v-for="p in products" :key="p.sku" :label="p.sku" :value="p.sku" />
      </ElSelect>
      <ElSelect v-model="mode" aria-label="试查用途" class="!w-[220px] max-w-full">
        <ElOption label="当前模拟" value="simulation" /><ElOption
          label="历史复盘"
          value="history_replay"
        />
      </ElSelect>
      <ElDatePicker
        v-model="asOf"
        type="datetime"
        placeholder="可用时间截点"
        aria-label="可用时间截点"
        class="!w-[220px] max-w-full"
      />
    </div>
    <ElSelect
      v-model="types"
      multiple
      clearable
      placeholder="全部资料类型"
      aria-label="试查资料类型"
      class="!w-[350px] max-w-full"
    >
      <ElOption v-for="(label, key) in typeLabels" :key="key" :label="label" :value="key" />
    </ElSelect>
    <ElInput
      v-model="query"
      type="textarea"
      :rows="3"
      maxlength="4000"
      show-word-limit
      placeholder="输入要查的问题或邮件内容"
      aria-label="检索问题"
    />
    <ElButton
      type="primary"
      :loading="busy"
      :disabled="!query.trim() || !sku || (mode === 'history_replay' && !asOf)"
      @click="search"
      >检索试查</ElButton
    >
    <ElAlert v-if="error" :title="error" type="error" :closable="false" />
    <template v-if="result">
      <p class="text-sm break-words"
        >本次条件：{{ input?.sku }} ·
        {{ input?.mode === 'history_replay' ? '历史复盘' : '当前模拟' }} · {{ input?.query }}</p
      >
      <ElAlert
        :title="reasons[result.reason]"
        :type="result.reason === 'ok' ? 'success' : 'warning'"
        :closable="false"
      />
      <p class="text-sm text-g-700"
        >发布记录 {{ result.head.epoch }} · {{ result.candidate_count }} 个候选 ·
        {{ result.evidence.length }} 份证据 · 上下文
        {{ result.usage?.context_proxy_tokens || 0 }} 代理tokens</p
      >
      <article
        v-for="item in result.evidence"
        :key="item.evidence_id"
        class="border-d rounded p-3 space-y-2 min-w-0"
      >
        <h3 class="font-medium break-words">{{ item.title }} · 第 {{ item.version_number }} 版</h3>
        <p class="text-sm text-g-700"
          >{{ item.page.length ? '原件第 ' + item.page.join('、') + ' 页 · ' : ''
          }}{{ item.section }} · 相关性 {{ item.score.toFixed(3) }}</p
        >
        <p class="text-sm break-words"
          >适用型号：{{ [...new Set(item.applicability.map((a) => a.sku))].join('、') }}</p
        >
        <pre class="whitespace-pre-wrap break-words text-sm font-inherit">{{ item.text }}</pre>
        <div class="flex flex-wrap gap-2"
          ><ElButton @click="check(item.evidence_id)">检查引用是否仍有效</ElButton>
          <ElButton type="primary" plain @click="emit('source', item.document_id, item.version_id)"
            >查看原件与核对结果</ElButton
          ></div
        >
        <p v-if="eligibility[item.evidence_id]" class="text-sm">{{
          eligibility[item.evidence_id]
        }}</p>
        <details class="text-xs text-g-700 break-all"
          ><summary>来源与发布凭证</summary> <p>原件 SHA：{{ item.source_sha256 }}</p
          ><p>内容 SHA：{{ item.content_hash }}</p>
          <p>引用：{{ item.evidence_id }} · 构建：{{ item.build_id }}</p>
          <p>可用时间：{{ new Date(item.available_at).toLocaleString('zh-CN') }}</p></details
        >
      </article>
    </template>
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue'
  import type { Catalog, DocumentType } from '@/api/knowledge-contract'
  import { useKnowledgeSearch } from '@/composables/useKnowledgeSearch'
  import { typeLabels } from './knowledge-labels'
  defineProps<{ products: Catalog['products'] }>()
  const emit = defineEmits<{ source: [string, string] }>()
  const query = ref(''),
    sku = ref(''),
    mode = ref<'simulation' | 'history_replay'>('simulation')
  const asOf = ref<Date | null>(null),
    types = ref<DocumentType[]>([])
  const { result, input, busy, error, eligibility, search: runSearch, check } = useKnowledgeSearch()
  const reasons = {
    ok: '已找到当前有效的证据。',
    empty: '这个型号和条件下没有合格证据。',
    scope_unavailable: '当前用途还没有合法的发布资料，无法试查。',
    incomplete_source: '有发布资料的原件或构建不完整，请先修复。',
    stale_release: '试查期间发布资料发生变化，请重新检索。',
    provider_error: '向量服务暂不可用或配置变化，本次未得到有效检索结果。'
  }
  async function search() {
    await runSearch({
      query: query.value,
      sku: sku.value,
      mode: mode.value,
      types: types.value,
      ...(asOf.value ? { as_of: asOf.value.toISOString() } : {})
    })
  }
</script>
