# Phase 8 第三轮工程审查

日期：2026-10-09。独立 fresh code-reviewer；Git 基线 `09a818fa9976c94e5c50a090620993b324b603ea`，范围为本期工作区全部工程增量，排除 `.idea/` 和进化队列。使用 [.agents/skills/code-review/SKILL.md](../../.agents/skills/code-review/SKILL.md)。

**本轮结论：Stage 1 核心工程核对通过并进入 Stage 2；Stage 2 FAIL，2 项 MEDIUM，0 项新增 HIGH。本轮不是最终 PASS。** 发现后主 Agent 已开始修复两项；修后源码需按 fresh 规则从 Stage 1 重审，本报告保留修前失败，不用修复声明覆盖实际反例。

## 范围、计划与延期边界

直接读取 AGENTS、Product-Spec REQ-014/AC-065–082、主架构 4.3/4.4/6.3/隐私与提交契约、DEV-PLAN Phase 8、实施步骤、SESSION-HANDOFF、文档索引及前两轮 FAIL。审查顺序：逐条工程映射 → 接收/受控案例/来源 → 联合理解/预算/危险共事务接管 → 更正/撤销/晚到 → 实际工作台 → 质量/安全/测试真实性/邻居渲染。没有修业务代码、commit、升级正式库或派发子 Agent。

用户原文“倒不如继续开发 到时候整个项目跑通之后再调整这种细节”“现在继续开发Phase8吧”改变推进顺序，不放宽来源、预算、危险 HITL、停止、撤销和人工恢复。依据 `Product-Spec.md:5`、`AGENT-ARCHITECTURE.md:5`、`DEV-PLAN.md:7/178/191`：本轮 0 付费模型请求；固定模型/SDK 捕获只验证工程。Phase 1/7 原质量 FAIL、AC-082 和视觉业务语义仍延期、未通过；AC-069/071 正式售后写归 Phase 9；AC-078 完整删除/备份恢复归 Phase 12，本期即时撤销仍须有效。未勾选产品 AC。

## Stage 1：本期工程逐项核对

下表“已验证”仅指列出的确定性工程行为，不表示整条产品 AC 的模型语义或后续业务已验收。后端简称路径统一前缀为 `globalmail-agent/backend/src/globalmail_agent/`；测试统一前缀为 `globalmail-agent/backend/tests/`。

