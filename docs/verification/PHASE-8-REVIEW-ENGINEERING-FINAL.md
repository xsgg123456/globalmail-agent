# Phase 8 第四轮工程审查

日期：2026-10-09。fresh code-reviewer，基线 `09a818fa9976c94e5c50a090620993b324b603ea`；审查本期工作区增量，排除用户 `.idea/` 和进化队列。执行 [code-review skill](../../.agents/skills/code-review/SKILL.md)。只产出本报告，不修代码、不提交、不派发、不调用付费模型。

**本轮结论：Stage 1 本期工程 PASS；Stage 2 FAIL，1 项 MEDIUM。文件名 ENGINEERING-FINAL 不表示通过。** 第三轮的 GET 证据 500 和 301 行问题已独立复核关闭；本轮发现同类 JSON 读取问题还存在于更正 POST。主 Agent 收到发现后已修复；本报告保留修前实证，不能为尚未独立复审的修后最终源背书。

## 范围、原文与计划

已直接读取 AGENTS、skill、code-reviewer.toml、Product-Spec REQ-014/AC-065–082、AGENT-ARCHITECTURE 4.4及表/API/提交契约、DEV-PLAN Phase 8、PHASE-8-IMPLEMENTATION、SESSION-HANDOFF 顶部、PHASE-8-VALIDATION、前三轮 INITIAL/FINAL/CLOSURE 原报告及本期 diff/新增附件模块。审查顺序：逐条需求及延期边界 → 接收/受控导入/授权 → 联合理解/预算/HITL → 更正/撤销/晚到 → 质量、安全、测试真实性、编译和实际邻居视觉。

用户明确“倒不如继续开发 到时候整个项目跑通之后再调整这种细节”“现在继续开发Phase8吧”。`DEV-PLAN.md:7/178/191`、`AGENT-ARCHITECTURE.md:5` 和实施步骤已同步。本轮只验工程行为；Phase 1/7 模型质量原 FAIL、字段/观察/分流语义及 AC-082 仍延期、未通过。AC-069/071 的正式售后写属于 Phase 9，AC-078 的完整副本删除/备份恢复属于 Phase 12。延期不放宽客户/分支/用途/历史来源、预算、HITL、撤销和副作用门。

正式库 0005 保持，不升级或重启；全部本轮 API/PG 反例使用 fixture 的随机 schema 和临时对象。工程固定模型和 SDK 参数捕获不能证明识别质量。无设计稿/Brief，UI 以现有 Art Design Pro/Element Plus 页面为基准。

## Stage 1：本期工程 PASS

以下逐项覆盖 REQ-014 的所有 MUST 和 AC-065–082。“工程通过”只对应表内确定性行为，不能勾选整条产品 AC。表内后端相对路径统一为 `globalmail-agent/backend/src/globalmail_agent/`，前端相对路径统一为 `globalmail-agent/frontend/src/`；测试相对路径统一为 `globalmail-agent/backend/tests/`。本表对应本轮发现前的审查源码；收口时主 Agent 又修了机器 JSON 同类读取，见末节。

