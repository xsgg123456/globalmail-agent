<template>
  <div class="space-y-4">
    <ElAlert
      v-if="!detail.source_available"
      title="原件缺失或损坏，请恢复完整原件或替换新文件后再核对。任务状态和操作仍可查看。"
      type="error"
      :closable="false"
    />
    <div class="flex flex-wrap gap-2 items-center">
      <ElSelect
        :model-value="detail.version.id"
        :disabled="busy"
        aria-label="资料版本"
        class="!w-[260px] max-w-full"
        @update:model-value="emit('version', $event)"
        ><ElOption
          v-for="version in document.versions"
          :key="version.id"
          :label="`版本 ${version.number} · ${labelState(version.status)}`"
          :value="version.id"
      /></ElSelect>
      <ElTag>{{ labelState(detail.version.status) }}</ElTag
      ><ElTag type="info">未发布</ElTag>
      <ElButton :disabled="busy" @click="emit('refresh')">刷新资料</ElButton>
      <ElButton :disabled="busy || !current" @click="emit('edit')">修订正文 / 适用范围</ElButton>
      <a :href="detail.source_url" target="_blank" rel="noopener" class="text-theme">下载原件</a>
    </div>
    <p class="text-sm text-g-700"
      >{{ document.document.source_reference }} ·
      {{ document.document.brand || '跨品牌资料（范围以绑定为准）' }} · 仅供模拟 · 资料可用时间
      {{ new Date(detail.version.available_at).toLocaleString('zh-CN') }}</p
    >
    <div class="flex flex-wrap gap-2 items-center">
      <ElSelect
        v-model="profile"
        aria-label="解析档位"
        :disabled="busy || !current"
        class="!w-[220px] max-w-full"
        ><ElOption
          v-for="item in profiles.filter((p) =>
            detail.version.format === 'pdf'
              ? p.id.startsWith('mineru_')
              : p.id === (detail.policy ? 'policy' : 'markdown')
          )"
          :key="item.id"
          :label="item.label + (item.available ? '' : '（未就绪）')"
          :value="item.id"
          :disabled="!item.available"
      /></ElSelect>
      <ElButton
        :disabled="busy || !current || !profiles.some((p) => p.id === profile && p.available)"
        :loading="busy"
        @click="parse"
        >{{ detail.version.parse_generation ? '重新解析，撤销旧核对' : '开始解析' }}</ElButton
      >
    </div>
    <div v-for="job in detail.jobs" :key="job.id" class="border-d rounded p-3">
      <div class="flex flex-wrap gap-2 items-center"
        ><ElTag>{{ labelState(job.status) }}</ElTag
        ><span>{{ labelStage(job.stage) }} · 第 {{ job.attempt_no }} 次</span>
        <ElButton
          v-if="['queued', 'running'].includes(job.status)"
          :disabled="busy || !current"
          @click="control(job.id, 'cancel', job.row_version)"
          >取消任务</ElButton
        >
        <ElButton
          v-if="['failed', 'cancelled'].includes(job.status) && job.retryable"
          :disabled="busy || !current"
          @click="control(job.id, 'retry', job.row_version)"
          >重试解析</ElButton
        > </div
      ><p v-if="job.error_code" class="mt-2 text-sm">{{ jobError(job.error_code) }}</p>
    </div>
    <ElTabs v-model="tab">
      <ElTabPane label="原件与解析对照" name="compare">
        <div class="grid grid-cols-1 xl:grid-cols-2 gap-4 items-start">
          <section class="border-d rounded p-3 min-w-0"
            ><h2 class="font-medium mb-3">原件</h2>
            <template v-if="detail.version.format === 'pdf'"
              ><p v-if="!pageAssets.length" class="text-sm text-g-700">{{
                detail.source_available
                  ? '解析后会显示原页预览，现在可以下载原件核对。'
                  : '原件当前不可用，恢复或替换后才能预览和下载。'
              }}</p
              ><figure v-for="asset in pageAssets" :key="asset.id" class="mb-4"
                ><figcaption class="text-sm mb-2">原件第 {{ asset.page }} 页</figcaption
                ><img
                  :src="asset.url"
                  :alt="`原件第 ${asset.page} 页`"
                  class="w-full h-auto border-d"
                  loading="lazy" /></figure
            ></template>
            <pre v-else class="whitespace-pre-wrap break-words text-sm font-inherit">{{
              originalText
            }}</pre>
          </section>
          <section class="min-w-0"
            ><h2 class="font-medium mb-3">解析结果与人工核对</h2
            ><KnowledgeReview
              :key="detail.version.id"
              :detail="detail"
              :current="current"
              :busy="busy"
              :execute="execute"
          /></section>
        </div>
      </ElTabPane>
      <ElTabPane label="适用型号" name="scope"
        ><ElEmpty
          v-if="!detail.applicabilities.length"
          description="还未明确适用范围，请修订资料添加"
        /><div
          v-for="(binding, i) in detail.applicabilities"
          :key="i"
          class="border-d rounded p-3 mb-3 break-words"
          ><p
            >{{ binding.sku }} ·
            {{ binding.section_id === 'document' ? '整份资料' : sectionLabel(binding.section_id)
            }}<span v-if="binding.page_start">
              · 第 {{ binding.page_start }}–{{ binding.page_end }} 页</span
            ></p
          ><p class="text-sm text-g-700 mt-2">判断依据：{{ binding.basis }}</p></div
        ></ElTabPane
      >
      <ElTabPane label="版本差异" name="diff"
        ><ElEmpty v-if="!detail.diff" description="这是第一版，没有上一版可比较" /><template v-else
          ><div class="flex gap-2 mb-3 flex-wrap"
            ><ElTag>{{ detail.diff.source_changed ? '原件内容已变' : '原件未变' }}</ElTag
            ><ElTag>{{
              detail.diff.applicability_changed ? '适用范围已变' : '适用范围未变'
            }}</ElTag></div
          ><pre v-if="detail.diff.text_diff" class="whitespace-pre-wrap break-words text-sm">{{
            detail.diff.text_diff
          }}</pre
          ><template v-if="detail.diff.applicability_changed"
            ><h3 class="font-medium mt-4">上一版范围</h3
            ><p v-for="(b, i) in detail.diff.before_applicabilities" :key="i" class="break-words"
              >{{ b.sku }} · {{ b.section_id === 'document' ? '整份资料' : b.section_id }} ·
              {{ b.page_start ? '第 ' + b.page_start + '–' + b.page_end + ' 页 · ' : ''
              }}{{ b.basis }}</p
            ><h3 class="font-medium mt-4">当前范围</h3
            ><p v-for="(b, i) in detail.diff.after_applicabilities" :key="i" class="break-words"
              >{{ b.sku }} · {{ b.section_id === 'document' ? '整份资料' : b.section_id }} ·
              {{ b.page_start ? '第 ' + b.page_start + '–' + b.page_end + ' 页 · ' : ''
              }}{{ b.basis }}</p
            ></template
          ></template
        ></ElTabPane
      >
      <ElTabPane label="操作记录" name="audit"
        ><div v-for="audit in document.audits" :key="audit.id" class="border-b-d py-3"
          ><p
            >{{ auditLabels[audit.action] || '资料操作' }} · 本机维护者 ·
            {{ new Date(audit.created_at).toLocaleString('zh-CN') }}</p
          ></div
        ></ElTabPane
      >
    </ElTabs>
  </div>
