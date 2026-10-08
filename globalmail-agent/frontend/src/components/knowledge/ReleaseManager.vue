<template>
  <div class="space-y-4" v-loading="loading || candidateLoading">
    <ElAlert
      v-if="error || actionError || candidateError"
      :title="error || actionError || candidateError"
      type="error"
      :closable="false"
    />
    <ElAlert v-if="notice" :title="notice" type="success" :closable="false" />
    <p
      >当前发布记录 {{ releases.head.epoch }} ·
      {{ currentRelease?.entries.length || 0 }} 份生效资料</p
    >
    <p class="text-sm text-g-700"
      >{{
        currentRelease?.profile?.label || '尚未发布模型空间'
      }}。回滚会重新检查全部资料的资格，并新增发布记录。</p
    >
    <ElButton :disabled="busy" @click="reload">刷新记录与候选构建</ElButton>
    <ElCollapse>
      <ElCollapseItem title="整批发布 / 切换向量模型" name="switch">
        <div class="space-y-3">
          <p class="text-sm text-g-700"
            >每份当前生效资料都必须有目标模型下的合格构建。切换会整体替换清单，不能混用不同模型的向量。</p
          >
          <ElSelect v-model="target" aria-label="整批发布模型" class="!w-[280px] max-w-full">
            <ElOption
              v-for="p in profiles.items"
              :key="p.key"
              :value="p.key"
              :label="p.label"
              :disabled="!p.available"
            />
          </ElSelect>
          <ElEmpty v-if="!candidates.length" description="还没有可维护资料" />
          <div
            v-for="item in candidates"
            :key="item.documentId"
            class="border-d rounded p-3 break-words"
          >
            <p
              >{{ item.title }} · 第 {{ item.version }} 版
              {{ requiredIds.has(item.documentId) ? '（当前生效，必须覆盖）' : '' }}</p
            >
            <ElSelect
              v-model="selected[item.documentId]"
              clearable
              value-on-clear=""
              placeholder="选择已完成构建"
              :aria-label="item.title + '候选构建'"
              class="!w-[350px] max-w-full mt-2"
            >
              <ElOption
                v-for="b in item.builds.filter((b) => b.profile_key === target)"
                :key="b.id"
                :value="b.id"
                :label="
                  '第 ' +
                  item.versions[b.version_id] +
                  ' 版 · ' +
                  b.profile_key +
                  ' · ' +
                  b.chunk_count +
                  '片段 · ' +
                  b.id.slice(0, 8)
                "
              />
            </ElSelect>
            <p
              v-if="requiredIds.has(item.documentId) && !selected[item.documentId]"
              class="text-sm text-g-700 mt-2"
              >请在这份资料的“索引与发布”中先构建目标模型。</p
            >
          </div>
          <p v-if="missing" class="text-sm"
            >还缺 {{ missing }} 份生效资料的目标构建，暂不能整体发布。</p
          >
          <ElButton type="primary" :loading="busy" :disabled="!canPublish" @click="publishAll"
            >确认整批发布</ElButton
          >
        </div>
      </ElCollapseItem>
    </ElCollapse>
    <ElEmpty v-if="!releases.items.length" description="还没有发布记录" />
    <article v-for="item in releases.items" :key="item.id" class="border-d rounded p-3 space-y-2">
      <div class="flex flex-wrap gap-2 items-center"
        ><ElTag>{{ operations[item.operation] || '资料发布' }}</ElTag>
        <span
          >记录 {{ item.epoch }} · {{ new Date(item.effective_at).toLocaleString('zh-CN') }} ·
          {{ item.entries.length }} 份资料</span
        >
        <ElTag v-if="item.id === releases.head.release_id" type="success">当前生效</ElTag></div
      >
      <p class="text-sm">{{ item.profile?.label || '空清单' }}</p>
      <details
        ><summary>完整发布清单</summary
        ><p v-for="e in item.entries" :key="e.document_id" class="text-sm break-words mt-2"
          >{{ e.title }} · 第 {{ e.version_number }} 版</p
        >
        <p class="text-xs text-g-700 break-all mt-2"
          >清单 SHA：{{ item.manifest_sha256 }}</p
        ></details
      >
      <ElButton v-if="item.id !== releases.head.release_id" :disabled="busy" @click="rollback(item)"
        >恢复这个发布清单</ElButton
      >
    </article>
  </div>