| 条目 | 本期工程结论与延期边界 | 代码及实际证据 |
|---|---|---|
| 接收真实格式/限制；AC-065 | 本地真实图片、仅图来信、候选来源工程通过；提取准确性及不重复补问语义延期 | `attachments/validation.py:8/16/29/37/39` 实际格式、帧、像素、verify+load，4图/10MiB/20MiB/20Mpix；`intake.py:22/43` 不排模型；`binding.py:49/64/73` 原子绑定。`test_attachment_validation.py:31/44/58`、`test_attachment_intake.py:53` 真字节/PG/HTTP，主 Agent [页面读回](artifacts/phase8/browser-api.json)证明仅图创建。 |
| 候选原读数/歧义/客户限制；AC-066 | schema/来源、歧义精确查单门通过；图文冲突/多商品澄清语义延期 | `attachments/understanding.py:8/42/57/68` 保存 raw/value/歧义，订单必须匹配无歧义候选；`agent/tool_gateway.py:96` 只走当前会话业务查询。本轮四字段正式 Graph 运行证明人工订单候选有效、旧号不有效；输出见独立验证。 |
| 观察/推测/位置；AC-067 | 分层存储和实际原图引用通过；识别准确率/责任和根因判断语义延期 | `attachments/understanding.py:15`、`attachments/evidence.py:42/61/79` 保存 analysis/view/hash/epoch/kind；`attachments/views.py:50` 标明实际整图及EXIF/尺寸，不伪造框。`test_vision_graph.py:38`（收口前为第30行起的同名测试）验证实际两图和检查点。 |
| 外观正常/局部图；AC-068 | 原规则已送入联合节点；模型是否遵守未通过验收 | `agent/prompts/visual-understanding.md:11` 明示未见不等于无功能故障/无缺件、反光不当裂纹；`agent/graph.py:82` 实际加载。没有把 Prompt 存在当作模型语义 PASS。 |
| 联合正文/订单/SOP/政策分流；AC-069 | 工程来源/资格边界通过；正式申请 Phase 9、语义延期 | `agent/graph.py:82` 同次理解；`agent/tool_gateway.py:96` 及 `application/draft_validation.py:35/40` 保留精确工具和适用步骤来源门；`agent/context.py:84` 明示售后写不可用。本期没有自动授予赔偿或履约资格。 |
| 危险直接共事务 HITL；AC-070 | 确定性接管通过；危险识别和安全话术语义延期 | `agent/graph.py:94/117` 有效风险不等下一次决策；`application/commit_outcome.py:52/64/74` 同事务保存理解/风险/人审并撤自动权；`application/risk_records.py:33` 明确人工风险修订。`test_vision_graph.py:61`（本轮初读为第41行起）固定合法风险验证仅1模型请求、0出站及active风险；本轮 lease 反例仍拒晚到。 |
| 截图不是账本；AC-071 | 图片 source kind/工具权限门通过；Phase 9 正式动作和截图语义延期 | `agent/understanding.py:69/72` 图片不得伪装人工/客户/工具事实；`application/draft_validation.py:40` order_fact 必须业务工具；`agent/prompts/visual-understanding.md:14` 不把截图当退款/发货结果。工具白名单没有本期之外的交易效果。 |
| 每图状态/缺失/不支持/真实失败；AC-072 | 接收、failure_reason及真实缺字节路径通过；辅助 POST 错误处理列 Stage 2 M1 | `attachments/importing.py:26/41` missing/unsupported保留；`attachments/lifecycle.py:5` 中断码；`worker/agent_runner.py:138/146` 按真实技术原因置 failed；`attachments/queries.py:15` 返回原因。本轮 missing HTTP：preview503/evidence200/correction422/revoke200；不会拿无字节伪造人工结论。 |
| 附件/CID/仅图/远程/幂等；AC-073 | 工程通过 | `domain/conversation.py:25/43` 仅受控 IDs及元数据，metadata不能替代仅图；`attachments/binding.py:12/37/49/79` 重复ID/CID拒绝、清单固定、同消息重试一致；`application/conversations.py:25/43` 同事务接受；前端 `components/mail-agent/MessageTimeline.vue:29` 按文本展示，无HTML执行。上传HTTP没有路径/URL入口。 |
| 受控案例包/合法历史图；AC-073/074 | 真字节导入及历史 Graph 通过 | `application/fixture_conversations.py:40` 正式入口调用；`attachments/importing.py:44/62` manifest content_id、包内resolve、最大读取、SHA与decode。本轮完整历史 Graph：1可见图、0未来图、真实PNG、未来正文不入模型、0出站。 |
| scope/用途/可见前缀/缓存；AC-074 | 授权工程通过；默认无跨run联合缓存 | `attachments/queries.py:22/37/44/91` 全scope、消息prefix、原/缩略图摘要及journal；`attachments/evidence.py:17/30` 人工修订也需当前可见/epoch；`attachments/views.py:63` 每次重新授权。`test_attachment_lifecycle.py:91` 逐SCOPE_KEYS拒绝；本轮真复合FK迁移反例和历史未来bytes检查通过。 |
| 不可信图片/注入；AC-075 | 工程权限边界通过；注入语义专项延期 | `agent/prompts/visual-understanding.md:14` 数据不授工具权；`agent/graph.py:163` 未声明工具拒绝；`api/security.py:38/41` Host/Origin/类型门保留，raw只为上传白名单；`attachments/importing.py:62` 只读取受控manifest。没有默认OCR、外链读取或额外视觉Agent。 |
| 原预算/未知用量；AC-076 | 确定性计量通过；真实视觉模型usage/时延及语义延期 | `attachments/views.py:17/26` 1024受限全图、非生成式处理和patch上界；`agent/budget.py:46/53/72/98` 6请求/6视图/12工具/120秒/16k/80k；`agent/graph.py:45/54/66` retry重新授权/预留/结算，unknown不归零；`adapters/model_provider.py:11/38` validation3990+10/2048thinking保持。`test_vision_graph.py` 同名 `test_network_retry_charges_views_unknown_usage_and_stops_over_six` 真4图重试在第二网络前拒绝。 |
| 图像字节/观测/RAG | 本期工程通过；正式 Langfuse 导出 Phase 11 | `adapters/model_provider.py:25/28/34` deepcopy后临时data字节；`attachments/views.py:50` Graph只refs；`observability/local_records.py:19` `_visual_raw_images` 在持久有效Understanding前由 `attachments/evidence.py:43` pop。`test_vision_provider.py:12` 捕获实际SDK参数、原messages不变；`test_vision_graph.py` 实际checkpoint没有base64/image_url。没有图片共享向量库写路径。 |
| 晚到/停止/接管/新输入/重置；AC-077 | 工程通过 | `agent/guard.py:43/54/66` 共事务统一锁序及fence/处理权；`attachments/corrections.py:47/78` row/input/epoch更改并关旧checkpoint；`worker/jobs.py:58`、`worker/leases.py:128` 中断processing。本轮真实失效lease后0分析/0出站；已有 `test_vision_graph.py` stop/takeover/input/revoke实际回调反例，本轮引用主 Agent37项测试结果。 |
| 即时撤销和衍生读取；AC-078 | 本期即时禁读通过；完整物理清理/备份恢复未实现、延期 | `attachments/revocation.py:10` 递归content_dependencies拒读；`adapters/body_store.py:50/64` 文本redaction/字节410；`application/run_records.py:40`、`adapters/checkpoint_repository.py:107` run/checkpoint禁读；`agent/memory.py:14/30` 混合事实登记所有可见图；`application/human_review.py:16` 人工note/draft/reply登记图片依赖；`commit_outcome.py:74` reason不存原摘要。本轮混合事实撤销marker不可读，两图撤销A后B原图200、共同证据410；仅辅助B更正错误反馈失败见M1。 |
| 多图/重复/超限/逐图覆盖；AC-079 | 工程通过；不同商品视觉对应语义延期 | `attachments/binding.py:12/73` 四图和总量、重复拒绝；`attachments/views.py:34` 全轮有界选取；`agent/graph.py:79` 明示未覆盖；`attachments/understanding.py:42/49` 每请求图恰一分析、unreadable不能产字段/观察/风险。实际两图联合请求、原图PNG和限制测试覆盖，未把一图成功说成全图已读。 |
| 人工有效优先及下一来信屏障；AC-080 | 本期主流程通过；M1为共同旧分析失效后的错误反馈缺陷 | `attachments/understanding.py:78/87/98` 去旧自动facts/同字段candidate/intent；`agent/graph.py:106/111` 重新投影有效source；`attachments/evidence.py:69/76` 不覆盖同列人工；`attachments/corrections.py:78` 更正不排run、不恢复。独立四字段正式PG→更正→人工回复→新来信→Graph均旧值不有效/人工值有效、raw审计保留；risk另需明确人工门。 |
| 工作台原图/草稿/状态/更正/撤销；AC-081 | 主流程工程通过；M1为辅助故障错误反馈 | 前端 `components/mail-agent/ImageUpload.vue:37/50/66` 防串scope、同bytes重试key、失败保留；`pending-image-uploads.ts:4`；`ConversationDialog.vue:175`、`MessageComposer.vue:55` 支持仅图；`ImageEvidenceDrawer.vue:71/85` allSettled独立保存、fallback epoch真撤销、表单/危险确认。metadata无服务器路径/凭据；本轮真实原图及证据UI可读，主Agent实际503保稿→真APIretry记录见验证报告。 |
| 冻结真实模型专项；AC-082 | **延期、未执行、未通过** | `DEV-PLAN.md:178/191/328`、实施步骤第6步；本轮0付费模型调用，工程fixture不算字段/观察/分流/禁止动作准确率。Phase1/7原FAIL全部保留。 |
| 草稿取消/24h过期 | 工程通过 | `attachments/intake.py:67/90/127` 只取消未绑定、复查引用/FK再清理；`worker/agent_runner.py:165` 定期扫；`test_attachment_lifecycle.py:16/42` 覆盖绑定/引用保留、过期/磁盘失败/journal。没有把草稿清理称为Phase12完整删除。 |