| Spec / AC | 本期工程结论与边界 | 代码和实际证据 |
|---|---|---|
| REQ-014 接收；AC-065 候选/仅图 | 本地上传和仅图消息已验证；候选语义/不重复补问延期 | `attachments/validation.py:8–52` 验实际 JPEG/PNG/静态 WebP、decode、10MiB/20M 像素；`intake.py:22–54` 上传不排模型；`binding.py:49–85` 仅 ready 原子绑定。`test_attachment_validation.py:31–64` 实际字节、方向、动图、损坏、边界；`test_attachment_intake.py:53–75` 实际 PG/HTTP。 |
| AC-066 精确候选/歧义/客户范围 | 来源与歧义工程门已验证；冲突澄清语义延期 | `attachments/understanding.py:42–75` 无歧义且原始读数含精确号码才获查单资格；`agent/tool_gateway.py:96–104` 当前客户业务范围。人工订单新修订优先由本轮四字段正式 Graph 反例证明，旧号不获有效投影。 |
| AC-067 观察/推测/定位 | 分层存储与对应原图已验证；识别准确率延期 | `attachments/understanding.py:15–24` 分栏；`attachments/evidence.py:61–85` 保存 hash/view/epoch/analysis/来源；`attachments/views.py:50–57` 明确整图、EXIF 校正和尺寸，不编精确框。`test_vision_graph.py:16–39` 真字节、逐图记录、实际 checkpoint。 |
| AC-068 正常外观不否定故障、局部不认缺件 | 规则已接入；模型是否遵守未验证 | `agent/prompts/visual-understanding.md:11–12`；`agent/graph.py:82–90` 实际送入联合节点。未用固定响应宣称语义通过。 |
| AC-069 订单/SOP/政策分流 | 本期来源/资格工程边界保持；正式申请 Phase 9，语义延期 | `agent/tool_gateway.py:96–154` 沿用精确业务服务；`application/draft_validation.py:35–45` 业务事实/适用步骤来源门；`agent/context.py:84–85` 明示本期无售后写工具。 |
| AC-070 危险直接 HITL | 核心工程已验证；危险识别/安全话术语义延期 | `agent/graph.py:94–127` 有效风险不走下一 decision；`application/commit_outcome.py:52–79` 同事务保存理解/风险/人审并撤权；`application/risk_records.py:33–60` 仅有依据人工决定处理 active 风险。`test_vision_graph.py:41–55` 1 模型请求、0 出站、持久 active risk。普通图片更正不解除风险门。 |
| AC-071 截图不覆盖账本 | 图片来源与工具权限工程门保持；真实售后动作/语义延期 | `agent/understanding.py:69–75` 图片事实不能冒充客户/人工/工具事实；`application/draft_validation.py:40–45` 账本声称须业务工具。`agent/prompts/visual-understanding.md:14–15` 不把退款/发货截图作执行凭证。 |
| AC-072 缺失/格式/真实失败 | 接收、逐图 failure_reason、missing/unsupported 已验证；撤销关联分析错误反馈另有 M1 | `attachments/importing.py:26–59` 保留缺字节；`attachments/lifecycle.py:5–8` 技术中断；`worker/agent_runner.py:138–152` 按真实错误码标 failed；`attachments/queries.py:15–19` 返回逐图原因。`test_vision_import.py:17–42`、`test_vision_corrections.py:88–99` 及独立 missing HTTP 反例。 |
| AC-073 附件/CID/仅图/远程/幂等 | 工程已验证；不执行 HTML、不取远程图 | `domain/conversation.py:25–50` 只传受控 ID 和元数据；`attachments/binding.py:12–46/49–85` 固定清单、CID/ID 去重、来源消息重试一致性；`application/conversations.py:25–31/40–58` 共事务绑定。`MessageTimeline.vue:29–35` 文本展示与图片按钮；上传端点不接路径/URL。 |
| 受控案例包；AC-073/074 合法历史图 | 实际字节接入和历史完整 Graph 已验证 | `application/fixture_conversations.py:37–44` 正式调用包加载；`attachments/importing.py:44–80` content_id 白名单、包内 resolve、size/hash/decode 后同事务登记。独立 `HISTORICAL_GRAPH`：受控 PNG 两封历史来信，首封当前可分析，未来图和正文不进模型，0 出站。 |
| AC-074 scope/用途/可见前缀 | 授权和未来拒绝已验证；无跨 run 联合理解缓存 | `attachments/queries.py:22–40/44–67/91–108` 全 scope、可见 seq、摘要、删除 journal；`attachments/evidence.py:17–39` 人工修订需当前可见且 epoch 一致。`test_attachment_lifecycle.py:91–102` 全 SCOPE_KEYS，`test_attachment_binding.py:80–105` 前缀/撤销，独立历史 Graph 对真实未来 bytes 不加载。 |
| AC-075 不可信图片不扩大权限 | 工程权限边界已核对；注入语义专项延期 | `agent/prompts/visual-understanding.md:14–17`；`agent/graph.py:163–171` 未声明工具拒绝；`api/security.py:38–45` Origin/写入类型门仅为 raw upload 增白名单；`attachments/importing.py:62–80` 包外字节拒绝。没有新增 OCR、外链访问或外部交易工具。 |
| AC-076 原预算/未知 usage | 工程计量已验证；实际模型视觉耗时/语义延期 | `attachments/views.py:17–31` EXIF/1024 全图与保守 patch 上界；`agent/budget.py:46–65/72–96/98–110` 6 请求、6 视图、12 工具、16k/80k/120秒；`agent/graph.py:45–68` 每次重试重新预留/授权/结算。`test_vision_graph.py:57–70` 四图重试超过 6 视图显停、unknown 保留占用。 |
| 图像 bytes 不入 Graph/checkpoint/观测 | 本期工程已验证；真实 Langfuse 导出 Phase 11 | `adapters/model_provider.py:25–35` deepcopy 后临时 SDK data URL；`attachments/views.py:50–57` Graph 仅 refs；`test_vision_provider.py:12–24` 捕获真实 SDK 参数且原 messages 不变；`test_vision_graph.py:31–35` 实际检查点无 base64/image_url；事件仅安全字段 `application/event_store.py:6–10`。 |
| AC-077 晚到/停止/接管/新输入/更正/lease | 工程已验证 | `agent/guard.py:43–72` 共事务 slot→branch→conversation→排序 attachment→head→run/task/cycle；`attachments/corrections.py:39–86` row/input/epoch、人工权限并使旧 run 失效；`worker/jobs.py:58–62`、`worker/leases.py:128–134` 中断图状态。`test_vision_graph.py:72–99` 真实状态竞争；独立 lease 晚到为 `lease_expired`、0 分析、0 出站；更正和人工回复后均不能 claim，下一客户输入才新 run。 |
| AC-078 即时撤销/衍生依赖 | 即时禁止内容读取已验证；关联 API 错误处理 M1；完整物理删除延期 | `attachments/corrections.py:78–84` epoch/input 及旧 checkpoint 关闭；`attachments/revocation.py:10–21` 递归依赖门；`adapters/body_store.py:50–72` 统一读门；`application/run_records.py:40–50`、`adapters/checkpoint_repository.py:107–117` 旧 run/checkpoint 禁读。`agent/memory.py:14–30`、`application/human_review.py:16–21/76–90` 混合事实及人工派生依赖所有可见原图；独立 mixed fact 撤销后私有 marker 不可读。 |
| AC-079 逐图状态/关联/未覆盖 | 工程已验证；不同商品视觉映射语义延期 | `attachments/binding.py:12–34/73–85` 四图/20MiB/重复拒绝；`attachments/views.py:34–60` 受限全图及最多六视图；`agent/graph.py:79–81` 明确未覆盖；`attachments/understanding.py:42–49` 每请求图恰一分析，unreadable 不得产出字段/观察/风险。 |
| AC-080 人工修订保护/不恢复 | 前两轮 HIGH 的实际反例已关闭 | `attachments/understanding.py:78–104` 移除矛盾自动 facts/同字段 candidates/同列观察推测，并加入有来源 human_decision/人工订单候选；`agent/graph.py:95–115` 刷新有效 image sources；`attachments/evidence.py:42–43/69–78` 原始分析仅审计、pop 后不入有效 Understanding/Graph，并保护同列证据。四字段正式 PG→更正→人工回复→新客户来信→Graph，旧值均无有效资格，raw audit 保留。 |
| AC-081 上传/草稿/原图/证据/更正/撤销 | 本期主流程已验证；M1 为剩余辅助接口错误 | 前端 `ImageUpload.vue:37–88` 防串 scope、保留失败，`pending-image-uploads.ts:4–12` bytes+target 同未知结果复用 key；`ImageEvidenceDrawer.vue:71–102` allSettled 独立保留证据并以 page 或 image epoch 撤销，`:27–37/110–114` 具体字段/依据/危险确认。独立真实浏览器 missing preview503→确认撤销→已移除禁用；原图/更正主流程另见开发者截图，本轮不将其冒充独立操作。 |
| AC-082 冻结真实模型专项 | **延期、未执行、未通过** | `DEV-PLAN.md:178/191`。本轮固定输出和 SDK capture 均无模型网络请求，不能证明字段/观察/分流/禁止动作准确率。 |
| 24h暂存/草稿取消与引用清理 | 工程已验证 | `attachments/intake.py:67–144` 只清无消息引用、复查 FK/衍生依赖；`worker/agent_runner.py:165–178` 定期扫。`test_attachment_lifecycle.py:16–89` 真 PG/对象验证绑定/引用保留、过期禁读、磁盘失败回滚和删除 journal。 |

