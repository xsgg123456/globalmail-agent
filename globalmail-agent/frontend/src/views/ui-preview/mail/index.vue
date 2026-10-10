<template>
  <div>
    <PreviewBanner note="邮件工作台只展示邮件往来和人工通信" />
    <div class="page-content flex !p-0 overflow-hidden mail-layout">
      <aside class="w-[260px] shrink-0 border-r-d flex flex-col min-h-0" aria-label="客户会话">
        <div class="p-4 border-b-d">
          <div class="flex-cb mb-3"
            ><h2 class="text-sm font-medium">客户会话</h2
            ><ElTag size="small" type="info">{{ demo.conversations.length }}</ElTag></div
          >
          <ElInput
            v-model="search"
            clearable
            placeholder="搜索客户、邮件主题"
            aria-label="搜索客户会话"
          />
          <ElSelect
            v-model="filter"
            placeholder="全部状态"
            class="w-full mt-3"
            aria-label="筛选会话状态"
          >
            <ElOption label="全部状态" value="" />
            <ElOption v-for="status in statuses" :key="status" :label="status" :value="status" />
          </ElSelect>
        </div>
        <div class="overflow-y-auto flex-1">
          <button
            v-for="item in filtered"
            :key="item.id"
            type="button"
            class="w-full p-4 border-b-d text-left hover:bg-active-color transition-colors"
            :class="item.id === current.id ? 'bg-theme/10' : ''"
            @click="select(item.id)"
          >
            <div class="flex-cb gap-2"
              ><span class="font-medium text-sm">{{ item.customer }}</span
              ><span class="text-xs text-g-600">{{
                mailTime(item.messages.at(-1)?.sent_at)
              }}</span></div
            >
            <p class="text-xs text-g-700 mt-2 truncate">{{ item.subject }}</p>
            <div class="flex-cb gap-2 mt-3"
              ><StatusTag :status="item.status" /><span class="text-xs text-g-600">{{
                item.brand
              }}</span></div
            >
          </button>
          <ElEmpty v-if="!filtered.length" description="没有符合筛选的会话" :image-size="60" />
        </div>
      </aside>
      <section class="flex-1 min-w-0 flex flex-col min-h-0" aria-label="邮件往来">
        <div class="p-4 flex-cb flex-wrap gap-3">
          <div class="min-w-0"
            ><h2 class="text-base font-medium break-words">{{ current.subject }}</h2>
            <p class="text-xs text-g-700 mt-2"
              >{{ current.email }} · {{ current.brand }} · {{ current.channel }}</p
            ></div
          >
          <div class="flex flex-wrap gap-2">
            <ElButton
              :disabled="['人工接管中', '已解决'].includes(current.status)"
              @click="takeover"
              >人工接管</ElButton
            >
            <ElButton :disabled="current.status === '已解决'" @click="resolve">标记已解决</ElButton>
          </div>
        </div>
        <div class="mx-4 mb-3 p-3 rounded-md bg-active-color flex-cb flex-wrap gap-3">
          <div class="flex items-center flex-wrap gap-2 text-sm">
            <ArtSvgIcon icon="ri:robot-2-line" class="text-lg text-theme" />
            <span>Agent</span><StatusTag :status="current.status" /><span
              class="text-xs text-g-700"
              >{{ statusNote }}</span
            >
          </div>
          <div class="flex flex-wrap gap-2">
            <ElButton v-if="current.advice" size="small" @click="adviceOpen = true"
              >查看客服建议</ElButton
            >
            <ElButton size="small" @click="openHistory"
              >全部 {{ currentRuns.length }} 轮 →</ElButton
            >
            <ElButton type="primary" plain size="small" @click="openRun">查看最新运行 →</ElButton>
          </div>
        </div>
        <p v-if="focusedMessage" class="mx-4 mb-3 text-xs text-theme" role="status"
          >已定位第 {{ focusedMessage.seq }} 封邮件 ·
          {{ focusedMessage.sender === 'customer' ? '客户来信' : '跟进回复' }}</p
        >
        <MessageTimeline
          ref="timeline"
          :messages="current.messages"
          :conversation-id="current.id"
          :scroll-signal="scrollSignal"
        />
        <div class="p-4 border-t-d">
          <div class="flex-cb flex-wrap gap-2 mb-3"
            ><span class="text-sm font-medium">人工回复</span
            ><span class="text-xs text-g-700">草稿跨页保留 · 仅在本预览中发送</span></div
          >
          <ElInput
            v-model="draft"
            type="textarea"
            :rows="3"
            resize="none"
            :maxlength="20000"
            placeholder="输入给客户的回复…"
            aria-label="人工回复正文"
          />
          <p v-if="replyError" class="text-xs text-danger mt-2" role="alert">{{ replyError }}</p>
          <div class="flex-cb flex-wrap gap-3 mt-3"
            ><span class="text-xs text-g-700">{{
              draft.length ? '草稿已保留' : '回复后等待客户下一封来信'
            }}</span>
            <ElButton type="primary" :disabled="current.status === '已解决'" @click="sendReply"
              >发送演示回复</ElButton
            ></div
          >
        </div>
      </section>
    </div>
    <AdviceDrawer
      v-model="adviceOpen"
      :advice="current.advice"
      :can-adopt="adviceIsCurrent(demo, current.id)"
      @adopt="adoptDraft"
    />
  </div>
