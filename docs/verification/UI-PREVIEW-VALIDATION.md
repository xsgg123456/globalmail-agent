# 工作台解耦交互预览验证

日期：2026-10-09。范围：用户授权的现有前端假数据预览，独立15175端口。正式Agent观测、真实思考采集、模型质量和82项AC不在本次完成声明中。

## 交付与隔离

- 现有Art Design Pro的主布局、侧栏、顶栏、页签、主题、El组件及原MessageTimeline直接复用；没有额外设计稿或新视觉体系。
- 邮件工作台、Agent运行台、业务数据中心、场景实验室独立页面；知识/状态保留原导航位置，展示预览辅助信息。
- 三个演示客户使用`preview.invalid`邮箱、DEMO订单和演示SKU。输入、思考、工具结果及后续运行均为预览构造，页面持续标记演示。
- Vite `ui-preview`注册专属路由和视图，正式模式的视图glob排除预览模块。内存状态不导入业务API，所有演示写操作不离开浏览器；15175 `/api/v1/health/ready`实测404。正式前端/ready仍HTTP200，正式会话列表经核对envelope/data/items结构后仍0项。

## 当场验证

| 检查 | 证据与结论 |
|---|---|
| 现有前端回归 | 修复后`pnpm test`：64 tests、64 pass、0 fail（2813ms）；`.local-data/runtime/ui-preview-tests.log` |
| 最终源码类型 | 阅读位置修复后`pnpm exec vue-tsc --noEmit`，退出0、无错误输出 |
| 两种完整构建 | 最后冻结源码`pnpm build`：`✓ built in 27.14s`；`pnpm run build:ui-preview`：`✓ built in 18.30s`，均含vue-tsc且退出0。日志分别为`.local-data/runtime/ui-preview-normal-build.log`、`ui-preview-build.log` |
| 原服务与预览 | 15175首页200，15175 API404，15173首页200，18080 ready200；未停止原服务 |
| 桌面与窄屏 | 主浏览器1440×900、800×900、414×896；实测800宽业务页面scrollWidth800，邮件/运行792；414宽邮件/运行406，无文档横向溢出。明/暗主题由原按钮切换，深色业务截图及窄屏邮件截图保存于`tmp/ui-preview/` |
| 独立审查 | 见[预览独审](UI-PREVIEW-REVIEW.md)：Stage1/2 PASS，首次MEDIUM修复复验关闭；独立19个断言及实际UI的人工/结案屏障、去重、重置通过 |

浏览器实际点击验证（无模型调用）：

1. Emma邮件→本轮run→订单工具→工具调用Tab→DEMO-1001业务→原run/order节点→邮件；run/step/order URL正确，草稿`Preview draft retained across pages.`仍在。
2. 理解节点思考Tab显示`enable_thinking=false`；核验节点显示明确标记的构造思考。工具Tab完整展示参数和返回；输入Tab显示messages/system/user/参数/schema。
3. 空人工回复出现“请填写回复正文”；发送文本后新增模拟人工邮件，其他客户邮件保持独立。搜索不存在的客户显示空状态；Olivia可人工接管。
4. 实验室退款推进产生DEMO回执、demo-run-04与第三封演示跟进邮件，按钮随后禁用，重复事件不再次创建。人工回复后等待客户期间推进只登记回执，不创建新运行或跟进邮件（独审独立实测）。
5. 实验室空来信报错；添加非空来信只增加演示客户邮件，明确不生成模型记录。重置确认恢复原三个场景及可推进按钮。
6. 业务的订单/库存/物流/申请回执Tab均可查看各自数据；关联订单可返回客户邮件与正确运行节点。
7. 初审发现同页切客户会被原MessageTimeline的异步滚底覆盖阅读位置；只在预览恢复函数等待子组件滚动结束。独审修后实测Emma scrollTop0→Liam→Emma0，跨页仍0，两个客户草稿独立；原MessageTimeline未改。

本次新文件均小于300行（最大steps.ts 276行）；`git diff --check`通过。页面捕获的warn/error日志为空。报告只证明已列的预览路径；没有验证真实流式输出、思考持久化、真实邮箱或ERP。