## Stage 2：2 项 MEDIUM

### M1：撤销一图后，另一图的关联证据端点返回无解释的 500

需求依据为 `Product-Spec.md:538/547` 的真实失败原因及证据工作台，质量依据为 code-review skill 的错误处理/故障交互真实性。它没有突破撤销隐私门，故为 MEDIUM。

修前位置：`globalmail-agent/backend/src/globalmail_agent/attachments/evidence.py:97/106` 对 `read_body` 返回值直接 `json.loads`。两图联合 analysis 的内容依赖两张原图；撤销 A 后，该 analysis 和由它派生的 B 证据被统一门返回 REDACTED。B 原图仍合法可看，但 JSON 解码 REDACTED 导致 `500 internal_error`。保守拒绝共享分析内容是正确的权限方向；错误必须明确表示撤销依赖失效，不能伪装内部故障。

独立实际 PG/Graph/HTTP 反例：上传两图→联合分析→转人工→撤销 A→B 原图 HTTP 200→B visual-evidence HTTP 500。模型为固定工程响应，原图是实际 Pillow PNG。完整输出：[closure-multi-revoke-fail.txt](artifacts/phase8/closure-multi-revoke-fail.txt)。

```text
AssertionError: 500 not found in (200, 410) : {"code":500,"msg":"internal_error","data":null,"request_id":"1f41c205-162a-44c5-83b3-cf17a7ba1182"}
Ran 1 test in 3.267s
FAILED (failures=1)
{"tests":1,"failures":1,"errors":0,"skipped":0,"successful":false,"source_changed":false}
```