</template>
<script setup lang="ts">
  import { computed, nextTick, onMounted, ref, watch } from 'vue'
  import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
  import { ElMessage, ElMessageBox } from 'element-plus'
  import MessageTimeline from '@/components/mail-agent/MessageTimeline.vue'
  import { formatMailTime } from '@/components/mail-agent/mail-labels'
  import PreviewBanner from '../components/PreviewBanner.vue'
  import StatusTag from '../components/StatusTag.vue'
  import AdviceDrawer from '../components/AdviceDrawer.vue'
  import { adviceIsCurrent, sendHumanReply, takeoverConversation } from '@/preview/behavior'
  import '@/preview/control-client'
  import { demo } from '@/preview/state'
  import { conversationRuns } from '@/preview/navigation'
  const route = useRoute()
  const router = useRouter()
  const search = ref('')
  const filter = ref('')
  const replyError = ref('')
  const adviceOpen = ref(false)
  const scrollSignal = ref(0)
  const timeline = ref<InstanceType<typeof MessageTimeline>>()
  const statuses = ['等待客户', '待人工接管', '人工接管中', '已解决']
  function mailTime(value?: string) {
    return value ? formatMailTime(value).split(' ').at(-1)?.slice(0, 5) : ''
  }
  const current = computed(
    () => demo.conversations.find((item) => item.id === demo.selectedMail) ?? demo.conversations[0]!
  )
  const currentRuns = computed(() => conversationRuns(demo.runs, current.value.id))
  const focusedMessage = computed(() =>
    current.value.messages.find((message) => message.id === route.query.message_id)
  )
  const draft = computed({
    get: () => demo.drafts[current.value.id] ?? '',
    set: (value: string) => {
      demo.drafts[current.value.id] = value
      replyError.value = ''
    }
  })
  const filtered = computed(() =>
    demo.conversations.filter(
      (item) =>
        (!filter.value || item.status === filter.value) &&
        `${item.customer} ${item.subject} ${item.email}`
          .toLowerCase()
          .includes(search.value.toLowerCase())
    )
  )
  const statusNote = computed(() =>
    current.value.persistentHuman && current.value.status !== '已解决'
      ? '客服持续主导 · Agent只提供内部建议和草稿'
      : current.value.status.includes('人工')
        ? '需要客服审核处理'
        : current.value.status === '已解决'
          ? '会话已由人工结案'
          : current.value.owner === 'human'
            ? '人工回复后，等待客户下一封来信'
            : '本轮处理结束，等待客户反馈'
  )
  function savePosition() {
    const node = timeline.value?.$el as HTMLElement | undefined
    if (node) demo.readPositions[current.value.id] = node.scrollTop
  }
  async function restorePosition() {
    await nextTick()
    // 原时间线在子组件更新后滚到底，等它完成再恢复当前客户的阅读位置。
    await nextTick()
    const node = timeline.value?.$el as HTMLElement | undefined
    if (!node) return
    const index = current.value.messages.findIndex(
      (message) => message.id === focusedMessage.value?.id
    )
    const article = index >= 0 ? node.querySelectorAll('article')[index] : undefined
    node.scrollTop = article
      ? node.scrollTop + article.getBoundingClientRect().top - node.getBoundingClientRect().top - 16
      : (demo.readPositions[current.value.id] ?? node.scrollHeight)
  }
  function select(id: string) {
    savePosition()
    void router.replace({ path: '/workbench', query: { conversation_id: id } })
  }
  watch(
    () => [route.query.conversation_id, route.query.message_id],
    ([id]) => {
      if (demo.conversations.some((item) => item.id === id)) demo.selectedMail = String(id)
      replyError.value = ''
      void restorePosition()
    },
    { immediate: true }
  )
  onMounted(restorePosition)
  onBeforeRouteLeave(savePosition)
  function openRun() {
    void router.push({ path: '/agent-runs', query: { run_id: current.value.runId } })
  }
  function openHistory() {
    void router.push({ path: '/agent-runs', query: { conversation_id: current.value.id } })
  }
  function takeover() {
    if (!takeoverConversation(demo, current.value.id)) return
    ElMessage.success('已在预览中接管此会话')
  }
  function resolve() {
    current.value.owner = 'human'
    current.value.status = '已解决'
    ElMessage.success('已在预览中标记解决')
  }
  function sendReply() {
    if (!draft.value.trim()) {
      replyError.value = '请填写回复正文'
      return
    }
    if (!sendHumanReply(demo, current.value.id, draft.value)) return
    scrollSignal.value++
    ElMessage.success('演示回复已加入邮件往来')
  }
  async function adoptDraft(body: string) {
    const conversationId = current.value.id
    const runId = current.value.advice?.runId
    if (!adviceIsCurrent(demo, conversationId)) return
    if (draft.value.trim() && draft.value !== body) {
      try {
        await ElMessageBox.confirm('替换你正在编辑的回复草稿？', '采用Agent建议', {
          confirmButtonText: '替换草稿',
          cancelButtonText: '保留我的草稿'
        })
      } catch {
        return
      }
    }
    if (
      current.value.id !== conversationId ||
      current.value.advice?.runId !== runId ||
      !adviceIsCurrent(demo, conversationId)
    )
      return
    draft.value = body
    adviceOpen.value = false
    ElMessage.success('草稿已放入人工回复框，请核对后发送')
  }
</script>
<style scoped>
  .mail-layout {
    height: min(850px, max(650px, calc(100vh - 220px)));
  }
  @media (max-width: 850px) {
    .mail-layout {
      flex-direction: column;
      height: auto;
    }
    .mail-layout > aside {
      width: 100%;
      max-height: 290px;
      border-right: none;
    }
    .mail-layout > section {
      min-height: 650px;
    }
  }
</style>
