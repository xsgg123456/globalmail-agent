<template>
  <div>
    <RuntimeStatus />
    <ElCard>
      <template #header
        ><div class="flex flex-wrap justify-between gap-3"
          ><h1 class="text-base font-medium">知识库</h1
          ><div class="flex flex-wrap gap-2"
            ><ElButton :disabled="busy" @click="refreshList">刷新列表</ElButton
            ><ElButton @click="searchDrawer = true">检索试查</ElButton
            ><ElButton @click="releaseDrawer = true">发布记录与模型切换</ElButton
            ><ElButton :loading="busy" @click="importPrepared">导入准备资料</ElButton
            ><ElButton type="primary" :disabled="busy" @click="create">新建资料</ElButton></div
          ></div
        ></template
      >
      <ElAlert
        title="资料核对完成后，先构建索引，再显式发布。检索试查只使用当前合格的发布资料。正式 Agent 回复将在下一阶段接入。"
        type="info"
        :closable="false"
        class="mb-4"
      />
      <div class="flex flex-wrap gap-3 mb-4">
        <ElSelect
          v-model="filters.publication"
          clearable
          placeholder="全部发布状态"
          aria-label="筛选发布状态"
          class="!w-[180px]"
          @change="filter"
        >
          <ElOption label="有生效版本" value="published" />
          <ElOption label="未发布" value="unpublished" />
          <ElOption label="已下架" value="withdrawn" />
        </ElSelect>
        <ElSelect
          v-model="filters.type"
          clearable
          placeholder="全部类型"
          aria-label="筛选资料类型"
          class="!w-[180px]"
          @change="filter"
          ><ElOption v-for="(label, key) in typeLabels" :key="key" :label="label" :value="key"
        /></ElSelect>
        <ElSelect
          v-model="filters.brand"
          clearable
          placeholder="全部品牌"
          aria-label="筛选品牌"
          class="!w-[160px]"
          @change="filter"
          ><ElOption
            v-for="brand in ['OUTON', 'OUTONLIFE', 'BELEEV']"
            :key="brand"
            :label="brand"
            :value="brand"
        /></ElSelect>
        <ElSelect
          v-model="filters.sku"
          clearable
          filterable
          placeholder="全部型号"
          aria-label="筛选精确型号"
          class="!w-[240px] max-w-full"
          @change="filter"
          ><ElOption
            v-for="product in catalog.products"
            :key="product.sku"
            :label="product.sku"
            :value="product.sku"
        /></ElSelect>
        <ElSelect
          v-model="filters.status"
          clearable
          placeholder="全部状态"
          aria-label="筛选状态"
          class="!w-[180px]"
          @change="filter"
          ><ElOption
            v-for="status in [
              'draft',
              'parsing',
              'needs_review',
              'reviewed',
              'failed',
              'cancelled'
            ]"
            :key="status"
            :label="labelState(status)"
            :value="status"
        /></ElSelect>
      </div>
      <ElAlert
        v-if="error || actionError || catalogError"
        :title="error || actionError || catalogError"
        type="error"
        :closable="false"
        class="mb-3"
      />
      <ElAlert v-if="notice" :title="notice" type="success" :closable="false" class="mb-3" />
      <ElSkeleton v-if="loading && !items.length" :rows="5" animated />
      <ElEmpty
        v-else-if="!items.length"
        :description="error ? '读取失败，请刷新重试' : '暂无符合条件的资料，可以新建或导入准备资料'"
      />
      <ElTable v-else :data="items" v-loading="loading">
        <ElTableColumn label="资料" min-width="240"
          ><template #default="{ row }"
            ><ElButton
              link
              type="primary"
              class="!whitespace-normal text-left"
              @click="open(row)"
              >{{ row.title }}</ElButton
            ><p class="text-xs text-g-700"
              >{{ row.brand || '按具体范围绑定' }} · {{ typeLabels[row.document_type] }}</p
            ></template
          ></ElTableColumn
        >
        <ElTableColumn label="版本" width="90"
          ><template #default="{ row }"
            >第 {{ row.current_version_number }} 版</template
          ></ElTableColumn
        >
        <ElTableColumn label="状态" min-width="150"
          ><template #default="{ row }"
            ><ElTag>{{ labelState(row.status) }}</ElTag></template
          ></ElTableColumn
        >
        <ElTableColumn label="用途" min-width="170"
          ><template #default="{ row }"
            >仅供模拟 ·
            {{ row.withdrawn ? '已下架' : row.published ? '有生效版本' : '未发布' }}</template
          ></ElTableColumn
        >
        <ElTableColumn label="操作" width="100"
          ><template #default="{ row }"
            ><ElButton link type="primary" @click="open(row)">查看核对</ElButton></template
          ></ElTableColumn
        >
      </ElTable>
      <div class="flex flex-wrap justify-end gap-2 mt-4"
        ><ElButton :disabled="loading || cursors.length < 2" @click="paginate(false)"
          >上一页</ElButton
        ><ElButton :disabled="loading || !nextCursor" @click="paginate(true)">下一页</ElButton></div
      >
    </ElCard>
    <ElDrawer
      v-model="drawer"
      :title="document?.document.title || '知识资料'"
      size="min(1150px, 100vw)"
      @closed="closeDetail"
    >
      <ElSkeleton v-if="detailLoading" :rows="8" animated />
      <ElAlert
        v-if="actionError || detailError"
        :title="actionError || detailError"
        type="error"
        :closable="false"
        class="mb-3"
      />
      <KnowledgeDetails
        v-if="document && detail"
        :document="document"
        :detail="detail"
        :profiles="catalog.parser_profiles"
        :busy="busy"
        :execute="execute"
        @refresh="refreshSelected"
        @version="select(document.document.id, $event)"
        @edit="edit"
      />
      <ElEmpty v-else-if="!detailLoading" description="资料读取失败，请关闭后刷新重试" />
    </ElDrawer>
    <ElDrawer v-model="searchDrawer" title="检索试查" size="min(860px, 100vw)" destroy-on-close>
      <SearchPreview v-if="searchDrawer" :products="catalog.products" @source="openSource" />
    </ElDrawer>
    <ElDrawer
      v-model="releaseDrawer"
      title="发布记录与模型切换"
      size="min(900px, 100vw)"
      destroy-on-close
    >
      <ReleaseManager v-if="releaseDrawer" @changed="refreshSelected" />
    </ElDrawer>
    <KnowledgeEditor
      v-if="editor"
      :document="editing ? document?.document || null : null"
      :detail="editing ? detail : null"
      :catalog="catalog"
      :execute="execute"
      :upload="upload"
      @close="editor = false"
    />
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue'
  import RuntimeStatus from '@/components/business/runtime-status.vue'
  import KnowledgeDetails from '@/components/knowledge/KnowledgeDetails.vue'
  import KnowledgeEditor from '@/components/knowledge/KnowledgeEditor.vue'
  import SearchPreview from '@/components/knowledge/SearchPreview.vue'
  import ReleaseManager from '@/components/knowledge/ReleaseManager.vue'
  import { typeLabels, labelState } from '@/components/knowledge/knowledge-labels'
  import { useKnowledgeWorkbench } from '@/composables/useKnowledgeWorkbench'
  import type { KnowledgeDocument } from '@/api/knowledge-contract'
  defineOptions({ name: 'Knowledge' })
  const {
    items,
    catalog,
    document,
    detail,
    filters,
    nextCursor,
    cursors,
    loading,
    detailLoading,
    busy,
    error,
    actionError,
    detailError,
    catalogError,
    notice,
    refreshList,
    refreshDetail,
    select,
    closeDetail,
    execute,
    filter,
    paginate,
    upload
  } = useKnowledgeWorkbench()
  const drawer = ref(false),
    editor = ref(false),
    editing = ref(false)
  const searchDrawer = ref(false),
    releaseDrawer = ref(false)
  async function refreshSelected() {
    await Promise.all([refreshList(), refreshDetail()])
  }
  async function openSource(did: string, vid: string) {
    searchDrawer.value = false
    drawer.value = true
    await select(did, vid)
  }
  async function open(row: KnowledgeDocument) {
    drawer.value = true
    await select(row.id, row.current_version_id)
  }
  function create() {
    editor.value = true
    editing.value = false
  }
  function edit() {
    editor.value = true
    editing.value = true
  }
  async function importPrepared() {
    try {
      await execute('/knowledge/prepared-import', { expected_version: 0 })
    } catch {
      /* 保留错误供用户重试。 */
    }
  }
</script>
