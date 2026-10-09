# Phase 8 第二轮工程审查

日期：2026-10-09。独立 fresh code-reviewer，基线 `09a818fa9976c94e5c50a090620993b324b603ea`。审查范围为本期工作区增量，不含用户 `.idea/` 与进化队列。执行 [.agents/skills/code-review/SKILL.md](../../.agents/skills/code-review/SKILL.md)。

**结论：Stage 1 FAIL，1 项 HIGH、1 项 MEDIUM；Stage 2 未执行。文件名 FINAL 不表示通过。** 主 Agent 收到发现后已经开始修改源码；本报告固定保留本轮修前发现，不为之后的修改背书。修复后需要另派 fresh reviewer 从 Stage 1 重新审查。

## 输入、计划与验收边界

已直接读取 AGENTS、Product-Spec REQ-014/AC-065–082、主架构 4.4/4.3/6.3/9 的来源、预算、锁序、提交和隐私契约、DEV-PLAN Phase 8、PHASE-8-IMPLEMENTATION、SESSION-HANDOFF、文档索引、初审报告及本期 git diff/新增附件模块。

审查步骤：逐条需求映射 → 接收/案例包/绑定/授权 → 联合理解/预算/风险接管 → 人工更正/撤销/晚到 → 工作台交互与本期编译。完成标准是每条本期工程行为具有代码与实际验证依据；有 HIGH 则停止在 Stage 1。

用户原文“倒不如继续开发 到时候整个项目跑通之后再调整这种细节”“现在继续开发Phase8吧”已由 DEV-PLAN.md:7/178 和 AGENT-ARCHITECTURE.md:5 同步。真实模型语义、Phase 1/7 质量 FAIL、AC-082 专项回归仍未通过；本轮 0 付费模型调用，固定响应只验证工程门。AC-069/071 的正式售后写属于 Phase 9，AC-078 的完整副本清理/备份恢复属于 Phase 12；这些延期不放宽本期即时撤销、来源、预算、停止和人工恢复门。

## HIGH：人工字段更正未清除当前有效 Understanding 中的矛盾自动字段事实

- 对照要求：Product-Spec.md:527/546（AC-080）要求后续合法运行使用人工新修订，旧分析/缓存不能覆盖；AGENT-ARCHITECTURE.md:235 要求候选核验不能无来源覆盖人工版本。PHASE-8-IMPLEMENTATION.md:20 明确“顶层候选/事实和查单门同步使用人工来源”。
- 修前位置：`globalmail-agent/backend/src/globalmail_agent/attachments/understanding.py:85–95` 只移除 observation/hypothesis 对应事实；order_number 仅移除 order_candidates/intent.order_number。sku、model、error_code 以及 order_number 的 top-level `facts` 没有人工同列保护。`agent/graph.py:94–117` 将该结果及原始 `images.field_candidates` 交给下一次决策，原始自动 `visual_sources` 也继续有效。
- 已修的一部分：`attachments/evidence.py:68–77` 会跳过同 epoch、同字段的自动 evidence 行。这保护了证据列表，却没有同步保护模型正在使用的 Understanding/facts/来源投影。
- 实际复现：真实隔离 PG、正式接收/更正/人工回复/Graph/上下文服务，依次对 sku、model、error_code、order_number 执行“图片分析 → HITL → 人工更正具体字段 → 人工回复 → 新客户来信 → 合法固定视觉输出”。四种字段均正常完成新 Graph；捕获 decision 请求中的有效事实：

```text
field_key=sku         old_fact_effective=true
field_key=model       old_fact_effective=true
field_key=error_code  old_fact_effective=true
field_key=order_number old_fact_effective=true

facts=[
  {key:sku, kind:model_inference, value:AUTO_OLD_sku, source:image:<attachment>},
  {key:manual_sku, kind:human_decision, value:HUMAN_NEW_sku, source:visual:<revision>}
]
images[0].field_candidates=[{key:sku, value:AUTO_OLD_sku}]
CLEANUP {"callbacks_passed": true, "schema_removed": true, "temporary_objects_removed": true}
```

