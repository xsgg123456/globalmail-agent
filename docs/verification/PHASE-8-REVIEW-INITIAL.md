# Phase 8 工程初审

日期：2026-10-09。独立 fresh code-reviewer；基线 `09a818fa9976c94e5c50a090620993b324b603ea`，范围为本期工作区增量，忽略用户 `.idea/`、进化队列。执行 `.agents/skills/code-review/SKILL.md`。

**结论：Stage 1 FAIL，4 项 HIGH、2 项 MEDIUM。Stage 2 未执行。** 这是开发中的初始快照报告，主 Agent 已收到发现并开始修复；以下旧行号/复现实证不能代表修复后的当前源。必须另做最终审查，不能把本报告改写成 PASS。

## 审查边界及计划

已读 AGENTS、REQ-014/AC-065–082、主架构 4.4/6.3/隐私契约、DEV-PLAN Phase 8、PHASE-8-IMPLEMENTATION、SESSION-HANDOFF、文档索引及本期 diff/新增模块。顺序为需求逐项映射→附件/API/来源门→联合理解/预算/HITL→更正撤销→工作台与工程验证。

用户明确先跑通完整项目，再统一处理模型细节。本期审工程链路与确定性约束；不调用付费模型，不以模拟响应声称视觉语义准确率通过。Phase 1/7 原 FAIL 保留。AC-069/071 售后写归 Phase 9、完整副本删除归 Phase 12、AC-082 专项真实模型统一回归延期，均不当作本期工程开工阻塞。

## HIGH 发现

### H1：受控案例包没有图片字节接入路径

- 需求：Product-Spec.md:517 要求本地上传或受控案例包内 JPEG/PNG/静态 WebP；主架构:200/213 要求历史前缀中具备受控字节的附件可以分析。
- 初始实现：`globalmail-agent/backend/src/globalmail_agent/application/fixture_conversations.py:37–42` 只调用 add_message 写正文；`application/replay.py:30–35` 同样只写正文。`domain/conversation.py:82–100` 的 ImportMessage 没有附件字段且 extra=forbid；`attachments/intake.py:41–42` 拒绝历史模式暂存。没有任何这些入口调用受控包字节校验/对象登记/附件绑定。
- 后果：受控案例有清晰图片、仅图来信或历史图片时，也无法进入正式联合理解；这是入口缺失，不是延期的识别准确率。
- 验证：阅读上述完整调用路径及 `git diff HEAD`；初始源码明确无附件加载器。补齐时必须从受控 manifest 白名单解析文件、验 hash/实际格式/限额，保留原始可见时间，不允许请求体任意路径/外链。

### H2：现有案例的缺字节附件被静默丢弃

- 需求：Product-Spec.md:517/523、AC-072/079 要求缺字节保持 missing、逐图显示真实未读状态；主架构:200 允许有正文的邮件保存 missing 元数据。
- 初始实现：`application/fixture_conversations.py:37–42` 忽略 attachment_metadata；`domain/conversation.py:22–43` 只接受 ready staged ID 绑定；`attachments/binding.py:65–71` 拒绝一切非 ready 对象。虽然表/前端枚举有 missing/unsupported，生产接收路径不能生成这些状态。
- 真实 PG 复现：用仓库原始 SCN-020（`data/knowledge/v1/scenarios/inputs.jsonl:41`，附件 missing-part.jpg、content_available=false）创建场景，再使用正式 load_context：

```text
MISSING_METADATA {"original_name": "missing-part.jpg", "saved_message_attachments": [], "context_unread_attachments": []}
```

- 后果：UI 与模型都丢失“客户附件存在但未读取”的信息，也没有针对附件的补发路径。原始证据：`tmp/phase8-review-initial-repro.txt`。

### H3：人工更正后，同一列的矛盾模型推断仍成为当前有效证据

- 需求：AC-080、Product-Spec.md:527、主架构:235 要求后续运行使用人工新修订，旧分析/缓存不能覆盖人工判断；不是仅在 Prompt 中提醒。
- 初始实现：`attachments/corrections.py:51–69` 产生人工修订，`attachments/evidence.py:68–78` 后续仍无条件插入相同 kind/field 的自动证据；`attachments/evidence.py:86–95` 按当前 epoch 返回两者。`attachments/understanding.py:58–64` 只有查单候选针对人工订单号过滤，没有观察/推测及其 top-level facts 的确定性优先门。`agent/prompts/visual-understanding.md:10` 只是模型提醒。
- 真实 PG/Graph 复现：原图→模型分析→HITL→人工更正 observation 为“反光、无裂纹”→人工回复→下一封新客户来信→固定模型返回“可见裂纹”。本轮正常 handoff，证据 API 同一 epoch 返回：

