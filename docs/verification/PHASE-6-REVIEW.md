# Phase 6 独立审查：Stage 1 FAIL

日期：2026-10-08。基线：Phase 5 `d0833a4`；审查当前未提交的 Phase 6 工作区。

**Stage 1：FAIL，HIGH 1 项、MEDIUM 1 项。Stage 2 未执行。不能进入本期 PASS 或正式升级。**

本次因线程数量上限，用户明确批准复用已结束的 code-reviewer 实例；审查者重新完整读取本期原文与相关实现，未沿用 Phase 5 的 PASS 假设，**不是 fresh 实例**。本报告只审查、未修复、未 commit、未 spawn。Phase 5 历史报告不变。

## 规划与完成标准

按 code-review skill 执行；已重新阅读 AGENTS.md、该 SKILL.md、Product-Spec REQ-005/CMP-010/011/012/SCREEN-002/知识 AC/输入状态、AGENT-ARCHITECTURE 第6–8节、DEV-PLAN Phase 6、PHASE-6-IMPLEMENTATION 和 docs/README.md 原文。

| 顺序 | 目标 | 完成标准与本轮结果 |
|---|---|---|
| 1 | 重新建立本期需求矩阵 | 逐项对照，不把 Phase 5 或主 Agent 绿声明当本期证据；完成源码映射 |
| 2 | 核心原文与可达反例 | 检查父块安全前提/范围、profile/cache/manifest、短事务、fence、CAS、修订保旧、下架、过滤和页面命令；发现下述独立复现 HIGH |
| 3 | Stage 2 质量与安全 | 仅 Stage 1 无 HIGH 才执行；本轮依 skill 停止，未给类型/文件大小/安全/视觉 PASS |
| 4 | 独立运行与真实评测 | 原计划等待主 Agent 释放 PG 与浏览器窗口；HIGH 出现时尚未获得窗口，未创建 PG schema、未启动 app、未调用真实供应商 |
| 5 | 失败交接 | 保留本轮 FAIL 与独立证据，只写本报告及 artifacts/phase6/review-*；完成 |

路径缩写：`B = globalmail-agent/backend/src/globalmail_agent`，`F = globalmail-agent/frontend/src`，`T = globalmail-agent/backend/tests`。表内“源码匹配”只表示已定位相应路径，**不等于独立运行通过**。

## HIGH：同 SKU 的明确章节绑定丢失必要安全前提

源要求：Product-Spec.md:355 AC-063 要求切分保留前提/警告/单位及原件位置，关键缺失阻止发布或明确排除；AGENT-ARCHITECTURE.md:325 明确“长文按章节/完整步骤切分，步骤携带必要前提/停止条件”。实施计划步骤1也要求在相同适用范围保留必要前提。

实际位置：`B/knowledge/chunking.py:78–81`。前序警告只有在 `canonical(matching(previous, bindings)) == canonical(applies)` 时才被带入当前操作块；此比较包含 `section_id` 与 `basis`。安全章节与操作章节即使精确绑定同一个 SKU，由于章节名不同，前序必要警告就不会进入操作父块和嵌入输入。

独立复现使用正常受控 JSON `globalmail.knowledge/1`，先通过生产 schema→ParserBlock→Applicability→精确真实 SKU 校验，再调用生产 `chunks`；没有修改任何源代码、没有数据库或供应商调用。

输入：

- `safety` 章节：“Warning: unplug power before performing any following operation. Stop if damaged.”，明确说明后续操作必须断电及损坏停止。
- `operation` 章节：9个完整长步骤，每步350个ASCII正文字符，触发长文结构切分。
- 两章分别绑定真实 `H-CTD16-US-BK`，basis 分别为“A型号共同安全前提”“A型号操作步骤”。没有跨品牌、其他 SKU、排除项或非法结构。

实际输出：3个父块，其中2个操作父块；**2/2操作父块及5/5对应嵌入输入均不含上述警告**。安全父块独立存在，但不是每个操作父块的必要上下文。

