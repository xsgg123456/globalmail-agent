<template>
  <ElButton @click="open=true;load()">删除记录</ElButton>
  <ElDrawer v-model="open" title="删除记录" size="min(540px, 100vw)">
    <ElAlert v-if="error" :title="error" type="error" :closable="false" class="mb-3" />
    <ElButton :loading="busy" class="mb-4" @click="load">刷新记录</ElButton>
    <ElEmpty v-if="!busy && !items.length" description="暂无删除记录" />
    <section v-for="item in items" :key="item.id" class="border-d rounded p-3 mb-4">
      <p class="text-sm mb-2">{{ labels[item.target_type] }}</p>
      <DeletionStatus :record="item" :busy="busy" @refresh="load" @retry="retry(item.id)" />
    </section>
  </ElDrawer>
</template>
<script setup lang="ts">
import { ref } from 'vue'
import { lifecycleApi, type DeletionRecord } from '@/api/lifecycle-api'
import DeletionStatus from './DeletionStatus.vue'
const open=ref(false),busy=ref(false),error=ref(''),items=ref<DeletionRecord[]>([])
const labels={conversation:'客户会话',document:'知识资料',attachment:'客户图片'}
async function load(){busy.value=true;error.value='';try{items.value=(await lifecycleApi.list()).items}catch(cause){error.value=cause instanceof Error?cause.message:'读取失败'}finally{busy.value=false}}
async function retry(id:string){busy.value=true;error.value='';try{await lifecycleApi.retry(id);await load()}catch(cause){error.value=cause instanceof Error?cause.message:'清理失败'}finally{busy.value=false}}
</script>