新增三表 `adapters/attachment_schema.py:9/34/43` 与冻结 DDL `migrations/versions/0007_visual_evidence.py:1/114`，上传/预览/证据/更正/撤销API `api/attachments.py:20`、`api/visual_evidence.py:10` 均落在REQ-014/Phase8。未发现本期新增scope creep、死引导、独立OCR、真实邮箱或售后效果工具。UI明确完整副本删除留后续；没有未实现删除成功入口。

## Stage 2：FAIL，1 项 MEDIUM

### M1：撤销联合分析的一张图后，另一张图的更正 POST 仍返回500

依据：`Product-Spec.md:538/546/547` 要求真实失败原因、有来源人工更正和可操作证据工作台；[code-review skill](../../.agents/skills/code-review/SKILL.md)要求错误处理和可达故障用例。没有突破撤销隐私门，不是新模型语义问题，定级 MEDIUM。

修前位置：`globalmail-agent/backend/src/globalmail_agent/attachments/corrections.py:67` 的 `json.loads(read_body(conn, self.store, conv, row["body_object_id"]))`。两图联合 analysis 对两张图都有依赖。撤销A后B原图仍获准，但B旧evidence内容依赖A，被read_body返回REDACTED；更正B在遍历旧证据时把REDACTED当JSON解析，最终成为500 internal_error。