`B/knowledge/retrieval.py:110–127` 对同一文档只选一个命中父块，`register_reference` 直接返回该父块正文。若操作父块成为命中父块，返回证据不补安全父块。因此不能用“警告还在另一个父块”认定步骤前提保留。`build_checks.py:33,74` 使用相同切分计划及生成manifest，未因这项必要上下文丢失阻止构建/发布。

[独立可复跑脚本](artifacts/phase6/review-chunking-counterexample.py)及[完整输入/输出](artifacts/phase6/review-chunking-counterexample.json)。本证据证明生产切分函数的可达行为；没有冒称已执行 PG 发布或真实模型检索。

```powershell
# 在 globalmail-agent/backend，数据库及模型均未使用
$env:PYTHONPATH = 'src'
uv run --frozen python ../../docs/verification/artifacts/phase6/review-chunking-counterexample.py
```

原始关键输出，exit=0：

```json
{
  "validated_content": true,
  "validated_bindings": true,
  "parent_count": 3,
  "operation_parents": 2,
  "operation_warning_present": [false, false],
  "operation_embedding_warning_present": [[false, false, false], [false, false]]
}
```

现有 `T/test_knowledge_index_structure.py:46` 的长文测试最初在:50创建 safety/operation 同SKU明确章节绑定，但在:54改成整文 document 绑定后才验证警告携带。这不是当前反例的前提，绿结果不能证明明确章节绑定时安全前提保留。

完成标准：在不扩大到其他 SKU/章节/页范围的前提下，保留操作所依赖的完整安全前提和原件位置；无法确定依赖时明确阻断/要求维护者说明，不能静默输出孤立步骤。补回“同 SKU、独立 safety/operation 绑定”的正反例和真实 PG→HTTP→检索证据；原反例证据与本轮 FAIL 保留。

## MEDIUM：缺少发布状态筛选

源要求：Product-Spec.md:569 SCREEN-002 指定知识管理按资料类型、品牌、SKU、用途和**发布状态**筛选。本期已交付发布/下架，发布状态筛选属于对应页面行为。

实际 `F/views/knowledge/index.vue:61–76` 状态选项只有 `draft/parsing/needs_review/reviewed/failed/cancelled`。`B/knowledge/queries.py:39,47` 的 status 只筛当前内容版本状态。虽然 :36–37 返回 publication/withdrawn，页面 :120 显示“有生效版本/未发布”，仍无法筛“已发布 / 未发布 / 已下架”。例如已发布v1、待核对v2与从未发布的待核对资料都落入同一个内容状态筛选。

完成标准：提供单独发布资格状态筛选，服务端按实际 publication/revocation/withdrawn 查询；保留内容状态筛选的独立含义。验证修订保旧时按真实生效版本筛选，并区分下架与彻底删除。

## Stage 1 源需求逐项对照

REQ-005 行323起18个条目均列出；本轮所有动态证据尚待修复后独立补验，不以其他线程结果替代。

