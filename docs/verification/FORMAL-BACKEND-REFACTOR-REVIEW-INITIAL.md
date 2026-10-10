# 正式改造 Phase 14/15 后端独立审查

日期：2026-10-09。审查者：独立 code-review 子 Agent。采用 `.agents/skills/code-review/SKILL.md:14` 的证据要求与两阶段流程。

**结论：本次授权的后端工程范围 Stage 1 通过，Stage 2 通过；当前未留 HIGH/MEDIUM 后端缺陷。** 初查发现的边界问题及死分支维护项已交主 Agent 修正，并在新 Python 进程、随机隔离 PostgreSQL schema 中重验。临时探针已编入永久测试文件，永久 suite 的最终运行和后续 fresh 独审仍由主 Agent 收口。下列证据不代表全部产品 AC、真实模型业务质量、前端接入与视觉或完整项目验收通过。

审查期间源码仍有主 Agent 的工作区修改，本报告对应末次 23 项复测读取的版本；没有 Git 提交基准。审查者仅新增临时探针与本报告，没有改实现、暂存、提交或修改正式数据库。

## 1. 范围与依据

- 当前授权：`Product-Spec.md:3`、`:5`（v1.18 正式改造覆盖旧预览/交易实现叙述），`AGENT-ARCHITECTURE.md:5`。
- 实施与验收：`docs/planning/WORKBENCH-REFACTOR-IMPLEMENTATION.md:29` 至八项后端契约；`DEV-PLAN.md:51` 的 Phase 14/15 及后续验收边界。
- 仅审后端权限、记录、历史迁移及直接受影响的恢复/业务事实入口。前端正在主 Agent 修改，邮件与独立运行台的实际渲染、引导真实性、邻居页面视觉比较未执行，不能由本报告验收。
- 真实模型七类业务质量及全部历史 AC 由后续专项验收完成；本次使用可控模型输出来证明实际服务、数据库与网关边界，不将其称为真实模型业务验证。

为避免重复长路径，下文代码位置使用：

| 前缀 | 完整目录 |
| --- | --- |
| `B/` | `globalmail-agent/backend/src/globalmail_agent/` |
| `M/` | `globalmail-agent/backend/migrations/versions/` |
| `T/` | `globalmail-agent/backend/tests/` |
| `P/` | `tmp/` |

## 2. Stage 1：Spec Compliance

### 2.1 当前后端契约逐项对照