主 Agent 已将这些 JSON 读取改为严格 `read_bytes` 410 门并新增正式两图回归；本轮**未重跑这个失败反例验证修复**。当前修后 evidence.py SHA256 为 `1391D829A2A49E1EA453957FB5E159633CD7FDFDDF4993E524AA8DCB543256A9`，属于下一轮审查输入，不能关闭本轮 FAIL。

### M2：改动后的工作台 composable 为 301 行

硬标准：`.agents/skills/code-review/SKILL.md:35`“文件不超 300 行”；`docs/planning/PHASE-8-IMPLEMENTATION.md:14` 同样规定 source 单文件不超过300行。修前 `globalmail-agent/frontend/src/composables/useMailWorkbench.ts:301` 超限；本期安全/长度扫描 67 个 src/migration 文件，仅这一文件超过300，其他文件均在门内。原始数值：[closure-security.json](artifacts/phase8/closure-security.json)。

```text
files=67
max_lines=301
over_300=[{file:globalmail-agent/frontend/src/composables/useMailWorkbench.ts,lines:301}]
```

主 Agent 去掉一空行后当前读取为300行。未以这个当前单项数值宣称本轮两阶段通过；下一 fresh reviewer 须对冻结最终源重新检查。

## Stage 2 其余质量、安全、真实性与视觉