| # | 原文要求 | 本轮实现状态与代码位置 |
|---|---|---|
| 1 | 新白名单/用途；未复核正文不自动入库 | 源码匹配。`B/knowledge/prepared.py:17,30` 固定rag白名单与simulation，`build_checks.py:10` 要求核对；未独立重跑白名单/字节保护 |
| 2 | 五类政策与业务资料；规则不能语义授权 | 政策发布源码匹配，执行仍后续。`build_checks.py:88–97` 重生成并核验policy，`releases.py:65` 同版捆绑；相似分数不触发业务动作 |
| 3 | 来源/品牌/版本/型号/时间、可信度区分、无视频编造 | 源码匹配。`releases.py:57–65` 完整来源资格清单、`retrieval.py:47–56` 来源/用途/时间过滤；不读取视频或宣称已看 |
| 4 | 每品牌代表产品族、七类业务、自编非官方 | prepared数据入口保留，`prepared.py:17,25`；完整七类Agent业务闭环不属本期 |
| 5 | 语义检索、品牌/SKU/资料类型、共享依据 | 已有真实Embedding/PG余弦代码，未独立运行。`embedding.py:57`、`retrieval.py:30,59,104`；章节资格有过滤，但必要安全前提存在 HIGH |
| 6 | 外语检索中文、小型标注集、非分数自动回复 | 实现路径及冻结集存在，实际精度尚未验。`embedding_child.py:11`、`knowledge-eval/query-freeze.json:3` 60旧+12新查询冻结；未跑不能给Recall@5 PASS |
| 7 | 引用ID/标题/版本/片段/适用条件、案例非授权 | 引用字段源码匹配，`references.py:20–33`；没有Agent授权。本轮未实跑引用登记/撤销 |
| 8 | Mock/真实隔离、历史截点 | `retrieval.py:31` 无合法历史清单返回scope_unavailable，:48–50 限simulation/rag/时间；本轮未给完整历史评测验收 |
| 9 | 管理入口、向量后台生成、不要求SQL | 构建/发布/切换/试查入口存在。`ReleaseActions.vue:164,171`、`ReleaseManager.vue:23,167,190`、`SearchPreview.vue:121`；发布状态筛选存在MEDIUM，实际GUI未执行 |
| 10 | 原件不可变、衍生重建、草稿失败不可检索、显式发布、配置分离 | `build_checks.py:10,33`、`builds.py:20`、`index_worker.py:95` 只到ready；发布另事务。0005不可变trigger:127；本轮未独立PG核验 |
| 11 | 原子切换/失败保旧/回滚/并发晚到 | `releases.py:31,86,112` CAS和新事件；`index_worker.py:22,94` guards。普通revision的fence与revocation分离，`eligible`不把revision误当撤销；动态竞争未独立补验 |
| 12 | 下架/删除区分、停止新用旧引用、彻底清理 | 下架源码存在：`releases.py:130`、`references.py:50`；彻底删除Phase12未实现，运行中正式Agent提交竞争Phase7未实现 |
| 13 | 维护/核对/发布/回滚/删除审计、保存不发布 | `releases.py:73,106,125,147` local_operator/审计，新构建不会自动发布；删除动作未到本期 |
| 14 | 政策规则说明同版、修改再核对、simulation不提升 | `build_checks.py:88`、`releases.py:65`，沿用源锁与同源政策；本轮未独立HTTP政策发布验证 |
| 15 | parser/chunker/profile/维度/完整输入摘要、缓存复用、独立空间 | `index_profiles.py:8,24`、`embedding.py:48`、`index_worker.py:51`；输入+profile cache，replace_all覆盖检查 `releases.py:99`；未独立实跑 |
| 16 | PDF原件/图文/位置，关键图不完整不可发布，不绕编辑源 | `build_checks.py:19,35` 重读原件/真实解析对象，沿用核对排除门；`chunking.py:101` 保存位置；完整PDF前提携带受HIGH影响，当前不能判AC063通过 |
| 17 | 独立精确适用关系/章节，不局部扩整份 | `chunking.py:11,60` 章节/SKU/page按范围分组、`retrieval.py:59` 父块每位置复核；同SKU不同章节必要前提没有带入，HIGH |
| 18 | 模拟政策说明从规则生成、SIM编号 | 生成路径保留 `policy_bundle.py:52`；本期未增加部件创建或自动执行业务动作 |

### 组件、架构、计划与AC