完整原始输出：`tmp/phase8-review-final-manual-fields-repro.txt`。输入符合正式 Pydantic schema，引用指向该图真实自动提取字符串；没有伪造不可达测试前提。它证明人工来源与矛盾自动来源同时取得当前有效资格，不涉及视觉识别准确率是否延期。

- 修复标准：原始模型分析可单独保存审计；传给当前决策、事实存储、来源核验和后续修订工具的有效投影必须服从人工同列版本。不能仅在 Prompt 提醒，或只让抽屉列表隐藏旧值。保留危险记录的独立人工处理门，普通自由更正不能清除有效安全风险。
- 现有回归的局限：`tests/test_vision_corrections.py:16–47` 验证 observation 更正及 evidence 列表，没有构造包含矛盾具体字段 top-level fact 的后续响应；`tests/test_vision_provider.py:26–40` 只验证 order 查询候选优先。因此全部现有测试通过不能关闭本发现。

## MEDIUM：缺字节或预览失败时，抽屉撤销确认后静默不执行

- 对照要求：Product-Spec.md:528/547（AC-081）要求已提交证据可撤销、真实错误与操作路径；主架构:236 规定即时撤销。
- 位置：`globalmail-agent/frontend/src/components/mail-agent/ImageEvidenceDrawer.vue:67–77` 用 `Promise.all` 同时加载原图与证据。缺字节、不支持、存储损坏时，预览失败会抛弃成功的证据响应，`page` 保持 null。`:85` 的 mutate 遇 `!page.value` 直接返回；`:40/108–112` 撤销按钮和危险确认仍可点击，确认后没有请求、成功或失败反馈。
- 真实 HTTP 前提已验证：随正文保存合法 missing PNG 元数据，使用正式附件端点：

```text
MISSING_DRAWER_HTTP {"preview_status": 503, "preview_reason": "attachment_bytes_unavailable", "evidence_status": 200, "evidence_revision": 0, "revoke_status": 200}
CLEANUP {"callbacks_passed": true, "schema_removed": true, "temporary_objects_removed": true}
```

原始输出：`tmp/phase8-review-final-missing-drawer-repro.txt`。服务端可撤销，该问题位于上述前端 Promise/早退路径；本轮没有将源码推导冒充真实浏览器点击结果。

- 修复标准：证据版本读取与原图预览独立处理，预览失败不阻断已有合法 epoch 的撤销；不可执行的按钮明确受限并反馈原因，不能确认后静默退出。

## Stage 1 逐项实现与验证

下表的“工程已验证”限于明确列出的确定性行为，不等于该整条产品 AC 或真实模型语义已验收。后端路径统一前缀为 `globalmail-agent/backend/src/globalmail_agent/`。

