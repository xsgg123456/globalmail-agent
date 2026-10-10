# Phase12 工程验收

日期：2026-10-10。基线 b42794e / 0011_observability。范围为删除、模拟分支重置、独立删除日志、联合备份及封闭恢复；模型业务质量及82项AC仍留Phase13。

状态：工程四步验收通过，正式0012已交付，待用户查看。冻结后端500/500、前端101/101、两模式编译、真实功能与fresh两阶段独审通过；一项旧隔离合成数据清理被自动审批拒绝，详见末节。Phase13及历史模型质量FAIL不记完成。

## 交付及证据

| 交付 | 实现与验证范围 |
|---|---|
| 会话、知识、图片彻底删除 | 影响预览与取消；持久请求；撤销停写→清理→核验；失败/共享依赖明确阻断并可重试。仅受管副本纳入，源准备包与其他分支保留 |
| 正文依赖与业务记录 | 原件、图像/解析派生、向量与缓存、工具/模型输出、摘要、检查点、草稿及模拟回复；知识跨作用域来源不视为会话自有产物；保留无正文业务防重账本 |
| 并发及浏览器 | 在途模型/解析/导出持共享写锁，清理取独占锁；对象墓碑防晚到写入。受影响会话ID与水位驱动SSE、跨标签页及GET兜底；草稿/建议/隐藏运行台晚到结果失效；确定404清理而503保留输入 |
| 删除后继续处理 | 旧人审从撤销时即不返回，清理完成后允许新空白人审及新回复。后端真实PG回归与独立浏览器路径分别验证 |
| 观测清理 | 已导出及接受未知的receipt均清理；真实远端删除确认前不能completed。旧两条实际业务trace不动；本期只创建并清除一条专属合成trace |
| 重置 | 仅脚本/API，旧模拟分支终止并释放占用，幂等创建新的独立分支；没有新测试页面 |
| 备份与恢复 | 离线锁定数据库及日志，联合数据库/对象/配置摘要；最新签名删除日志独立于备份。全新目标默认封闭，重放及核验后才开放；同库离线崩溃恢复允许过期遗留任务安全停用 |

操作见[删除、重置与恢复](LIFECYCLE-OPERATIONS.md)。共享PDF自动分离未提供；原数据库完全丢失时缺少第二份水位证明会保守拒绝恢复。备份保存配置摘要，完整独立凭据仍需本机受控保管。

## 验证记录

| 检查 | 当场命令及结果 |
|---|---|
| 后端全量 | 对`unittest discover -s tests`完整发现的500用例按ID分3进程执行：167/167/166全部通过，0错误/失败/跳过；分片640.922s/666.567s/620.453s。发现集合无遗漏/重复，测试前后源码SHA一致；[冻结摘要](artifacts/phase12/backend-final-summary.json)、[日志0](artifacts/phase12/backend-shard-0.log)、[日志1](artifacts/phase12/backend-shard-1.log)、[日志2](artifacts/phase12/backend-shard-2.log) |
| 前端全量 | `pnpm exec tsx --test --test-concurrency=1 scripts/*.test.ts`：101/101通过、0跳过，23373.8849ms；[日志](artifacts/phase12/frontend-tests.log) |
| 正式前端编译 | `pnpm build`：vue-tsc零错误、Vite51.00s，退出0；[日志](artifacts/phase12/frontend-build.log) |
| 隔离预览编译 | `pnpm build:ui-preview`：vue-tsc零错误、Vite34.05s，退出0；[日志](artifacts/phase12/frontend-preview-build.log) |
| 代码与脚本 | `python -m compileall -q src tests migrations`、`git diff --check`退出0；87个变更代码文件均≤300行，6个本机PowerShell脚本AST解析零错误；[文件SHA及检查](artifacts/phase12/quality-checks.json) |

- [早期GUI](PHASE-12-GUI.md)：真实预览/取消无数据库变化、三类删除、共享阻断、实际写锁失败与重试、查询错误及1440/720布局；报告保留其源码版本边界。
- [实际观测探针](artifacts/phase12/observability-actual.json)：独立合成trace导出→远端删除→读回确认，模型调用0；探针早于最终丢失响应重试加固，该边界及后续13项回归已明确记录。
- [浏览器失效后端定向](artifacts/phase12/content-invalidation.log)：5项通过，16.987秒，含真实CleanupRunner自动完成及撤销时即隐藏旧人审。
- [接口与历史迁移回归](artifacts/phase12/regression-contracts.log)：52项通过，226.491秒；另[健康门禁10项](artifacts/phase12/regression-health.log)及[跨进程写锁1项](artifacts/phase12/regression-lock.log)通过。
- 冻结前混合源码的失败全量完整保留于 `artifacts/phase12/before-final-mixed-source/`，其中source_changed=true；不能视为最终验收结果。

## 独立审查闭环

[初审](PHASE-12-REVIEW.md)、[第二轮](PHASE-12-REVIEW-2.md)、[第三轮](PHASE-12-REVIEW-3.md)、[第四轮](PHASE-12-REVIEW-4.md)、[第五轮](PHASE-12-REVIEW-5.md)均保留原FAIL，不回写为PASS。问题依次涉及发布快照/旧备份目标、共享来源归属/重复下架、过期任务恢复、浏览器旧草稿、删除后的再次人工接管入口；修复由后续fresh审查独立验证。

[第六轮fresh独审](PHASE-12-REVIEW-6.md)Stage1/Stage2均PASS，无未关闭HIGH/MEDIUM。独立47项专项及1项慢writer排空通过；新合成图片在真实GUI完成“保存旧草稿→删除→completed→空白人审→保存新文→模拟发送→刷新/GET无旧哨兵”。一项LOW建议为未来将再次接管按钮的浏览器路径固化为常驻自动化；本期真实GUI证据已保留。该报告落盘时全量仍运行，最终全量结果由本报告及冻结摘要补齐，不改写其历史时间边界。

## 正式交付

正式升级前已停本项目服务，私有备份`.local-data/backups/before-0012-20261010-223426`包含有效466645字节PG归档、70对象及配置，ACL仅当前用户/SYSTEM/管理员。`start-local.ps1 -SkipInstall`完成0011→0012及重启；表数78→80，77旧业务表逐旧列/行摘要一致，70对象、22知识/22版本、源包和settings保留。见[数据与源包核验](artifacts/phase12/formal-preservation.json)、[对象及配置核验](artifacts/phase12/formal-object-preservation.json)。

正式15173/18080、代理ready、观测3001、原预览15175及新删除记录GET均200；正式active jobs=0、deletion_requests=0，本期没有正式删除或新模型调用。[交付检查](artifacts/phase12/delivery-cleanup.json)。

最终隔离启动器退出0并清理schema、对象及进程，全部本期浏览器已关闭。早期GUI残留的schema `phase12_browser_ca1031205ca740bc9046e3b824b16c42` 与 `tmp/globalmail_phase12_browser_r0kfaxmr` 清理命令被自动审批拒绝，返回`blocked by policy`；没有执行或绕过。该目录仅合成验收数据，测试18189/15179端口关闭；保留此清理例外，不声称所有临时资源已删除。私有配置、备份、tmp、用户.idea及原signals改动均不纳入本期提交。