| 契约/要求 | 当前实现与证据 | 验证结果 |
| --- | --- | --- |
| 邮件只通信；运行台数据来自实际输入、返回与工具记录 | `B/application/run_records.py:33` 只读 run；`:67` 读取实际 tool 命令/结果；`:81` 读取逐 attempt model_calls；`:84` 返回当轮 context。`B/api/conversations.py:59` 只读建议接口。 | 完整实现。model_records 的 2 项永久测试与 P08 验证实际记录；GET 无 graph/enqueue 调用。前端展示排除于本范围。 |
| 四类首轮只读核查并转 HITL，进入持续人工；每封后续来信独立 human_assist | `B/application/human_assistance.py:9` 商业意图集合，`:28` 在 guarded 事务中切换会话、run、cycle 权限；`B/agent/graph.py:118` 来源验证后切换，`:184` 修订理解后再次切换；`B/application/conversation_base.py:68` 保留持续人工并排内部轮次；`B/application/task_queue.py:45` 入队继承模式。 | 完整实现。`T/test_human_assistance.py:36` 覆盖退款、退货、换货、补寄首轮与后续；P05 覆盖理解从非商业修订为商业后下一决策前转换。 |
| 内部辅助不得自动发信、创建/取消申请、冻结库存/资金或履约 | `B/agent/tool_schemas.py:85` 默认目录没有商业写工具；`B/agent/tool_menu.py:17` 内部终结仅 handoff；`B/agent/tool_gateway.py:29` 拒绝未注册工具及内部自主草稿；`B/application/commit_outcome.py:64` 最终提交再次拒绝非 handoff；`:79` 拒绝商业等待。 | 完整实现。`T/test_human_assistance.py:64` 直接调用真实网关验证恶意商业写工具及自主草稿拒绝；四类/后续测试断言无自主客户出站。 |
| 普通咨询/排障/物流仍可自主模拟回复；普通不确定 HITL 保留原恢复规则 | `B/worker/leases.py:27` autonomous 仅 owner=agent、gate=open 且非 persistent；`B/application/commit_outcome.py:87` 原有模拟完整回复提交；`B/application/conversation_base.py:71` 普通 human_wait_customer 后来信恢复。 | 完整实现。`T/test_human_assistance.py:99` 支持的普通回复仅发送一次；独立执行 test_agent_human、test_agent_faults 等 35 项，普通 HITL 恢复与故障屏障通过。 |
| 人工发送 input_revision++；在途旧结果不能产生效果；接管、停止、重试不绕权限 | `B/application/human_review.py:69` 人工发送，`:74` 精确 revision，`:79` invalidate，`:98`/`:102` revision++；`B/worker/leases.py:23` lifecycle/mode/owner/gate/revision/epoch/generation 联合资格；`B/agent/guard.py:43` slot/lease/fence 与资格校验；`B/worker/jobs.py:82` 重试再验权限。 | 完整实现。`T/test_human_assistance.py:74` 与 P04 验证人工回复抢先使旧 run superseded；晚到模型结果只保留诊断记录，artifact 数为 0。旧 stop/lease/takeover/checkpoint 故障测试通过。 |
| 结案后新来信仅登记，不重开、排队、takeover、retry | `B/application/conversation_base.py:67` closed 标志，`:76` 保持 resolved，`:81` 不重建开放 case memory，`:88` 不入队；`B/application/human_review.py:26`/`:72` open 门禁；`B/worker/jobs.py:86` open 门禁。 | 完整实现。`T/test_human_assistance.py:86` 与 P02/P03 验证来信保留已 resolved 的事项、无新 run；对结案前 stopped run 重试返回 retry_not_allowed。 |
| 业务更新仅更新事实与旧建议有效性，不 auto_wake，不默认注册旧模拟执行入口 | `B/application/branch_facts.py:60` invalidate，`:63` revision++、idle，`:65` facts_updated；无 enqueue；`B/application/waits.py:99` 始终 suppressed_by_human，`:104` revision/invalidate/在途调度归 idle，`:114` event suppressed；无 enqueue；`B/main.py:28`/`:86` 只注册新 facts 测试 API，未注册旧 simulation_router。旧售后路由只读。 | 完整实现。P06 使用 Agent 实际查询的库存资源更新，input_revision 2→3、advice stale=true、新库存值 7，无自动 run/outbox。旧历史表和读入口保留。 |
| 建议独立于客服个人草稿，不自动采用/覆盖；来源、时间与过期可追溯 | `B/application/advice_commit.py:11` 建议依赖 context/tool receipts，`:14` 未发送草稿单独对象，`:16` 保存 run/revision/实际 UTC 保存时刻 queried_at 与输入 as_of，`:19` 仅确保 review 存在；`B/application/conversation_queries.py:22` 仅 human_draft/human_note 作为 staff 字段；`B/application/conversation_advice.py:33` revision/最新 run/lifecycle 过期判断。 | 完整实现。P01 验证首次建议不会写客服 draft/note；后续辅助保留人工 Personal wording/verified note。P06 验证业务变更过期。前端人工采用确认未审。 |
| 每个网络 attempt 独立保留完整 messages/schema/tools/options/输出/usage/失败；reasoning 仅返回原文 | `B/agent/graph.py:45` 每 attempt reserve，`:71` finally 保存结果并 settle；`B/agent/budget.py:65` 唯一 usage request_key；`B/observability/model_records.py:11` 原始文本与配置，`:39` 返回对象，`:48` 读取状态；`B/adapters/model_provider.py:20` SDK retries=0，`:41`/`:43` 原样 usage/reasoning。 | 完整实现。`T/test_model_records.py:8` 逐项核对完整消息/schema/tools/output/reasoning；`:24` 两次超时产生不同 failed receipts、未知 usage。6 项 provider 测试核对真正 SDK 参数。没有构造 CoT。 |
| 失败、历史缺失、未启用、模型未返回 reasoning 必须显式；保留预算 | `B/observability/model_records.py:56` not_recorded/returned/failed/disabled/not_returned；`M/0010_human_assistance.py:22` 老 usage 默认 not_recorded；`B/agent/budget.py:56`/`:58` 保留图片/请求/token/120s限制，`:108` 工具预算。 | 完整实现。model_records 超时与 migration 老 usage 探针验证；35 项旧 Agent 故障/预算/恢复测试通过。未知 usage 未伪造为 0。 |
| 安全隔离：完整五维对象 scope；图片撤回后衍生记录不可读；晚到记录不能恢复执行权 | `M/0010_human_assistance.py:29` request/response/advice 的五维复合 FK；`B/adapters/body_store.py:63` scope/hash/revocation；`B/observability/model_records.py:33` 晚到保存前检查撤回、`:39` 衍生 response；`B/application/run_records.py:40` context 撤回门禁。 | 完整实现。P07 wrong-workspace 两个读入口 404，request/response/advice 三种异域对象赋值均被数据库 FK 拒绝；P08 原件撤回后读取模型记录返回 image_content_revoked；P04 晚到仍无提交。 |
| 0010 additive：保留历史表/对象；商业旧会话 backfill 为 persistent；中断旧在途，不删除历史 | `M/0010_human_assistance.py:16` 仅增列/约束；`:46` 源商业 caseissues/operations backfill；`:48` 保留 human_wait_customer；`:55` 处理中图片转可解释失败；`:58` 修正会话状态；`:62`/`:64`/`:66` 中断任务；`:67` slot fence++；没有 DROP TABLE/DELETE 数据。 | 完整实现。P09/P10 从真实 0009 旧表形状插入旧记录再 upgrade 0010，逐项比较 objects/messages/identities/caseissues/usage，旧正文/图片字节不变。completed review/history 不被重建覆盖。 |
| 隔离 schema 迁移健康、正式服务 feature 声明匹配 | `M/0006_agent_results.py:121`、`M/0007_visual_evidence.py:106`、`M/0008_after_sales_ledger.py:108` 显式 current_schema 目标表存在判断；0010 的反射均显式 schema；`B/adapters/database.py:9` revision=0010；`B/api/system.py:30` simulation_control=false、人协助/模型记录 true。 | 完整实现。每个隔离 fixture 成功迁移 head，P09/P10 验证 0009→0010；0008 operation_commands 不再被可见 public 同名表误判为已有。 |