本轮独立真实PG/Graph/HTTP前提：实际上传两张PNG→一次合法联合Understanding→转人工→撤销A→读取当前row_version/input_revision/B epoch0→B原图200→B证据410→POST B corrections带合法observation/value/reason。原图仍可看，UI的fallback epoch也允许发这个合法POST；没有绕过人工处理权、猜版本或伪造不可达参数。

原始输出：

```text
test_revoking_one_joint_image_keeps_other_preview_but_invalidates_shared_evidence ... ok
test_correction_after_other_joint_image_revoked ... FAIL
AssertionError: 500 == 500 : {"code":500,"msg":"internal_error","data":null,"request_id":"096d3084-be86-4214-b3b2-2d9c2894f8e2"}
Ran 2 tests in 5.701s
FAILED (failures=1)
JOINT_B_CORRECTION {"preview":200,"evidence":410,"correction":500,"body":{"code":500,"msg":"internal_error","data":null,"request_id":"096d3084-be86-4214-b3b2-2d9c2894f8e2"}}
{"tests":2,"failures":1,"errors":0,"skipped":0,"source_changed":false}
```

安全修复标准：机器JSON走严格read_bytes撤销门，返回明确410 image_content_revoked或有说明的安全拒绝，不解析显示占位符、不恢复被撤销内容；失败不改row/input/epoch、不触发自动run。保留文本展示用途的read_body。

主 Agent 已将该处及同类机器 JSON 路径改为严格read_bytes，并在正式两图测试增加POST B必须410/row及epoch不变。**本轮未独立执行这项修后反例，不关闭本轮FAIL。** 下一fresh reviewer应从Stage1读取最终源再验该POST及相关读取路径。

### 第三轮两项关闭证据

| 旧问题 | 本轮独立结论 |
|---|---|
| CLOSURE M1，B证据GET500 | 本轮稳定源两图真实Graph/PG/HTTP测试通过：B原图200且显式thumbnail=false为PNG，B共同证据410 image_content_revoked、正文无旧观察；`attachments/evidence.py:32/69/97/106` 全JSON读取已为read_bytes。上文2项运行中的第一项为独立通过。 |
| CLOSURE M2，composable301行 | 本轮扫描67个本期src/migration，最大300行、无超限；`frontend/src/composables/useMailWorkbench.ts:300` 实际为300。其SHA为`b9d0b3b1ff52bc1cec4c1224728c9ff45433eafff6533d4d516116fb07aba5a8`。 |

## Stage 2 其余质量、安全与视觉

