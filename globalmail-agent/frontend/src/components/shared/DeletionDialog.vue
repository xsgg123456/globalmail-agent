<template>
  <ElDialog :model-value="true" title="彻底删除" width="min(540px, 94vw)" :close-on-click-modal="false" :before-close="close">
    <ElAlert v-if="error" :title="error" type="error" :closable="false" class="mb-3" />
    <DeletionStatus v-if="record" :record="record" :busy="busy" @refresh="refresh" @retry="retry" />
    <template v-else>
      <p class="font-medium break-words mb-3">{{ label }}</p>
      <ElSkeleton v-if="loading" :rows="3" animated />
      <template v-else-if="impact">
        <p class="text-sm mb-3">确认后停止相关运行，删除本项目持有的原件副本及受影响的模型记录、草稿和追踪。已发生业务保留无正文的防重记录。</p>
        <dl class="text-sm space-y-2 mb-3"><div v-for="item in counts" :key="item.name" class="flex justify-between gap-3"><dt>{{ item.name }}</dt><dd>{{ item.count }}</dd></div></dl>
        <div v-if="impact.impact.blocked_document_ids.length" class="text-sm mb-3">
          <p>以下资料与待删内容共享历史原件，确认后会暂停清理并禁止共享原件下载：</p>
          <p v-for="id in impact.impact.blocked_document_ids" :key="id" class="break-all">资料：{{ id }}</p>
        </div>
        <p class="text-xs text-g-700">外部源包、供应商留存、已外发内容和离线备份不在本次删除范围内。旧备份恢复时会重新执行删除记录。</p>
      </template>
      <ElButton v-else @click="load">重新读取影响</ElButton>
    </template>
    <template #footer><div class="flex flex-wrap justify-end gap-2">
      <ElButton :disabled="busy" @click="emit('close')">{{ record ? '关闭' : '取消' }}</ElButton>
      <ElButton v-if="!record" type="danger" :disabled="!impact || loading" :loading="busy" @click="confirm">确认彻底删除</ElButton>
    </div></template>
  </ElDialog>
</template>
<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { lifecycleApi, type DeletionKind, type DeletionImpact, type DeletionRecord } from '@/api/lifecycle-api'
import DeletionStatus from './DeletionStatus.vue'
const props = defineProps<{kind: DeletionKind; targetId: string; label: string}>()
const emit = defineEmits<{close: []; revoked: []; completed: []}>()
const impact = ref<DeletionImpact|null>(null), record = ref<DeletionRecord|null>(null)
const loading = ref(false), busy = ref(false), error = ref('')
let generation = 0, timer: ReturnType<typeof setTimeout>|undefined
const names: Record<string,string> = {objects:'文件及衍生副本',runs:'受影响运行',conversations:'受影响会话',documents:'资料',attachments:'图片'}
const counts = computed(() => Object.entries(impact.value?.impact ?? {}).filter(([key,value]) => key in names && typeof value === 'number').map(([key,value])=>({name:names[key],count:value})))
function close(done:()=>void) {if(!busy.value){emit('close');done()}}
function message(cause:unknown){return cause instanceof Error?cause.message:'读取失败，请重试。'}
function received(value:DeletionRecord){
  record.value=value
  if(value.status==='completed')emit('completed')
  if(['revoked','purging','verifying'].includes(value.status))timer=setTimeout(()=>void refresh(),1500)
}
async function load(){
  const current=++generation;clearTimeout(timer);impact.value=null;record.value=null;loading.value=true;error.value=''
  try{const value=await lifecycleApi.impact(props.kind,props.targetId);if(current===generation)impact.value=value}
  catch(cause){if(current===generation)error.value=message(cause)}finally{if(current===generation)loading.value=false}
}
async function confirm(){
  if(!impact.value||busy.value)return
  const current=generation;busy.value=true;error.value=''
  try{const value=await lifecycleApi.create(props.kind,props.targetId,impact.value.expected_version);if(current===generation){emit('revoked');received(value)}}
  catch(cause){if(current===generation)error.value=message(cause)}finally{if(current===generation)busy.value=false}
}
async function update(retrying:boolean){
  if(!record.value||busy.value)return
  const current=generation;clearTimeout(timer);busy.value=true;error.value=''
  try{const value=await(retrying?lifecycleApi.retry(record.value.id):lifecycleApi.get(record.value.id));if(current===generation)received(value)}
  catch(cause){if(current===generation)error.value=message(cause)}finally{if(current===generation)busy.value=false}
}
const refresh=()=>update(false), retry=()=>update(true)
watch(()=>[props.kind,props.targetId],load,{immediate:true})
onBeforeUnmount(()=>{generation++;clearTimeout(timer)})
</script>