| Spec / AC | 结果 | 当前代码与验证依据 |
|---|---|---|
| 接收格式/字节/限额；AC-065 | 工程已验证；模型提取及不重复补问语义延期 | `attachments/validation.py:8–52` 实际 decode/格式/20Mpix/10MiB；`intake.py:22–54` 独立暂存；`binding.py:49–85` 仅 ready 原子绑定。`test_attachment_validation`/`test_attachment_intake`/`test_attachment_binding` 实际字节与 PG/HTTP。 |
| 字段/歧义/客户限制；AC-066 | 工程来源门已实现；语义延期 | `attachments/understanding.py:8–12/57–75` 保留 raw/value/歧义并拒绝歧义查单候选；`agent/tool_gateway.py:96–104` 要有来源且走当前会话业务查询。人工字段优先未完整实现，见 HIGH。 |
| 观察/推测/原图定位；AC-067 | 工程已验证；识别语义延期 | `attachments/understanding.py:15–24` 分栏；`evidence.py:65–84` 有图/摘要/view/epoch/来源；`views.py:50–57` 标整图和尺寸，未伪造框。`test_vision_graph.py:16–39` 实际图像/逐图证据。 |
| 图片正常/局部不否定功能或缺件；AC-068 | Prompt 接入，语义未验证 | `agent/prompts/visual-understanding.md:11–12`，`agent/graph.py:82–85`；没有以工程固定响应宣布模型遵守。 |
| 观察结合订单/SOP/政策分流；AC-069 | 本期来源/工具权限门保留；正式申请 Phase 9 | `agent/tool_gateway.py:96–154`、`application/draft_validation.py:35–45` 强制账本工具与适用资料来源；`agent/context.py:84–85` 明确当前无售后写。真实业务分流延期。 |
| 风险程序直接人审；AC-070 | 工程已验证；危险识别及安全话术语义延期 | `agent/graph.py:94–123` 无额外 decision 请求；`application/risk_handoff.py:5–9`；`commit_outcome.py:52–79` 同事务理解、风险、人审和撤销处理权。`test_vision_graph.py:41–55` 验证 1 请求、0 出站、active risk。 |
| 图片不作为退款/发货回执；AC-071 | 来源/权限工程门保留；Phase 9 及语义延期 | `agent/understanding.py:69–75` 图片不可伪装 human/customer/tool facts；`draft_validation.py:40–45` 账本 claim 必须有业务工具；`agent/tool_schemas.py` 现有白名单无售后效果工具。 |
| 缺失/不支持/坏图/失败及原因；AC-072 | 后端工程已验证；抽屉操作部分实现 MEDIUM | `attachments/importing.py:26–57` missing/unsupported；`validation.py:29–52` 坏图/动图明确拒绝；`lifecycle.py:5–8` 中断码；`worker/agent_runner.py:138–152` 逐图失败码；`queries.py:15–19` 返回原因。`test_vision_import.py:17–42` 与 `test_vision_corrections.py:71–82` 实际 HTTP/PG。 |
| 上传/CID/仅图/远程拒绝/幂等；AC-073 | 工程已验证 | `domain/conversation.py:25–50` 受控 ID、元数据不允许仅图；`attachments/binding.py:12–34/49–85` 固定有序 CID 清单和限额；`intake.py:31–54` upload 幂等；`application/conversations.py:25–31/40–58` 原子接收和重复消息清单检查。端点不收远程路径/URL，`MessageTimeline.vue:29–30` 文本展示正文。 |
| 受控案例包/历史合法图；AC-073/074 | 接入缺口工程已修；历史字节完整 Graph 仍应补专项 | `application/fixture_conversations.py:37–44` 正式调用 `save_metadata`；`attachments/importing.py:42–78` content_id manifest 白名单、包内 resolve、限额/hash/decode 同事务对象登记。`test_vision_import.py:44–62` 实际受控 PNG 接入及越界路径拒绝。 |
| 跨客户/分支/用途/前缀拒绝；AC-074 | 已有授权工程路径验证 | `attachments/queries.py:22–40/44–67/71–108` 全 scope/可见 seq/原图完整性和删除journal；`evidence.py:17–39` 当前可见且未撤销的人工版本；`test_attachment_lifecycle.py:91–102` 逐 scope 拒绝，`test_attachment_binding` 实际可见前缀；`test_vision_import.py:64–73` 未来元数据不进本轮 Context。无跨 run 联合理解缓存。 |
| 不可信图片不扩大权限；AC-075 | 工程权限边界保留；注入语义专项延期 | `agent/prompts/visual-understanding.md:14–15`，`agent/graph.py:163–167` 拒绝未声明工具；`api/security.py` 原 Host/Origin/写入类型门；`attachments/importing.py:60–78` 文件只从受控包白名单，不访问二维码/外链。 |
| 6 视图/请求、12 工具、16k/80k/120秒、unknown；AC-076 | 工程已验证 | `attachments/views.py:17–31/34–60` EXIF/1024 全图/保守 patch 上界；`agent/budget.py:46–65/72–96/98–110` 共享 cycle 预留/结算/unknown。`agent/graph.py:45–68` 每次网络重试重新授权并计量，`test_vision_graph.py:57–70` 四图重试超 6 显停、unknown 不归零。 |
| Graph/checkpoint/观测无图片字节 | 工程已验证；正式 Langfuse 导出 Phase 11 | `adapters/model_provider.py:25–35` SDK 内临时 data URL 与 deepcopy；`attachments/views.py:50–57` Graph 仅 refs；`test_vision_provider.py:12–24` 捕获实际 SDK 参数且原 messages 不变，`test_vision_graph.py:31–35` 实际检查点没有 image_url/base64。本期本地 trace 保留无正文关联，未将原图入共享 RAG。 |
| 停止/接管/新输入/更正晚到门；AC-077 | 已有停止/接管/新输入/撤销竞争已验证；更正有效投影 HIGH | `agent/guard.py:43–72` slot→branch→conversation→排序 attachment→head→run/task/cycle；`attachments/corrections.py:39–76` 人工权限/row/input/epoch/无自动恢复；`application/task_queue.py`/`worker/jobs.py`/`worker/leases.py` 中断图状态。`test_vision_graph.py:72–99` 固定模型回调中真实变更处理权，0 有效分析/出站。 |
| 撤销/依赖读取/物理删除；AC-078 | 本期后端即时撤销修复有证据；UI MEDIUM；完整清理 Phase 12 | `attachments/corrections.py:70–76` 撤销+输入栅栏；`revocation.py:10–21` 递归依赖拒读；`adapters/body_store.py:50–72` 统一读门；`run_records.py:40–50`/`checkpoint_repository.py:110–117` Context 撤销门；`agent/memory.py:14–30` 混合事实依赖所有可见原图，`human_review.py:16–21` 人工派生内容登记依赖。`test_vision_graph.py:101–120` 与 `test_vision_corrections.py:49–69` 实际 PG/HTTP 410 和红字占位。 |
| 多图状态/关联/未覆盖；AC-079 | 工程已验证；不同商品视觉对应语义延期 | `binding.py:12–34/73–85` 每封四图/总量、重复 CID/ID 拒绝；`views.py:34–60` 最新六图选取；`agent/graph.py:79–81` 明确未覆盖清单；`attachments/understanding.py:42–49` 每传入图恰一分析，unreadable 不得有字段/观察/风险。missing 真实显示。 |
| 人工更正来源/修订/下一封屏障；AC-080 | **部分实现，HIGH** | `corrections.py:39–88` 人工权限、版本冲突、supersedes/epoch、不同列人工修订保留；`evidence.py:68–77` 有效 evidence 行保护；`understanding.py:85–95` 有效 facts/字段投影仍矛盾，四字段实际复现见上。更正和人工回复后不会自动 claim 新 run 已由回归验证。 |
| 新建/追加/原图/失败/更正/撤销 UI；AC-081 | 主入口源码完整，撤销部分实现 MEDIUM；实际邻居视觉未执行 | 前端 `ConversationDialog.vue:42–43/175–188`、`MessageComposer.vue:55–63/95–102` 支持仅图/保留草稿；`ImageUpload.vue:37–88` 防串目标、未知结果同 bytes/scope 重试 key；`pending-image-uploads.ts:4–12`；`MessageTimeline.vue:31–35` 逐图状态；`ImageEvidenceDrawer.vue:25–42/79–113` 具体字段/理由/危险确认，读图失败死操作见上；API metadata 不含对象路径、preview no-store/nosniff。 |
| 冻结真实专项；AC-082 | 经用户授权延期，未执行/未通过 | `DEV-PLAN.md:178/191`、`PHASE-8-IMPLEMENTATION.md:12/16`；本轮全部固定响应及 SDK capture 均 0 网络模型调用，不作为视觉语义结果。 |
| 24h暂存/草稿取消/清理引用 | 工程已验证 | `attachments/intake.py:67–144` 仅未绑定取消/过期、再次锁定、遍历 FK/依赖后清理；worker `agent_runner.py:165–172` 定期扫暂存。`test_attachment_lifecycle.py:16–89` 实际验证绑定/额外引用保留、过期拒读、磁盘失败回滚及删除journal。 |