</template>
<script setup lang="ts">
  import { computed, watch, onUnmounted } from 'vue'
  import { ElMessageBox } from 'element-plus'
  import { useKnowledgeIndex } from '@/composables/useKnowledgeIndex'
  import { useReleaseManager } from '@/composables/useReleaseManager'
  import { releasePreferences } from '@/composables/knowledge-index-preferences'
  import type { KnowledgeRelease } from '@/api/knowledge-index-contract'
  const emit = defineEmits<{ changed: [] }>()
  const { releases, profiles, loading, busy, error, actionError, notice, refresh, execute } =
    useKnowledgeIndex()
  const {
    candidates,
    loading: candidateLoading,
    error: candidateError,
    load,
    cancel
  } = useReleaseManager()
  const target = computed({
    get: () => releasePreferences.target,
    set: (value: string) => {
      releasePreferences.target = value
    }
  })
  const selected = computed({
    get: () => releasePreferences.selected,
    set: (value: Record<string, string>) => {
      releasePreferences.selected = value
    }
  })
  const operations: Record<string, string> = { publish: '发布', rollback: '回滚', withdraw: '下架' }
  const currentRelease = computed(() =>
    releases.value.items.find((r) => r.id === releases.value.head.release_id)
  )
  const requiredIds = computed(
    () => new Set(currentRelease.value?.entries.map((e) => e.document_id) || [])
  )
  const chosen = computed(() =>
    candidates.value.flatMap((d) => {
      const b = d.builds.find(
        (b) => b.id === selected.value[d.documentId] && b.profile_key === target.value
      )
      return b ? [b] : []
    })
  )
  const missing = computed(
    () =>
      [...requiredIds.value].filter(
        (id) =>
          !chosen.value.some((b) =>
            candidates.value.find((d) => d.documentId === id)?.builds.includes(b)
          )
      ).length
  )
  const canPublish = computed(
    () =>
      !loading.value &&
      !candidateLoading.value &&
      !error.value &&
      !candidateError.value &&
      !missing.value &&
      chosen.value.length > 0 &&
      new Set(chosen.value.map((b) => b.profile_id)).size === 1
  )
  function defaults() {
    selected.value = Object.fromEntries(
      candidates.value.map((d) => [
        d.documentId,
        Object.hasOwn(selected.value, d.documentId) && !selected.value[d.documentId]
          ? ''
          : d.builds.find(
              (b) => b.id === selected.value[d.documentId] && b.profile_key === target.value
            )?.id ||
            d.builds.find((b) => b.profile_key === target.value)?.id ||
            ''
      ])
    )
  }
  watch(target, () => {
    selected.value = {}
    defaults()
  })
  async function reload() {
    await Promise.all([refresh(''), load()])
    defaults()
  }
  void reload()
  onUnmounted(cancel)
  async function publishAll() {
    try {
      await ElMessageBox.confirm(
        `将整体发布 ${chosen.value.length} 份资料，使用 ${target.value}。这会替换当前完整清单。`,
        '确认整批发布',
        { confirmButtonText: '整批发布', cancelButtonText: '返回核对' }
      )
    } catch {
      return
    }
    try {
      await execute('/knowledge/releases', {
        expected_release_epoch: releases.value.head.epoch,
        build_ids: chosen.value.map((b) => b.id),
        replace_all: true
      })
      emit('changed')
      await load()
      defaults()
    } catch {
      /* 保留错误和选择。 */
    }
  }
  async function rollback(item: KnowledgeRelease) {
    try {
      await ElMessageBox.confirm(
        `恢复记录 ${item.epoch} 的完整清单：${item.entries.length} 份资料，${item.profile?.label || '空清单'}。当前清单会被替换；已下架或来源不完整的资料将阻止恢复。`,
        '确认恢复发布',
        { confirmButtonText: '恢复清单', cancelButtonText: '取消' }
      )
    } catch {
      return
    }
    try {
      await execute(`/knowledge/releases/${item.id}/rollback`, {
        expected_release_epoch: releases.value.head.epoch
      })
      emit('changed')
    } catch {
      /* 已显示资格变化或失败原因。 */
    }
  }
</script>