| 要求 | 本轮结论与位置 |
|---|---|
| CMP-010 / CMP-011 / CMP-012 | 原件核对保留，索引/发布/记录/试查有源码；`KnowledgeDetails.vue`接ReleaseActions，`ReleaseManager.vue:92`完整清单、`SearchPreview.vue:88`定位/来源；未做真实视觉/交互验证，发布状态筛选缺失 |
| 5.11/5.12状态及写入输入 | `useKnowledgeIndex.ts:68` frozen body/key、4xx释放命令、未知错误保留；`useKnowledgeSearch.ts:11` 冻结本次条件与旧请求代次；`index_commands.py:14,41` CAS/严格scope/time输入。未知响应/空错态实际GUI待独立验证 |
| 架构6.1/6.2 | `builds.py:23` idempotency、`index_worker.py:67` 外部调用在事务外、`embedding_process.py:27`隔离有界孩子；`jobs.py:124,156`及`index_worker.py:100`晚到guards；未独立PG/子进程复验 |
| 架构6.3 | 发布head先于排序/登记事务锁，`retrieval.py:91`；下架知识slot→head→doc，`releases.py:138`。正式Agent/副作用最终提交Phase7未实现，本轮不提前验收 |
| 架构7.1 / 实施步骤1–3 | 不可变输入/profile/probe/cache/manifest及短事务有实现：0005:127、`build_checks.py:51`、`index_worker.py:34`、`releases.py:68`；结构前提HIGH使步骤1不达标 |
| 架构7.2 / 步骤4 | 过滤先于PG排序、20候选、5文档去重、4500代理tokens代码存在：`retrieval.py:30,104,113,123`；2000父/2500短输入配置来自本期新原文 `index_profiles.py:8`；操作证据必要警告未保留 |
| 架构7.3 | 撤销代次与文档构建fence分开，`releases.py:143`；下架停止旧任务、旧引用明确停用；彻底删除/恢复演练不属本期 |
| 架构8 / migration | 0005 profile/build/cache/releases/refs带scope FK，保留既有0004：0005:104–125，schema:17/37/57/73；实际迁移与旧数据未独立运行 |
| DEV-PLAN Phase6及步骤5 | 未达到四步与独立两阶段门槛；真实Embedding→正式PG/60+12查询/实际GUI尚未独立验收，且存在HIGH。不能引用主Agent早前绿结果覆盖缺陷 |
| AC-013/014/016 | 实现精确过滤路径，历史无合法清单拒绝；实际SKU和外语检索与Recall@5尚未独立验收 |
| AC-015 | 正式Agent回复未实现，本期仅资料来源/内容提示，不关闭最终AC |
| AC-055/056/063 | 原件定位/范围/缺失门禁已有；**AC-063本期切分层FAIL**，操作父块丢必要前提；不能以已有原件解析证据代替切分完整性 |
| AC-057/058 | 草稿/ready/发布分离、失败保旧/同版政策源码路径存在；实际原子发布/回滚/旧版服务需独立验证 |
| AC-059 | 下架/旧索引任务/引用门本期路径存在，独立动态待验；正式Agent运行中回复提交Phase7补验 |
| AC-060 | Phase12彻底删除未实现，不算本期scope creep或提前验收 |
| AC-061/062 | input/profile缓存和完整模型空间切换源码存在，动态复用/失败保旧/回退独立待验 |
| AC-064 | 页面入口存在但筛选MEDIUM；完整维护闭环真实GUI尚未执行，当前不能给本期PASS |

## Stage 2 未执行及证据边界

依据 code-review skill：Stage 1 有 HIGH 问题即停，Stage 2 不执行。本轮未给代码质量/文件大小/TS strict/no any、安全扫描、编译、实际明暗/窄宽邻居视觉或全套测试 PASS。未启动 Playwright session。

主 Agent 提供的后端核心/Embedding/前端37/编译/依赖/真实probe结果不作为本轮独立通过结论。已读现有协议测试，`T/index_helpers.py:20`明确 synthetic unit vectors；它们用于真实PG/HTTP/worker协议而非模型相关性，不应与真实供应商能力混写。

本轮只运行上述生产切分反例；未读取配置秘密、未创建PG schema、未修改正式资料/用户配置、未导入prepared包、未运行模型/邮箱。未以controller/fullstories/evaluation/businessholdout替代知识原件。

修复后从 Stage 1 重新审查，复验原反例，再执行 Stage 2 与独立运行/实际视觉。应保留本报告FAIL，使用新的复审报告记录后续结论。