```text
"active_observations": [
  {"manual": true, "value": "Human verified: reflection only, no visible crack", "epoch": 1},
  {"manual": false, "value": "Model says visible crack", "epoch": 1}
]
```

- 后果：矛盾自动结果继续作为当前证据交给后续决策/界面。可以保存原始模型分析作审计，但当前有效证据与可用 facts 必须受人工同列版本保护。原始证据：`tmp/phase8-review-initial-repro.txt`。

### H4：撤销门没有覆盖列内摘要及混合来源案件事实

- 需求：AC-078 的本期即时撤销部分、主架构:236/238 要求依赖内容立即禁止读取。完整副本物理删除延期不授权继续读取被撤销的派生内容。
- 漏点 A：`application/commit_outcome.py:73–76` 把图像推导的 handoff summary 直接复制进 human_reviews.reason；`application/conversation_queries.py:17–21` 只检查 note/draft/reply 对象，原样返回 reason。真实 PG 固定响应摘要含测试标记，撤销后：

```text
REVOKED_SUMMARY_READ {"reason": "Image extracted private marker REVIEW_PRIVATE_98122\n待核查：Check original image", "note": "（图片证据已撤销，相关派生内容不可读取）", "marker_still_readable": true}
```

- 漏点 B：`agent/memory.py:19–28` 对同时引用 mail+image 的事实，只登记 derived_from=mail.body_object，漏图片源。正式 update_case_state 工具接受合法双来源 visual_observation，随后撤销，`conversation_queries.py:82` 仍返回带测试标记的完整事实；`agent/context.py:62–66` 后续还可读入该候选事实：

```text
REVOKED_CASE_FACT_READ {"still_readable": ["[{...\"kind\":\"visual_observation\",...\"message_id\":\"image:34df63c8-de1a-418a-bc74-196345a2c455\",...\"value\":\"REVIEW_IMAGE_FACT_5711\"}]"]}
```

- 原始输出分别为 `tmp/phase8-review-revoked-summary-repro.txt`、`tmp/phase8-review-revoked-facts-repro.txt`。均实际调用领域服务/Graph/PG，模型是受控固定响应，0 付费。
- 修复应覆盖真正来源集合及所有读取投影，不只封 reason 一处。另 `application/human_review.py:16–18` 的人工正文/备注依赖仍仅枚举 mail bodies，应同步审计图片来源依赖登记。

## MEDIUM 发现

| ID | 问题与影响 | 初始证据 |
|---|---|---|
| M1 | 逐图 failed 没有具体失败原因；抽屉无法区分读取错误、视觉超时与进程中断。AC-072/081 要求真实原因及重发/重试路径。 | attachment_schema.py:9–31 无 failure_reason；attachments/lifecycle.py:5–7 只置 failed；attachments/queries.py:15–19 不返回错误；ImageEvidenceDrawer.vue:6/10–12 仅状态和空分析。全轮 RunPanel 错误不能替代逐图原因。 |
| M2 | 运行卡片仍显示“Phase 7 文本 Agent”，与后端 phase=8/images=true 及图片上传入口不一致。 | frontend/src/components/business/runtime-status.vue:48 固定文案；隔离浏览器 `127.0.0.1:15174/#/workbench` 实际 AX/截图确认。 |

表中省略公共前缀：后端 `globalmail-agent/backend/src/globalmail_agent/`；前端组件 `globalmail-agent/frontend/src/components/mail-agent/`。

## Stage 1 逐项覆盖

“工程已验证”只指指定确定性行为，不等于整条业务/模型 AC 勾选。延期内容照实保留。