未发现本期新增独立视觉 Agent、额外 OCR 服务、共享图片 RAG、真实邮箱或外部交易权限。三个附件表、上传/预览/更正/撤销端点和工作台组件属于 REQ-014/Phase 8；源码中的 Phase 9/12 限制文案未假称已经交付。旧 `0001`–`0006` 迁移的 `git diff --name-only HEAD` 输出为空；新 DDL 位于 `migrations/versions/0007_visual_evidence.py`，本轮只在隔离 schema 验迁移，没有升级正式库。

## 本轮工程检查原始输出

独立执行九个本期测试模块，真实隔离 PG schema/临时对象；完整输出 `tmp/phase8-review-final-tests.txt`。这些是仓库当前已有测试，HIGH 另用正式 Graph 反例补充，不能用该全绿输出掩盖缺口。

```text
----------------------------------------------------------------------
Ran 34 tests in 53.352s

OK
{"tests": 34, "failures": 0, "errors": 0, "skipped": 0, "seconds": 55.51500000001397}
```

输出中保留迁移反射对 `public.vector` 的 SAWarning，不把 warning 隐去或算失败；对应迁移测试结果为 ok。

独立后端 `python -m compileall -q src tests migrations`、前端 `pnpm exec vue-tsc --noEmit`：

```text
compileall_exit=0
vue_tsc_exit=0
```