| 检查 | 结论及证据 |
|---|---|
| 命名、职责、类型、大小 | 附件validation/intake/binding/importing/views/evidence/corrections/revocation/queries分模块；TS接口显式、`frontend/tsconfig.json:6` strict=true。67个本期src/migration实际行均≤300，TS any扫描0。结构见 `attachments/validation.py:16`、`views.py:34`、前端 `api/attachment-contract.ts:1/17/32`。错误处理唯一MEDIUM见M1。 |
| 安全扫描 | 本轮67文件eval/raw HTML/frontend VITE KEY/SECRET/TOKEN/硬编码密钥密码/shell=True/用户绝对路径/TS any扫描均0命中。另人工核对 `validation.py:17/26/33` 路径/字节/像素限制、`importing.py:62` manifest目录、`attachment_schema.py:24/59` 复合FK、`api/attachments.py:28/49` stream限制和no-store/nosniff、`api/security.py:38` Origin门。没有证据支持新增安全缺陷；不把此扫描称为全仓/第三方漏洞审计。 |
| 第三方处理依据 | 实际使用Pillow verify后重新open/load符合官方区分识别与真正解码的说明，`validation.py:37/39`；见[Pillow Image](https://pillow.readthedocs.io/en/stable/reference/Image.html)。官方Qwen视觉计量采用32×32 patch，项目 `views.py:26/31` 做受限尺寸与额外保守预留，见[Qwen视觉文档](https://www.alibabacloud.com/help/en/model-studio/vision)。本轮未实测供应商usage/语义，不能据文档推导质量通过。 |
| 测试真实性 | `test_attachment_validation.py:58` 真实JPEG合法padding覆盖10MiB；`test_attachment_binding.py:69` 实际三张7MiB经过生产stage触发总量，不伪改数据库size。`vision_fixture.py:12/20` 加载实际Pillow字节，真实PG/Graph/HTTP，固定识别审批明确只作工程fixture。本轮新增可达更正POST反例证明已有37项绿仍存在漏点；不能只用现有绿测试宣布质量通过。 |
| 旧迁移前提 | `test_knowledge_migration.py:34/43/50` 按0003时期消息/事件/job契约建种子后upgradehead，验证旧job/run/cycle和对象保留；`attachments/importing.py:26` 无metadata立即return，未放宽撤销。`test_attachment_migration.py:29/64/79` 0006旧行按旧形状冻结、升级保留和复合FK反例；本轮8项中这些测试均ok，但该8项源中途变化，不能称最终冻结证明。 |
| 视觉实际对照 | 本轮自有IAB实际打开1280×720工作台、phase8-final工程会话原图/证据抽屉、既有人审抽屉、知识库页面及新建知识表单，并逐页获取截图。图片抽屉520px/人审420px，统一白色背景、主题标题/标签/按钮/表单/边框、长内容滚动；没有发现本期偏离既有Art Design Pro/Element Plus。代码 `ImageEvidenceDrawer.vue:2/17/27/39`、`views/mail-agent/index.vue:140`、`ReferenceDrawer.vue:2`。本轮只读UI、不写会话、页已关闭。1280真实截图在本轮工具输出；主Agent [原图抽屉](artifacts/phase8/evidence-drawer.png)、[900视图](artifacts/phase8/evidence-drawer-900.png) 和第三轮 [邻居人审](artifacts/phase8/closure-neighbor-human.png)/[知识库](artifacts/phase8/closure-neighbor-knowledge.png)为另行引用证据，不冒充本轮900实测。 |

本轮扫描原始数值：

```text
files=67
max_lines=300
over_300=[]
hits=[]
```

## 编译、独立验证与源变化

本轮独立编译命令为后端`.venv/Scripts/python.exe -m compileall -q src tests migrations`，前端`pnpm exec vue-tsc --noEmit`，stdout/stderr没有编译诊断，原始退出值：

```text
compileall_exit=0
vue_tsc_exit=0
```

编译发生在主Agent同类修复前后附近，不能宣称独立最终冻结全量构建。主Agent另有 [前端55项](artifacts/phase8/frontend-tests.txt) 与 [Vite构建](artifacts/phase8/frontend-build.txt)的原始输出：

```text
ℹ tests 55
ℹ pass 55
ℹ fail 0
ℹ skipped 0
ℹ duration_ms 2520.6163
✓ built in 30.45s
```

本轮独立复用已读过源码的第三轮反例方法，执行四字段正式Graph、missing真实HTTP、lease晚到、历史真实图、混合事实撤销以及2个附件迁移/1个旧知识迁移，共8项。原始结果：

```text
Ran 8 tests in 27.448s
OK
MANUAL_GRAPH {"key":"sku","old_effective":false,"manual_effective":true,"raw_audit_preserved":true,"automatic_resume":false}
MANUAL_GRAPH {"key":"model","old_effective":false,"manual_effective":true,"raw_audit_preserved":true,"automatic_resume":false}
MANUAL_GRAPH {"key":"error_code","old_effective":false,"manual_effective":true,"raw_audit_preserved":true,"automatic_resume":false}
MANUAL_GRAPH {"key":"order_number","old_effective":false,"manual_effective":true,"raw_audit_preserved":true,"automatic_resume":false}
MISSING_HTTP {"preview":503,"evidence":200,"correction":422,"revoke":200,"status":"revoked"}
LATE_LEASE {"error":"lease_expired","analysis_count":0,"outbound_count":0}
HISTORICAL_GRAPH {"visible_images":1,"future_images":0,"actual_image_decode":true,"outbound":0}
MIXED_FACT_REVOKE {"previously_readable":true,"marker_readable_after_revoke":false}
{"tests":8,"failures":0,"errors":0,"skipped":0,"source_changed":true}
```

迁移反射原警告也保留：

```text
test_attachment_migration.py:43: SAWarning: Did not recognize type 'public.vector' of column 'vector'
test_attachment_migration.py:43: SAWarning: Did not recognize type 'public.vector' of column 'probe_vector'
test_attachment_migration.py:61: SAWarning: Did not recognize type 'public.vector' of column 'vector'
test_attachment_migration.py:61: SAWarning: Did not recognize type 'public.vector' of column 'probe_vector'
```

8项运行中主Agent修复了7个文件：`agent/context.py`、`agent/tool_gateway.py`、`application/draft_validation.py`、`application/understanding_revisions.py`、`attachments/corrections.py`、`worker/agent_runner.py`、`tests/test_vision_graph.py`。所以shell最终exit1是快照门拒绝，不是8项测试失败；本报告诚实保留`source_changed=true`，不将其作为最终冻结通过。

主Agent此前37项最终图片/旧迁移专项为 [focused-tests.json](artifacts/phase8/focused-tests.json)、[原日志](artifacts/phase8/focused-tests-final.txt)：37项/0fail/error/skip/54.968s/source_changed=false，覆盖本轮修前源码。第三轮35+8+2各稳定测试是旧独立证据，详见 [CLOSURE](PHASE-8-REVIEW-CLOSURE.md)，本轮读过且另有上述重验，不把旧实测冒充新运行。

主Agent完整后端回归原输出为317项/0fail/error/skip/677.333s，`backend-tests.json`明确`source_changed=true`；不能称最终冻结全量。首轮316旧迁移错误及新增原图/缩略图断言修前FAIL均保留。主Agent修后受影响模块定向回归尚在进行，本轮不预判结果、不追加无差别全量。

修前关键SHA：

| 文件 | SHA256 |
|---|---|
| `attachments/corrections.py` | `ce70d61aa6c356da77cae05d105cf7935e6bdb139be89c4576bb84ff83340d58` |
| `attachments/evidence.py` | `1391d829a2a49e1ea453957fb5e159633cd7fdfddf4993e524aa8dcb543256a9` |
| `attachments/understanding.py` | `f3ccdfe7afbc10dd9ab63b1876c9b6680746bc802d35e60d73ae7dcefbf06584` |
| `attachments/importing.py` | `791b53e87615ecd65d943e492e3b7b04167b013937fe012e815a4188b3379b2c` |

## 收口与下一轮

本轮完整Stage1工程审查没有HIGH，可以进入Stage2；Stage2新增B更正500的MEDIUM已真实复现，故本轮仍FAIL。源码同类修复已发生，但本轮没有将修后“已改”当作独立通过。主Agent按缺陷路径修复、保持严格撤销，并重新派fresh reviewer从Stage1核对最终少量变更及合法POST B的410/无状态变化。

前三轮及本轮原FAIL保持。AC082、Phase1/7质量、Phase9售后写、Phase12完整删除和82项整体验收继续保留后续边界；不因本期工程接收/更正/撤销可运行而称模型语义或全项目完成。