| Spec/AC | 结果 | 代码/验证证据 |
|---|---|---|
| REQ-014 接收；AC-065 图片候选/仅图 | 本地 staged/仅图工程已验证；案例入口未实现 H1 | intake.py:22–54；binding.py:48–84；test_attachment_intake.py:53–75；test_attachment_binding.py:15–37。候选语义/业务回复延期。 |
| AC-066 歧义/冲突/客户范围 | 歧义候选门已实现；语义延期 | attachments/understanding.py:46–54 不允许 ambiguous 字段成为可用查单候选；agent/tool_gateway.py:96–102 精确有来源号码，沿用当前客户业务查询。冲突澄清内容未作真实模型验收。 |
| AC-067 观察/推测/来源位置 | 分层存储工程已实现；识别语义延期 | attachments/understanding.py:15–24；evidence.py:68–78；views.py:45–52 明确整图/尺寸，不伪造框；test_vision_graph.py:16–39 验证逐图证据/manifest。 |
| AC-068 外观不否定功能/局部不认缺件 | Prompt 规则已接入；语义延期 | prompts/visual-understanding.md:11–12；agent/graph.py:82–90。未据此宣布模型遵守。 |
| AC-069 指导/资格/内部申请 | 本期沿用工具/SOP/来源门；售后写 Phase 9，语义延期 | agent/tool_gateway.py:96–153；application/draft_validation.py:33–46 区分 order_fact/product_step/visual_observation。未把图片升为交易凭证。 |
| AC-070 危险直接 HITL | 核心工程已验证 | agent/graph.py:95–115；application/risk_handoff.py:5–9；commit_outcome.py:58–79 共事务理解/风险/人审；test_vision_graph.py:41–55 一次模型请求、0 出站、持久 active risk。 |
| AC-071 截图不改账本 | 工程工具边界保留；Phase 9 真动作/语义延期 | prompts/visual-understanding.md:14–15；agent/context.py:84–85 无售后写；draft_validation.py:39–46 账本 claim 须业务工具。 |
| AC-072 真实失败/重试 | 部分实现，H2/M1 | validation.py:45–52 拒绝损坏/伪类型；worker/agent_runner.py:138–151 failed/budget_exhausted；缺字节生命周期和逐图原因不完整。 |
| AC-073 附件/CID/仅图/远程/幂等 | staged/CID/仅图/幂等工程已验证；受控包 H1 | binding.py:12–34/48–84；test_attachment_binding.py:15–37/60–77/107–118；上传 API 无远程取图参数、邮件正文按文本展示。 |
| AC-074 客户/分支/用途/前缀 | 本地授权门已验证；历史合法字节入口 H1 | queries.py:22–40/44–67；test_attachment_lifecycle.py:91–102 全 SCOPE_KEYS；test_attachment_binding.py:80–105 前缀/撤销；test_attachment_migration.py:73–94 复合 FK。 |
| AC-075 图像指令不增权限 | 工程工具边界保持；语义延期 | prompts/visual-understanding.md:14–15；agent/tool_schemas.py:75–96 工具白名单；agent/graph.py:164–166 拒绝未声明工具；api/security.py:38–44 原 Origin/类型门保留。 |
| AC-076 原预算/未知 usage | 核心计量工程已验证；实际图像耗时/usage 不作质量结论 | views.py:17–31 有界 EXIF/1024 非生成式全图；agent/budget.py:46–65 累计6视图/6模型/80k/16k/120秒；:72–96 unknown 保留占用；test_vision_graph.py:57–70 4图重试超6显停、未知不归零。 |
| AC-077 晚到/屏障 | stop/takeover/new input/revoke 已验证；更正保护 H3 | agent/guard.py:43–72；test_vision_graph.py:72–99 在真实模型接口固定回调中改处理权/输入，旧结果无 analysis/understanding/出站；worker/jobs.py:58–62、leases.py:128–132 中断状态。 |
| AC-078 撤销/完整删除 | 即时撤销部分失败 H4；完整删除 Phase 12 | corrections.py:70–76；revocation.py:10–21；body_store.py:50–72；checkpoint_repository.py:107–117；test_vision_graph.py:101–120 预览/原分析/checkpoint 读取门通过，列内摘要和混合事实漏保护。 |
| AC-079 多图/超限/逐图未读 | 主流程工程已验证；missing H2、原因 M1 | binding.py:12–34/72–84；views.py:37–54 最多6视图；graph.py:79–81 明确未覆盖清单；understanding.py:31–38 每 attached ID 恰一分析、unreadable 无字段/观察/风险；test_attachment_binding.py:15–37/60–77。 |
| AC-080 人工版本及屏障 | 部分实现，H3 | corrections.py:39–48 的 version/input/epoch/处理权 CAS；:70–76 不生成 run、不恢复人工；当前有效自动证据仍可与人工冲突，实际 PG 复现。 |
| AC-081 工作台上传/原图/更正/撤销 | 主入口实际可见；M1/M2 | ConversationDialog.vue:39–43/175–180；MessageComposer.vue:55–69；ImageUpload.vue:37–88；ImageEvidenceDrawer.vue:63–109；API preview no-store/nosniff，metadata 不含服务器路径/凭据；隔离浏览器实际打开新建对话框，看见4图/10MiB/20MiB/上传不分析提示。 |
| AC-082 真实专项统一回归 | 经用户授权延期，未执行/未通过 | DEV-PLAN.md:178、PHASE-8-IMPLEMENTATION.md:工程验证步骤6；没有新增付费图像请求。 |