typecheck stdout/stderr 为空，`tmp/phase8-review-final-typecheck.txt` 长度 0。首次重定向路径写错导致命令未执行，随后正确路径重新运行并取得以上 exit；那次工具路径错误不属于项目编译错误。

主 Agent 另有前端 55/55、0 fail/skip、Vite `✓ built in 57.85s`（`tmp/phase8-frontend-tests.txt`、`tmp/phase8-frontend-build.txt`）；本报告只引用为开发者证据，不称独立最终冻结源构建。主 Agent 后端全量/隔离浏览器工作仍在进行，本报告不预判其结果。

## 检查快照与后续审查

09:44:35 北京时间读取的核心修前 SHA256：

| 文件（backend/src/globalmail_agent/ 下） | SHA256 |
|---|---|
| attachments/understanding.py | B2D75B6B6E2585E715281C13D08B5F5DB88EF514CC8E3C72AF7D358D750B32A0 |
| attachments/evidence.py | 2D0F6E62728A6F858E2CF981A0D61F0CCD5D92426F45EC960209BEFD3F453D0D |
| application/fixture_conversations.py | D936C0AD784D451902A7F521B0C974ECA09699040E60F8DD5A361D82E0937680 |
| agent/memory.py | 78307692AEF27B6A84BC17F202D1CFD777853C9680DB0A9ADEC4FD3AFBDBB5F2 |
| application/conversation_queries.py | 228F6378C29705577C278075BBCA227EA572CAC94B8B4F4BEAD6576D92644AFD |

MEDIUM 发现时 `frontend/src/components/mail-agent/ImageEvidenceDrawer.vue` SHA256 为 `8C35D545E6964623A62A27CDB4309328C770F5454DC1F4E7B7EA7DFCE4840A65`。收口复查 understanding.py 已变为 `F3CCDFE7AFBC10DD9AB63B1876C9B6680746BC802D35E60D73AE7DCEFBF06584`，表明主 Agent 修复正在进行；本轮测试未做整个后端源前后冻结，不作为修复后当前源稳定全量证明。

Stage 1 有 HIGH，依 Skill 未执行 Stage 2：未完成代码质量/完整安全扫描/测试真实性专项/邻居基准页面实际渲染对照，均不能标 PASS。本轮没有改业务源码、commit、付费模型或正式数据库升级；只产出本报告和 Git 忽略的复现/测试日志。主 Agent 修复两项后按 Stage 1 失败路径补实现并重验，再派 fresh reviewer；保留本轮及初审 FAIL、Phase 1/7 质量延期状态，不勾整条产品 AC。
