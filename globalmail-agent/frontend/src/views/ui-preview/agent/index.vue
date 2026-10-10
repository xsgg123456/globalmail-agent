<template>
  <div>
    <PreviewBanner note="一个会话，多轮独立运行 · 多轮交互预览" />
    <div class="flex-cb flex-wrap gap-3 mb-4">
      <div
        ><h1 class="text-xl font-semibold">Agent 运行台</h1
        ><p class="text-sm text-g-700 mt-1">先选客户会话，再查看某一轮的判断与执行。</p></div
      >
      <div class="flex flex-wrap gap-2"
        ><RunHistory :selected-id="mail.id" @select="selectConversation" /><ElButton
          @click="backToMail"
          ><ArtSvgIcon icon="ri:mail-line" class="mr-2" />返回邮件</ElButton
        ></div
      >
    </div>
    <section class="page-content !p-5 mb-4" aria-label="当前会话与运行概览">
      <div class="flex-cb flex-wrap gap-4">
        <div class="flex items-start gap-3 min-w-0"
          ><div class="run-avatar"><ArtSvgIcon icon="ri:robot-2-line" /></div>
          <div class="min-w-0"
            ><div class="flex items-center flex-wrap gap-3"
              ><h2 class="text-lg font-semibold">{{ mail.customer }}</h2
              ><span class="text-xs text-g-700">会话状态</span><StatusTag :status="mail.status"
            /></div>
            <p class="text-sm text-g-700 mt-2 break-words"
              >{{ mail.subject }} <span class="text-xs ml-2">{{ mail.brand }}</span></p
            >
          </div>
        </div>
        <ElTag :type="mail.persistentHuman ? 'warning' : 'info'" effect="plain">{{
          mail.persistentHuman ? '客服持续主导' : '按本轮权限处理'
        }}</ElTag>
      </div>
      <ConversationRounds
        :runs="rounds"
        :selected-id="run.id"
        :customer-mails="customerMails"
        @select="selectRun"
      />
      <div class="run-meta mt-4"
        ><span class="font-medium text-g-900">所选第 {{ run.round }} 轮</span
        ><span>本轮结果：{{ run.status }}</span> <span>{{ run.duration }} 耗时</span
        ><span>{{ modelCount }} 次模型 / {{ toolCount }} 次工具</span
        ><span>{{ run.tokens.toLocaleString() }} Tokens · 演示</span>
        <span>{{
          run.mode === 'automatic'
            ? '本轮：正常回复'
            : run.mode === 'handoff'
              ? '本轮：转人工'
              : '本轮：内部辅助 · 未发信'
        }}</span>
        <ElButton v-if="linkedMessageId" link type="primary" size="small" @click="openLinkedMail"
          >{{ run.triggerMessageId ? '查看触发来信' : '查看跟进邮件' }} →</ElButton
        >
        <span class="font-mono text-g-600 ml-auto">{{ run.id }}</span>
      </div>
      <ElAlert v-if="isHistory" type="info" :closable="false" class="mt-4">
        <template #title
          ><div class="flex-cb flex-wrap gap-2"
            ><span
              >有更新的运行：第 {{ latest.round }} 轮。当前保留第
              {{ run.round }} 轮及所选节点。</span
            ><ElButton type="primary" link size="small" @click="selectRun(latest.id)"
              >查看最新一轮 →</ElButton
            ></div
          ></template
        >
      </ElAlert>
    </section>
    <div class="execution-layout"
      ><ExecutionFeed
        :key="run.id"
        :steps="run.steps"
        :selected-id="step.id"
        @select="selectStep" /><NodeDetail :key="`${run.id}:${step.id}`" :step="step"
    /></div>
  </div>
</template>
<script setup lang="ts">
  import { computed, watch } from 'vue'
  import { useRoute, useRouter } from 'vue-router'
  import { demo } from '@/preview/state'
  import '@/preview/control-client'
  import { conversationRuns, resolvePreviewRun } from '@/preview/navigation'
  import NodeDetail from '../components/NodeDetail.vue'
  import ExecutionFeed from '../components/ExecutionFeed.vue'
  import RunHistory from '../components/RunHistory.vue'
  import ConversationRounds from '../components/ConversationRounds.vue'
  import PreviewBanner from '../components/PreviewBanner.vue'
  import StatusTag from '../components/StatusTag.vue'
  const router = useRouter()
  const route = useRoute()
  const mail = computed(() => {
    const requested = demo.runs.find((item) => item.id === route.query.run_id)
    const id = route.query.conversation_id ?? requested?.conversationId ?? demo.selectedMail
    return demo.conversations.find((item) => item.id === id) ?? demo.conversations[0]!
  })
  const rounds = computed(() => conversationRuns(demo.runs, mail.value.id))
  const run = computed(() =>
    resolvePreviewRun(demo.runs, mail.value.id, route.query.run_id, demo.viewedRuns[mail.value.id])
  )
  const latest = computed(() => rounds.value.at(-1)!)
  const isHistory = computed(() => run.value.id !== latest.value.id)
  const step = computed(
    () => run.value.steps.find((item) => item.id === route.query.step_id) ?? run.value.steps[0]!
  )
  const linkedMessageId = computed(() => run.value.triggerMessageId ?? run.value.outputMessageId)
  const customerMails = computed(
    () => mail.value.messages.filter((item) => item.sender === 'customer').length
  )
  const modelCount = computed(() => run.value.steps.filter((item) => item.kind === 'model').length)
  const toolCount = computed(() => run.value.steps.filter((item) => item.kind === 'tool').length)
  watch(
    () => run.value.id,
    (id) => {
      demo.viewedRuns[mail.value.id] = id
    },
    { immediate: true }
  )
  function selectConversation(id: string) {
    const latestRun = conversationRuns(demo.runs, id).at(-1)!
    demo.selectedMail = id
    void router.replace({
      path: '/agent-runs',
      query: { conversation_id: id, run_id: latestRun.id }
    })
  }
  function selectRun(id: string) {
    void router.replace({
      path: '/agent-runs',
      query: { conversation_id: mail.value.id, run_id: id }
    })
  }
  function selectStep(id: string) {
    void router.replace({
      path: '/agent-runs',
      query: { conversation_id: mail.value.id, run_id: run.value.id, step_id: id }
    })
  }
  function backToMail() {
    void router.push({ path: '/workbench', query: { conversation_id: mail.value.id } })
  }
  function openLinkedMail() {
    void router.push({
      path: '/workbench',
      query: { conversation_id: mail.value.id, message_id: linkedMessageId.value }
    })
  }
</script>
<style scoped>
  .run-avatar {
    display: grid;
    place-items: center;
    width: 44px;
    height: 44px;
    flex-shrink: 0;
    border-radius: 10px;
    background: var(--el-color-primary-light-9);
    color: var(--el-color-primary);
    font-size: 24px;
  }
  .run-meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 10px 16px;
    color: var(--el-text-color-secondary);
    font-size: 12px;
  }
  .execution-layout {
    display: grid;
    grid-template-columns: minmax(330px, 0.9fr) minmax(400px, 1.15fr);
    gap: 16px;
    height: max(420px, calc(100vh - 525px));
  }
  @media (max-width: 1050px) {
    .execution-layout {
      grid-template-columns: 1fr;
      height: auto;
    }
    .execution-layout > section:last-child {
      min-height: 550px;
    }
  }
  @media (max-width: 600px) {
    .run-meta {
      gap: 10px 14px;
    }
    .execution-layout {
      gap: 12px;
    }
  }
</style>