| 检查 | 结论与证据 |
|---|---|
| 职责、类型、结构 | 附件 validation/intake/binding/importing/views/evidence/corrections/queries/lifecycle/revocation 分模块，新增源码均≤300行；TS 新增接口显式类型，没有 any；主要结构证据 `attachments/validation.py:16`、`views.py:34/63`、`corrections.py:38`、前端 `attachment-contract.ts:1–38`。长度唯一失败见 M2。 |
| 安全扫描 | 67个本期 src/migration 文件中 eval、raw HTML、前端 key/secret/token、硬编码凭据、TS any、shell=True 危险模式均0匹配，详见 [扫描原件](artifacts/phase8/closure-security.json)。人工核对上传限流/实际格式/路径白名单、复合 FK、scope、Origin 和 nosniff/no-store：`validation.py:16–52`、`importing.py:62–80`、`adapters/attachment_schema.py:24–33/55–62`、`api/attachments.py:28–54`。该扫描不等于整项目或第三方依赖漏洞审计。 |
| 图像预算/处理模式核查 | 官方 [视觉理解计量](https://www.alibabacloud.com/help/en/model-studio/vision-model) 描述32×32 patch计量；项目 `views.py:26–31` 使用两倍 patch 数再加512的保守预留。官方 [Pillow Image](https://pillow.readthedocs.io/en/stable/reference/Image.html)、[ImageOps](https://pillow.readthedocs.io/en/stable/reference/ImageOps.html) 区分 verify 与实际加载及方向校正；项目 `validation.py:37–43` 同时 verify/load、先限制像素与帧数。这里确认实现依据，不宣称真实供应商 usage/时延已验收。 |
| 测试真实性 | 实际 JPEG 追加合法尾部 padding 验10MiB与三张7MiB总量，不靠改 DB size 欺骗生产路径：`test_attachment_validation.py:58–64`、`test_attachment_binding.py:69–78`。VisionFixture 调用真实 PG/HTTP/Graph/对象/SDK接口；固定识别及固定语义审批明确只作工程 fixture：`vision_fixture.py:12–24`、`agent_fixture.py:43–79`。本轮另构造四字段有效 facts/source、missing preview503、真实 lease 过期、历史未来字节、混合来源事实以及 M1 故障；没有用绿测试掩盖新增失败。 |
| 旧schema迁移前提 | `test_knowledge_migration.py:34–54` 在0003按旧消息/event/job契约造数据再升级，验证旧job/run/cycle及对象保留，不让当前head服务假装能完整运行旧schema；`attachments/importing.py:26–28` 无元数据直接return避免无必要的新表查询。本轮冻结8项实际隔离迁移/附件反例0fail/error/skip。 |
| Spec漂移 | 新3张图片表、新暂存/原图/证据/更正/撤销 API 与组件均属于REQ-014/Phase8，见 `adapters/attachment_schema.py:9/34/43`、`main.py:81–82` 路由注册、`api/attachments.py:20`、`api/visual_evidence.py:10`。没有新增独立视觉Agent/OCR、共享图片RAG、真实邮箱、售后效果或完整删除成功入口。 |
| 实际邻居渲染 | 独立在1280×720打开工作台图片证据抽屉、既有人审抽屉及知识库邻居页面，实际截图比较 Element Plus按钮/标签/抽屉标题/字号/边框/留白。图片520px宽、人审420px宽均受100vw限制，沿用相同主题组件；没有仅数组件就算视觉通过。代码 `ImageEvidenceDrawer.vue:2/17/27/39`、`views/mail-agent/index.vue:148–165`、`ReferenceDrawer.vue:2–18`。证据：[图片抽屉](artifacts/phase8/closure-missing-before.png)、[邻居人审](artifacts/phase8/closure-neighbor-human.png)、[邻居知识库](artifacts/phase8/closure-neighbor-knowledge.png)。未在本轮独立验证明暗/1440×900全部状态，不追加此类结论。 |

## 独立验证原始输出与快照

首次独立九个附件/视觉模块（真隔离PG/临时对象，修前）完整输出 [closure-tests.txt](artifacts/phase8/closure-tests.txt)：

```text
Ran 35 tests in 56.034s
OK
{"tests":35,"failures":0,"errors":0,"skipped":0,"successful":true,"source_changed":false}
```

四字段正式 Graph/缺字节 HTTP/lease 首次扩展复现使用错误的UI呈现scope读取审计对象，产生4个 `body_not_found`，是复现脚本前提错误，日志 `tmp/phase8-review-closure-repro.txt` 保留。改为读取真实 conversations 行后，四字段全部通过；该次运行恰逢主 Agent 改 importing.py，3项绿但 `source_changed=true`，完整原件 [closure-manual-repro.txt](artifacts/phase8/closure-manual-repro.txt)，**不作为冻结源证明**。

修正后在冻结源重跑四字段/lease/missing、四项 import 和旧schema迁移，共8项；完整输出 [closure-frozen-focused.txt](artifacts/phase8/closure-frozen-focused.txt)：

```text
Ran 8 tests in 24.495s
OK
MANUAL_GRAPH {"key":"sku","old_effective":false,"manual_effective":true,"raw_audit_preserved":true,"automatic_resume":false}
MANUAL_GRAPH {"key":"model","old_effective":false,"manual_effective":true,"raw_audit_preserved":true,"automatic_resume":false}
MANUAL_GRAPH {"key":"error_code","old_effective":false,"manual_effective":true,"raw_audit_preserved":true,"automatic_resume":false}
MANUAL_GRAPH {"key":"order_number","old_effective":false,"manual_effective":true,"raw_audit_preserved":true,"automatic_resume":false}
LATE_LEASE {"error":"lease_expired","analysis_count":0,"outbound_count":0}
MISSING_HTTP {"preview":503,"evidence":200,"correction":422,"revoke":200,"status":"revoked"}
{"tests":8,"failures":0,"errors":0,"skipped":0,"successful":true,"source_changed":false}
```

已在主 Agent要求收口前启动的历史/混合来源两项补证收取结果，完整输出 [closure-extra-tests.txt](artifacts/phase8/closure-extra-tests.txt)、逐文件前后SHA [closure-extra-snapshot.json](artifacts/phase8/closure-extra-snapshot.json)：

```text
Ran 2 tests in 7.681s
OK
HISTORICAL_GRAPH {"visible_images":1,"future_images":0,"actual_image_decode":true,"outbound":0}
MIXED_FACT_REVOKE {"previously_readable":true,"marker_readable_after_revoke":false}
{"tests":2,"failures":0,"errors":0,"skipped":0,"successful":true,"source_changed":false}
```

这一2项快照已含修后 evidence.py，但没有执行 M1 修复反例；不能把补证冒充修后完整复审。Understanding SHA 为 `F3CCDFE7AFBC10DD9AB63B1876C9B6680746BC802D35E60D73AE7DCEFBF06584`；importing SHA 为 `791B53E87615ECD65D943E492E3B7B04167B013937FE012E815A4188B3379B2C`。

独立编译：后端 `python -m compileall -q src tests migrations`，前端 `pnpm exec vue-tsc --noEmit`；后者 stdout/stderr 为空，原件 [closure-typecheck.txt](artifacts/phase8/closure-typecheck.txt)。工具原始输出：

```text
compileall_exit=0
vue_tsc_exit=0
```

开发者前端记录为55 tests/55 pass/0 fail/skip及 Vite `✓ built in 27.68s`（`tmp/phase8-frontend-tests.txt`、`tmp/phase8-frontend-build.txt`）；本报告只作为开发者构建证据引用，不称独立最终全量构建。主 Agent 后端完整回归遇源变化会保留原snapshot；本轮未复制其全量结果为自己验证。

独立浏览器在现有隔离18181/15174创建 `closure-missing@example.test`，立即takeover取消模型队列。缺字节抽屉实际看见503提示及空证据，未出现人工更正表单；点击撤销→危险确认→确认后按钮禁用、状态“已移除”，人审保持。截图 [操作前](artifacts/phase8/closure-missing-before.png)、[操作后](artifacts/phase8/closure-missing-after.png)。既有人审记录实际显示0/6模型、0/12工具。没有触发真实模型/真实邮箱；测试schema和对象由原fixture清理，浏览器页已关闭。

## 收口

前两轮核心 HIGH 的人工有效字段、受控案例入口、缺字节状态、混合事实/人工派生撤销与摘要读取问题已有独立工程证据；不改历史FAIL。当前本轮新增M1/M2已报告并由主Agent修复，但本轮保留 **Stage 2 FAIL**。下一轮 fresh review 需要按最终源重读Stage1，再确认B证据明确410/无正文、300行门及相关编译和定向回归，不能只凭“已修”标PASS。模型质量、售后写、完整删除和82项整体产品验收继续留后续阶段。