</template>
<script setup lang="ts">
  import { computed, ref, watch } from 'vue'
  import type {
    Catalog,
    DocumentDetail,
    KnowledgeResult,
    VersionDetail
  } from '@/api/knowledge-contract'
  import KnowledgeReview from './KnowledgeReview.vue'
  import { labelState, labelStage, jobError } from './knowledge-labels'
  const props = defineProps<{
    document: DocumentDetail
    detail: VersionDetail
    profiles: Catalog['parser_profiles']
    busy: boolean
    execute: (path: string, body: Record<string, unknown>) => Promise<KnowledgeResult>
  }>()
  const emit = defineEmits<{ version: [string]; refresh: []; edit: [] }>()
  const profile = ref(props.detail.version.parser_profile_id),
    tab = ref('compare')
  watch(
    () => props.detail.version.id,
    () => {
      profile.value = props.detail.version.parser_profile_id
    }
  )
  const current = computed(
    () => props.document.document.current_version_id === props.detail.version.id
  )
  const pageAssets = computed(() =>
    props.detail.assets
      .filter((asset) => asset.kind === 'page_preview')
      .sort((a, b) => (a.page || 0) - (b.page || 0))
  )
  const originalText = computed(() => {
    if (props.detail.policy) return props.detail.policy.description
    if (props.detail.version.format === 'md') return props.detail.source_text || ''
    // Structured knowledge preserves its controlled bytes; show readable fields for human comparison.
    try {
      const text = props.detail.source_text || ''
      const rows: unknown =
        props.detail.version.format === 'jsonl'
          ? text
              .split('\n')
              .filter((line) => line.trim())
              .map((line) => JSON.parse(line) as unknown)
          : (JSON.parse(text) as { blocks?: unknown }).blocks
      return Array.isArray(rows)
        ? rows
            .map((row: unknown) => {
              if (typeof row !== 'object' || row === null) return ''
              const block = row as Record<string, unknown>
              return [
                typeof block.text === 'string' ? block.text : '',
                Array.isArray(block.table_rows)
                  ? block.table_rows
                      .map((cells: unknown) => (Array.isArray(cells) ? cells.join(' | ') : ''))
                      .join('\n')
                  : ''
              ]
                .filter(Boolean)
                .join('\n')
            })
            .join('\n\n')
        : '无法读取原件结构，请下载原件核对。'
    } catch {
      return '无法读取原件结构，请下载原件核对。'
    }
  })
  const auditLabels: Record<string, string> = {
    'version.created': '创建新版本',
    'parse.queued': '提交解析',
    'parse.completed': '解析完成',
    'parse.failed': '解析失败',
    'version.reviewed': '保存人工核对',
    'job.cancel': '取消解析',
    'job.retry': '重试解析',
    'prepared.imported': '导入准备资料'
  }
  function sectionLabel(id: string) {
    const heading = props.detail.blocks.find(
      (block) => block.section_id === id && block.type === 'heading'
    )
    return heading?.text || '指定章节 ' + id
  }
  async function parse() {
    try {
      await props.execute(`/knowledge/versions/${props.detail.version.id}/parse`, {
        expected_version: props.detail.version.row_version,
        parser_profile_id: profile.value
      })
    } catch {
      /* 页面保留错误与原输入。 */
    }
  }
  async function control(id: string, action: string, revision: number) {
    try {
      await props.execute(`/jobs/${id}/${action}`, { expected_version: revision })
    } catch {
      /* 页面保留错误。 */
    }
  }
</script>
