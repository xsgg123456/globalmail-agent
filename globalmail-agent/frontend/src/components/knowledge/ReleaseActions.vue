<template>
  <div class="space-y-4" v-loading="loading">
    <ElAlert
      v-if="error || actionError"
      :title="error || actionError"
      type="error"
      :closable="false"
    />
    <ElAlert v-if="notice" :title="notice" type="success" :closable="false" />
    <div class="border-d rounded p-3 space-y-2">
      <p v-if="status?.publication"
        >当前生效：第 {{ publishedVersion }} 版 · 发布记录 {{ status.publication.release_epoch }}</p
      >
      <p v-else-if="status">{{
        status?.withdrawn ? '资料已下架，重新构建并发布后才能恢复。' : '这份资料还未发布。'
      }}</p>
      <p v-else>暂未读到发布状态，请等待或刷新重试。</p>
      <p class="text-sm text-g-700"
        >核对完成后先构建，再显式发布。新构建失败时，原先生效的版本继续可用。</p
      >
      <ElButton :disabled="busy" @click="refresh(detail.version.id)">刷新构建与发布状态</ElButton>
    </div>
    <div class="flex flex-wrap gap-3">
      <ElSelect
        v-model="profile"
        aria-label="向量模型"
        class="!w-[250px] max-w-full"
        :disabled="busy"
      >
        <ElOption
          v-for="p in profiles.items"
          :key="p.key"
          :value="p.key"
          :label="p.label + (p.available ? '' : '（未配置）')"
          :disabled="!p.available"
        />
      </ElSelect>
      <ElSelect
        v-model="chunker"
        aria-label="切分方案"
        class="!w-[250px] max-w-full"
        :disabled="busy"
      >
        <ElOption v-for="p in profiles.chunkers" :key="p.key" :value="p.key" :label="p.label" />
      </ElSelect>
      <ElButton type="primary" :loading="busy" :disabled="!canBuild" @click="build"
        >构建索引</ElButton
      >
    </div>
    <p v-if="detail.version.status !== 'reviewed'" class="text-sm text-g-700"
      >请先在“原件与解析对照”中完成并保存人工核对。</p
    >
    <p v-if="!current" class="text-sm text-g-700"
      >这是历史内容版本。请选择当前版本构建；恢复旧发布可在发布记录中操作。</p
    >
    <ElEmpty v-if="status && !status.builds.length" description="还没有索引构建" />
    <article
      v-for="item in status?.builds || []"
      :key="item.id"
      class="border-d rounded p-3 space-y-2"
    >
      <div class="flex flex-wrap gap-2 items-center">
        <ElTag>{{ buildStates[item.status] || '状态待确认' }}</ElTag>
        <span
          >{{ item.profile_key }} · {{ item.embedded_count }}/{{ item.chunk_count }} 个片段 · 复用
          {{ item.cache_hits }} 个向量</span
        >
        <ElTag v-if="status?.publication?.build_id === item.id" type="success">当前生效</ElTag>
      </div>
      <p v-if="item.error_code" class="text-sm">{{ jobError(item.error_code) }}</p>
      <p v-if="item.status === 'ready' && !item.eligible" class="text-sm"
        >这个构建当前不符合发布条件，请核对原件、版本与下架记录后重新构建。</p
      >
      <ElButton
        v-if="item.eligible && status?.publication?.build_id !== item.id"
        :disabled="busy"
        type="primary"
        @click="publish(item)"
        >发布这个构建</ElButton
      >
      <p
        v-if="
          item.eligible &&
          releases.head.embedding_profile_id &&
          releases.head.embedding_profile_id !== item.profile_id
        "
        class="text-sm text-g-700"
        >与当前模型空间不同。请到“发布记录与模型切换”准备全部资料后整体切换。</p
      >
    </article>
    <div class="border-t-d pt-4 space-y-2">
      <p class="text-sm text-g-700"
        >下架会立即停用这份资料和旧引用，并取消未完成任务。原件与记录仍可维护。</p
      >
      <ElButton
        type="danger"
        plain
        :disabled="busy || !status || status.withdrawn"
        @click="withdraw"
        >下架这份资料</ElButton
      >
    </div>
  </div>