### 2.2 初查问题与本轮修正证据

以下均为可达场景，不是推测；已修项保留记录，不将初始失败抹成一直通过。

| 级别 | 初查问题/可达业务场景 | 当前修正与新进程复核 |
| --- | --- | --- |
| MEDIUM，已修 | 首轮/后续 Agent 建议写入 human_reviews draft/note，可能把个人回复框变成自动采用的建议。 | `B/application/advice_commit.py:14` 建议/未发送草稿独立保存；`:19` 不写个人字段。P01 验证首次无 staff draft、已有人工 draft/note 原值保留。 |
| MEDIUM，已修 | 商业会话查询库存后，只更新没有匹配活跃 issue 的库存，旧建议可能仍显示有效。 | `B/application/branch_facts.py:60` 对事实变化统一 invalidate/revision++，无自动唤醒。P06 facts_updated、revision 2→3、stale=true。 |
| MEDIUM，已修 | 结案后新来信虽不排 run，却通过 rebuild 把 correspondence 事项重开，隐式改变结案语义。 | `B/application/conversation_base.py:81` closed 不 rebuild。初探针 issue=开放失败；新进程 P03 确认 lifecycle=resolved 且 correspondence=resolved。 |
| MEDIUM，已修 | 0010 中断旧 Agent run，却把关联图片留在 processing、会话留在 running，前台永久等待。 | `M/0010_human_assistance.py:55`/`:58` 补齐图片失败/会话失败。P09 image=failed、conversation=failed、run=interrupted、slot cleared/fence=8，旧对象仍在。 |
| MEDIUM，已修 | 已人工回复的旧商业会话只有 completed review；0010 把 human_wait_customer 改成 human_review 且 claimed=true，却无 open review，处理权/审核状态矛盾。 | `M/0010_human_assistance.py:47`/`:48` 保留该归属，不覆盖 completed 审核。P10 owner=human_wait_customer、claimed=true、open_review=false、waiting_customer；既有 run handed_off 与 understood image 不变。 |

