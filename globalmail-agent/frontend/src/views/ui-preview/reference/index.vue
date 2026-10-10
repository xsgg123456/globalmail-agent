<template>
  <div>
    <PreviewBanner note="保留原导航位置，仅展示本次预览的辅助信息" />
    <ElCard v-if="route.path === '/knowledge'">
      <template #header><h1 class="text-base font-medium">知识库</h1></template>
      <ElAlert
        title="本预览列出运行记录中引用的演示资料，知识维护功能仍以现有正式前端为准。"
        type="info"
        :closable="false"
        class="mb-4"
      />
      <ElTable :data="documents"
        ><ElTableColumn prop="title" label="资料名称" min-width="230" /><ElTableColumn
          prop="brand"
          label="品牌"
          min-width="140"
        /><ElTableColumn prop="sku" label="适用 SKU" min-width="150" /><ElTableColumn
          prop="version"
          label="版本"
          width="120"
        /><ElTableColumn label="来源"
          ><template #default
            ><ElTag size="small" type="warning">预览构造</ElTag></template
          ></ElTableColumn
        ></ElTable
      >
    </ElCard>
    <ElCard v-else>
      <template #header><h1 class="text-base font-medium">系统状态</h1></template>
      <ElDescriptions :column="1" border
        ><ElDescriptionsItem label="运行模式">交互预览 · ui-preview</ElDescriptionsItem
        ><ElDescriptionsItem label="数据">浏览器内存中的演示数据</ElDescriptionsItem
        ><ElDescriptionsItem label="业务 API">未连接</ElDescriptionsItem
        ><ElDescriptionsItem label="模型调用">未执行</ElDescriptionsItem
        ><ElDescriptionsItem label="正式服务"
          >现有前后端继续使用15173 / 18080端口</ElDescriptionsItem
        ></ElDescriptions
      >
    </ElCard>
  </div>
</template>
<script setup lang="ts">
  import { useRoute } from 'vue-router'
  import PreviewBanner from '../components/PreviewBanner.vue'
  const route = useRoute()
  const documents = [
    {
      title: '落地灯遥控配对排障 · 演示资料',
      brand: 'OUTON',
      sku: 'DEMO-FL-01',
      version: 'demo-v2'
    },
    {
      title: '退款记录查询与人工核对 · 演示资料',
      brand: 'BELEEV',
      sku: 'DEMO-SC-02',
      version: 'demo-v1'
    },
    {
      title: '危险迹象人工分流 · 演示资料',
      brand: 'OUTONLIFE',
      sku: 'DEMO-FL-01',
      version: 'demo-v1'
    }
  ]
</script>