</template>
<script setup lang="ts">
  import { computed, watch } from 'vue'
  import { ElMessageBox } from 'element-plus'
  import type { DocumentDetail, VersionDetail } from '@/api/knowledge-contract'
  import type { IndexBuild } from '@/api/knowledge-index-contract'
  import { useKnowledgeIndex } from '@/composables/useKnowledgeIndex'
  import { buildPreferences } from '@/composables/knowledge-index-preferences'
  import { jobError } from './knowledge-labels'
  const props = defineProps<{ document: DocumentDetail; detail: VersionDetail; current: boolean }>()
  const emit = defineEmits<{ changed: [] }>()
  const {
    profiles,
    status,
    releases,
    loading,
    busy,
    error,
    actionError,
    notice,
    refresh,
    execute
  } = useKnowledgeIndex()
  const preferences = computed(() => buildPreferences(props.detail.version.id))
  const profile = computed({
    get: () => preferences.value.profile,
    set: (value: string) => {
      preferences.value.profile = value
    }
  })
  const chunker = computed({
    get: () => preferences.value.chunker,
    set: (value: string) => {
      preferences.value.chunker = value
    }
  })
  const buildStates: Record<string, string> = {
    queued: '等待构建',
    indexing: '正在构建',
    ready: '构建完成',
    failed: '构建失败',
    cancelled: '已取消'
  }
  const publishedVersion = computed(
    () =>
      props.document.versions.find((v) => v.id === status.value?.publication?.version_id)?.number ||
      '历史'
  )
  const canBuild = computed(
    () =>
      !loading.value &&
      !error.value &&
      status.value !== null &&
      props.current &&
      props.detail.source_available &&
      props.detail.version.status === 'reviewed' &&
      !status.value?.builds.some((b) => ['queued', 'indexing'].includes(b.status)) &&
      profiles.value.items.some((p) => p.key === profile.value && p.available)
  )
  watch(
    () => props.detail.version.id,
    (id) => refresh(id),
    { immediate: true }
  )
  async function save(path: string, body: Record<string, unknown>) {
    try {
      await execute(path, body)
      emit('changed')
    } catch {
      /* 已显示错误，保留输入。 */
    }
  }
  async function build() {
    await save(`/knowledge/versions/${props.detail.version.id}/build`, {
      expected_version: props.detail.version.row_version,
      embedding_profile_key: profile.value,
      chunking_profile_key: chunker.value
    })
  }
  async function publish(item: IndexBuild) {
    if (
      releases.value.head.embedding_profile_id &&
      releases.value.head.embedding_profile_id !== item.profile_id
    ) {
      actionError.value = '请到“发布记录与模型切换”完成全部资料的模型切换。'
      return
    }
    try {
      await ElMessageBox.confirm(
        `将“${props.detail.version.title}”第 ${props.detail.version.number} 版发布，替换这份资料的当前生效版本。其他资料继续生效。`,
        '确认发布',
        { confirmButtonText: '发布', cancelButtonText: '返回核对' }
      )
    } catch {
      return
    }
    await save('/knowledge/releases', {
      expected_release_epoch: releases.value.head.epoch,
      build_ids: [item.id],
      replace_all: false
    })
  }
  async function withdraw() {
    if (!status.value) return
    try {
      await ElMessageBox.confirm(
        `立即下架“${props.document.document.title}”？旧引用也会停用。`,
        '确认下架',
        { type: 'warning', confirmButtonText: '下架', cancelButtonText: '保留' }
      )
    } catch {
      return
    }
    await save(`/knowledge/documents/${props.document.document.id}/withdraw`, {
      expected_version: status.value.document_row_version,
      expected_release_epoch: releases.value.head.epoch
    })
  }
</script>