生命周期补充：暂存24小时及取消仅清无消息引用、无对象依赖源，`attachments/intake.py:90–143`；`test_attachment_lifecycle.py:16–41` 实测绑定/被引用源保留，过期/取消拒绝重读，磁盘失败事务回滚，删除 journal 拒绝原图/缩略图。图片临时 data URL 只在 `adapters/model_provider.py:25–35` 组装；Graph/checkpoint 固定工程用例确认不含 image_url/base64。没有加入共享 RAG、额外 OCR 或视觉 Agent，新增表/API/组件属于本期范围，未发现范围漂移。

## 工程验证原始输出

独立运行附件与视觉6个测试模块，临时私有 PG schema 和 TemporaryDirectory，对正式库不升级/写业务状态；不是实际 Qwen 语义测试。完整输出：`tmp/phase8-review-initial-tests.txt`。

```text
----------------------------------------------------------------------
Ran 25 tests in 47.083s

OK
{"tests": 25, "failures": 0, "errors": 0, "skipped": 0, "seconds": 47.07799999997951}
```

独立后端 `python -m compileall -q src tests migrations` 与前端 `pnpm exec vue-tsc --noEmit` 原始结果：

```text
compileall_exit=0
vue_tsc_exit=0
```

前端 typecheck stdout/stderr 为空，保存 `tmp/phase8-review-initial-typecheck.txt`。开发者已有前端测试输出55/55、构建 `✓ built in 25.99s`（`tmp/phase8-frontend-tests.txt`、`tmp/phase8-frontend-build.txt`），本报告不把它们冒充独立最终冻结源验证。旧 `tmp/phase8-typecheck.txt` 仍含已修复 TS2488，因此没有据旧日志误报当前编译失败。

三个真实复现脚本的清理凭证均为：

```text
CLEANUP {"callbacks_passed": true, "schema_removed": true, "temporary_objects_removed": true}
```

## 快照与收口

最初复现 H1/H2/H3 时的 SHA256：

| 路径（backend/src/globalmail_agent/ 下） | 初始 SHA256 |
|---|---|
| attachments/evidence.py | FB4C79B6800D3808367A3D8DC4285A704834CAE0864CDB2A08A68E1DDBD950C2 |
| attachments/understanding.py | 425E646ADCB3E50AC5AFDAC34FCF49F660309AA0528D3512D29898DDB3933E29 |
| application/fixture_conversations.py | DB955E22B80A8ED6E644AD4F2D0F50FA817DD8ECFF391CFDFA3C91712D523CF9 |
| domain/conversation.py | 8D7CFF1C1D23907B618AE2B46A5DA8E17250DF9C50B4814C19C3ED7BE71EE910 |

2026-10-09 09:38 北京时间检查，上述4个文件均已被主 Agent 修改，属于开发中的修复，未在本次初审关闭。撤销复现时 `agent/memory.py` SHA256 为 `0B36A1787F5196F407A5A9F1927ED63070D408965FBDEC3AD8961C2CF726AB28`；其他模块也须在最终源冻结后重新检查。

Stage 1 有 HIGH，依 Skill 停止 Stage 2：未执行代码质量/完整安全扫描/测试真实性专项/邻居页面视觉比较，不声明通过。主 Agent 修补工程缺口后，应从 Stage 1 重新派发 fresh 最终审查，并维护文档索引。本期不改原质量 FAIL，不提交 Git，不升级正式数据库，不勾产品 AC。