另外，原始履约样例 parcel_purpose=original，而更正接口只接受 original_order。`B/application/branch_fulfillment.py:19` 已兼容两者，仍要求 operation_id=None；这是对原发货数据形状的兼容修正，不授予售后操作写权限。

### 2.3 部分实现、未实现与 Spec 漂移

- 本次后端契约没有发现部分实现/未实现项目。前端运行台、建议采用确认和视觉属于明确排除范围，不能据此宣布 Phase 16 或全产品完成。
- 新 advice GET、新 facts 测试 API、权限/实际记录列均在正式规划授权内，未发现额外商业自动执行范围。证据：`B/api/conversations.py:59`、`B/api/testing.py:9`、`M/0010_human_assistance.py:16`。
- 旧商业 ledger、API 只读历史、未默认注册的旧模拟实现保留，符合历史保留要求；它们的存在不表示新默认工具仍可写交易。证据：`B/main.py:85`、`:86`，`B/agent/tool_schemas.py:85`。

## 3. Stage 2：Code Quality

Stage 1 后端通过后执行本阶段。

| 维度 | 结论与证据 |
| --- | --- |
| 文件职责/大小/类型 | 检查 32 个改动及新增后端 Python 源文件；最大 graph.py 为 269 物理行，均未超 300。权限切换、建议提交与实际记录各有独立小模块：`B/application/human_assistance.py:28`、`B/application/advice_commit.py:10`、`B/observability/model_records.py:11`。工具输入仍由 Pydantic 模型校验，`B/agent/tool_gateway.py:29`。 |
| 错误和副作用边界 | 网络 attempt 失败留记录，提交经过 guarded；晚到 usage/response 只诊断。图片分析失败同时清空 processing_run_id，避免残留在途标记。证据：`B/agent/graph.py:66`、`:71`，`B/observability/model_records.py:22`，`B/agent/budget.py:82`，`B/worker/agent_runner.py:151`；P04、永久 timeout 与最新 vision 故障测试通过。 |
| 安全扫描 | 对上述 32 个源文件扫描 eval、危险 HTML、前端密钥前缀、硬编码 password/API key 特征，rg 退出 1，即无命中。未发现本改造新增字符串用户值拼接 SQL；0010 固定 SQL 无外部输入，`M/0010_human_assistance.py:46`。API scope、工具 scope 与对象 FK 另有实际攻击探针 P07/P08，不能只靠 grep 宣称安全。 |
| 测试真实性 | 网络输出是可控模型替身，但 service、lease、tool gateway、BodyWriter、PostgreSQL约束和迁移均实际执行；`T/test_protocol.py:30` 为每个 fixture 建随机 schema/temp object root，`:46` upgrade head；探针 migration 直接旧形状插入而非用 0010 service 在旧表上制造不可能前提，`P/review_boundary_probe.py:205`。未以跳过用例或空断言证明通过。 |
| PostgreSQL 反射修正 | 使用 current_schema 明确选目标表，再 create(checkfirst=False)，避免 public 同名可见表混淆。`M/0008_after_sales_ledger.py:108`，0010 反射 schema 明确。该模式符合 SQLAlchemy 的 schema/search_path 反射语义，且隔离实际迁移验证成功。[官方 PostgreSQL schema 反射文档](https://docs.sqlalchemy.org/en/21/dialects/postgresql.html)、[官方 Inspector 文档](https://docs.sqlalchemy.org/en/21/core/reflection.html)。 |
| UI/视觉 | 未执行；本任务仅后端，不能声称运行台或邻居页面视觉通过。 |

### 本轮 LOW 维护项闭环

旧 business_wait 死分支：已修。当前位置 `B/application/commit_outcome.py:79`、`:82`、`:87`。

初查时 `business_wait_forbidden` 后仍有不可达商业等待校验/循环/outcome。主 Agent 已删去死分支；当前仅在 `:82–83` 注册普通 customer wait，`:87` 提交普通模拟回复，保留 `:79–81` 对商业等待的防御拒绝。历史数据没有随该清理删除。

独立探针固化：源文件已落地，永久运行结果待主 Agent 汇总。

位置：`P/review_boundary_probe.py:26`、`:180`、`:198`；已对应迁入 `T/test_formal_boundary.py:26`、`:180` 和 `T/test_human_assistance_migration.py:26`。

P01–P08 的个人草稿、结案事项、late response、修订商业意图、事实过期、对象 scope 与图片撤回已编入正式 boundary 文件；P09/P10 的真实旧 shape 升级及 completed 人工审核保留已编入 migration 文件。临时探针独立通过不自动等于永久 suite 已通过；主 Agent 正在复测这些文件，本报告不预先替其签收。

## 4. 探针归档

独立执行入口：`P/review_boundary_probe.py`。以下归档输入、生产路径与关键断言；永久版本已编入上一节列出的两个正式测试文件，最终运行证据待主 Agent 汇总。

| 编号 | 探针位置 | 真实路径/关键断言 |
| --- | --- | --- |
| P01 | `P/review_boundary_probe.py:74` | 商业首轮及人工保存个人草稿后第二轮；Agent 建议不自动变成 staff draft/note，个人正文/备注精确保留。 |
| P02 | `P/review_boundary_probe.py:44` | stopped run 后结案，再重试原 run；ServiceError=retry_not_allowed，不产生新 run。 |
| P03 | `P/review_boundary_probe.py:52` | 真结案后追加来信；lifecycle 与已 resolved correspondence 事项不变、无入队。 |
| P04 | `P/review_boundary_probe.py:90` | 模型 request 回调中实际人工发送；旧 run superseded，晚到 request_state completed 只诊断，artifact=0。 |
| P05 | `P/review_boundary_probe.py:109` | 首轮非商业理解，在真实 revise 工具中转商业；下次决策/终结前 persistent=true、execution_mode=human_assist，handoff。 |
| P06 | `P/review_boundary_probe.py:134` | BASE-OUTON-01 订单明确退款及库存询问，实际 get_item_availability，再写该库存 fact；facts_updated、revision++、旧建议 stale、新库存值正确，无自动出站。 |
| P07 | `P/review_boundary_probe.py:27` | wrong workspace 请求 run/advice 均 404；第二会话异域对象赋给 request_object_id/response_object_id/advice_object_id 三次数据库拒绝。 |
| P08 | `P/review_boundary_probe.py:181` | VisionFixture 真图片执行，记录 image_views 授权引用且无传输 base64；撤回原图后 RunRecords.get 拒绝衍生记录。 |
| P09 | `P/review_boundary_probe.py:199` | 单独随机 schema upgrade 0009，旧在途商业 case/run/job/cycle/slot/image/object/usage，再 upgrade0010；保留旧数据、interrupt、图片 failed、会话 failed、slot fence++、历史 usage not_recorded。 |
| P10 | `P/review_boundary_probe.py:202` | 同样真实 0009，但已有 human_wait_customer + completed review + 人工来信历史，旧 run handed_off、image understood；0010 不重建 open review，不改归属或覆写旧正文/记录。 |

迁移探针反射 vector/probe_vector 时收到 SQLAlchemy 未注册 `public.vector` 类型的 SAWarning。该探针不读写向量列；相关旧记录比较及迁移执行均成功。该警告不是偷偷跳过迁移，也未对正式 schema 做操作。

## 5. 实测与编译原始输出

测试 launcher：`tmp/run-refactor-tests.py`，只从私有配置读取 test DSN；报告没有凭据。fixture 使用随机 PostgreSQL schema 和临时对象目录，销毁仅其自身 schema。没有对正式会话/对象执行测试写入。

末次命令（新 Python 进程）：

```powershell
$env:PYTHONPATH = (Resolve-Path -LiteralPath 'tmp').Path
& 'globalmail-agent/backend/.venv/Scripts/python.exe' 'tmp/run-refactor-tests.py' review_boundary_probe test_human_assistance test_model_records test_model_provider
```

原始汇总与探针输出：

```text
Ran 23 tests in 62.235s

OK
PROBE staff_draft {'draft': 'Staff personal wording', 'note': 'Staff verified note'}
PROBE closed_issues {'lifecycle': 'resolved', 'issue_states': {'correspondence': 'resolved'}}
PROBE late_response {'result': {'error_code': 'lease_expired'}, 'run_status': 'superseded', 'call_status': 'completed', 'artifacts': 0}
PROBE scopes {'foreign_workspace_read': '404', 'foreign_object_updates': '3 FK rejections'}
PROBE inventory_change {'event_status': 'facts_updated', 'before_revision': 2, 'after_revision': 3, 'advice_stale': True, 'new_on_hand': 7}
PROBE revised_intent {'persistent_human': True, 'execution_mode': 'human_assist', 'outcome': 'handoff'}
PROBE image_records {'image_transport': 'authorized_reference', 'revoked_read': 'image_content_revoked'}
PROBE migration_0010 {'persistent_human': True, 'run_status': 'interrupted', 'slot_fence': 8, 'image_status': 'failed', 'conversation_state': 'failed', 'objects_preserved': 2}
PROBE migration_0010 {'persistent_human': True, 'run_status': 'handed_off', 'slot_fence': 8, 'image_status': 'understood', 'conversation_state': 'waiting_customer', 'objects_preserved': 3}
PROBE migrated_staff {'processing_owner': 'human_wait_customer', 'human_claimed': True, 'open_review': False}
SUMMARY 23 failures 0 errors 0 skipped 0
```

独立旧关键路径命令：

```text
tmp/run-refactor-tests.py test_agent_human test_agent_faults test_agent_checkpoint test_vision_graph
Ran 35 tests in 96.752s

OK
SUMMARY 35 failures 0 errors 0 skipped 0
```

两组共 58 项测试通过，互不重复；前者包含 10 个临时探针、7 个 human/model 新永久测试、6 个 provider 测试。两组均在主 Agent 最后一次 waits/commit_outcome/agent_runner 清理后以新进程重新运行。不是全量 suite。较早初查失败的探针在修正后重新运行，不将旧失败输出冒充最终结果。

编译命令：

```powershell
& 'globalmail-agent/backend/.venv/Scripts/python.exe' -m compileall -q 'globalmail-agent/backend/src' 'globalmail-agent/backend/migrations'
Write-Output ('COMPILE_EXIT=' + $LASTEXITCODE)
uv pip check --python 'globalmail-agent/backend/.venv/Scripts/python.exe'
```

原始输出：

```text
COMPILE_EXIT=0
Using Python 3.12.10 environment at: globalmail-agent\backend\.venv
Checked 58 packages in 2ms
All installed packages are compatible
```

独立初审到此结束。主 Agent 仍需完成完整 suite、永久回归运行证据、后续 fresh 独审、前端实际 API/视觉和真实模型业务验收；本报告没有替这些工作签收。
