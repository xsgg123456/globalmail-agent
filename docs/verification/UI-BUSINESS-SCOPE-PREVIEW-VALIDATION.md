# 已对齐业务的前端预览验证

日期：2026-10-09。范围：Product-Spec v1.17和[本轮规划](../planning/UI-PREVIEW-IMPLEMENTATION.md)；只验15175隔离预览。用户允许构造数据，明确不Git提交。

## 交付范围

- 保留Art外壳、邮件时间线和已确认的运行概览/轮次/执行过程/详情视觉；删除业务数据中心和场景实验室路由、页面及关联入口，启动清理旧页签/搜索历史。知识库和系统状态原位置保留。
- 八个客户覆盖七类业务及安全分流，初始13轮运行。Liam退款三次来信、两次人工回复、三轮独立run；Emma从普通排障转补件人工，再到物流追问，共四轮。
- 退款/退货/换货/补件仅只读核查、内部事实/来源/时间/缺口/建议/未发送草稿。客服显式采用、核对并手动发送，后续来信仍由客服主导；库存不预留，退款已处理不等于银行到账。
- 普通问题可有据演示回复；物流未知、缺订单、查询失败及危险迹象交人工。已解决不能通过接管隐式重开；追加来信只登记。
- `/__ui_preview__/events`和PowerShell脚本仅驱动本地Mock，不调用正式业务API/数据库/模型，没有前端测试控件。

## 工程验证

工作目录：`globalmail-agent/frontend`。以下为最新代码的主Agent执行结果。

| 命令 | 结果 | 原始证据 |
|---|---|---|
| `pnpm test` | 82 tests / 82 pass / 0 fail / 0 skip，3043.5014ms | [日志](../../tmp/ui-preview/business-scope-tests.log) |
| `pnpm build` | vue-tsc零错误，Vite构建成功30.51s | [日志](../../tmp/ui-preview/business-scope-production-build.log) |
| `pnpm build:ui-preview` | vue-tsc零错误，Vite构建成功19.37s | [日志](../../tmp/ui-preview/business-scope-preview-build.log) |
| 修改范围ESLint | exit 0 | [日志](../../tmp/ui-preview/business-scope-lint.log) |
| preview源文件行数 | 全部≤300 | PowerShell逐文件计数，无超限项 |
| 正式dist扫描 | 未出现preview路由/控制事件/售后演示标题 | `rg -l`扫描dist/assets/*.js无匹配 |
| Git检查 | diff --check退出0，暂存区为空 | 没有stage/commit/push；已有历史未提交内容保留 |

现有测试中的Vue生命周期提示、构建中的既有Sass废弃提示等保留在原始日志；命令成功不等于零警告。

新增回归覆盖四类首轮及持续人工、人工往来进入后续run、历史快照不可覆写、客户/草稿隔离、业务数据变化仅使建议过期、缺订单和失败可达、危险/结案屏障、已删除页签迁移以及HTTP输入/来源/去重/冲突/重置。控制HTTP测试使用独立临时目录与随机端口，清理前检查目标路径，不触碰正式配置。

## 实际浏览器验证

使用CUA实际页面点击，以下与纯状态测试分别记录。

| 操作 | 实测结果 |
|---|---|
| 初始退款页采用草稿 | 五封往来保持五封，文字进入人工回复框，未自动发信 |
| 已有客服个人草稿 | 出现替换确认；取消保留原文；确认才替换 |
| 替换确认期间脚本追加来信 | 新run改变后，旧确认不覆盖个人草稿；邮件仅增加客户来信 |
| 客服发送 | 仅手动点击后增加模拟人工邮件，清空本客户草稿，显示等待客户及“客服持续主导” |
| 历史第2轮退款工具 | 保留当时“处理中”记录及查询时间；新第4轮提示可见，不把后来“已处理”反填旧轮；按历史URL重入仍定位原节点 |
| 提示词/思考/工具 | system/user分段、完整原始请求JSON可展开；思考摘要标“演示构造”；仅query/search只读工具 |
| 缺订单脚本 | lookupNotFound→内部空事实、明确缺口及人工核对草稿；未生成退款/标签/客户Agent邮件 |
| 英文未知和旧扫描 | `Not delivered; current carrier status unknown`→结构状态未知、转人工；三封邮件中仅一封为初始正常物流Agent回复，没有新的Agent邮件 |
| 人工结案 | 接管、结案、发送均disabled；handler状态反例也拒绝重开 |
| 明暗及响应式 | 实际切换主题，恢复原浅色；DOM实测1440/1280/800/414宽度时文档宽度≤视口；截图检查无页面横向溢出，临时视口最后恢复默认 |

截图：[运行台桌面](../../tmp/ui-preview/business-scope-desktop.jpg)、[提示词/思考](../../tmp/ui-preview/business-scope-agent-thinking.jpg)、[历史定位](../../tmp/ui-preview/business-scope-history-kept.jpg)、[建议抽屉](../../tmp/ui-preview/business-scope-advice.jpg)、[缺订单](../../tmp/ui-preview/business-scope-missing-order.jpg)、[最终英文未知深色](../../tmp/ui-preview/business-scope-english-unknown-dark.jpg)、[最终闭案屏障](../../tmp/ui-preview/business-scope-closed.jpg)、[深色运行台](../../tmp/ui-preview/business-scope-dark.jpg)、[1280](../../tmp/ui-preview/business-scope-1280.jpg)、[800](../../tmp/ui-preview/business-scope-800.jpg)、[414](../../tmp/ui-preview/business-scope-414.jpg)。早期截图用于外观/交互证明，最终未知/闭案截图对应最后修复后的源码。

## 隔离与审查

最终正确健康检查路径为`/api/v1/health/ready`：15173代理与18080直连均HTTP200，database/schema/object_store=ready；15175同路径404。15175控制GET返回200 JSON，15173同路径仅200 SPA HTML、无控制事件JSON，不能把SPA fallback当成接口已注册。见[健康证据](../../tmp/ui-preview/business-scope-ready.json)、[控制隔离与首次路径探测](../../tmp/ui-preview/business-scope-http.json)。第一次误用`/system/ready`返回404保留在后者，不是正式服务故障。

原两轮FAIL保留：[首轮](UI-BUSINESS-SCOPE-PREVIEW-REVIEW-INITIAL.md)、[第二轮](UI-BUSINESS-SCOPE-PREVIEW-REVIEW-2.md)。物流未知误出站、缺订单不可达、英文错误混入旧扫描和闭案接管四项均已修并补反例；最终fresh [独立报告](UI-BUSINESS-SCOPE-PREVIEW-REVIEW.md)Stage 1 PASS、Stage 2 PASS，本轮无未关闭HIGH/MEDIUM。审查中发现的“等待业务”遗留筛选删除后，审查者重新从Stage 1复核并独立重跑82项及实际筛选。

## 查看与脚本

预览入口：`http://127.0.0.1:15175/#/workbench?conversation_id=demo-mail-02`；运行台：`http://127.0.0.1:15175/#/agent-runs?run_id=demo-run-02-03`。交付前重置到八客户/十三轮，测试输入不留在初始样例中。

项目根目录执行：

```powershell
./globalmail-agent/scripts/drive-ui-preview.ps1 -Action incoming -ConversationId demo-mail-02 -Body 'The money has not arrived. Could you check again?'
./globalmail-agent/scripts/drive-ui-preview.ps1 -Action business_update -OrderId DEMO-1004 -PatchJson '{"lookupNotFound":true}'
./globalmail-agent/scripts/drive-ui-preview.ps1 -Action business_update -OrderId DEMO-1007 -PatchJson '{"shipmentState":"in_transit","shipment":"Current carrier scan: in transit"}'
./globalmail-agent/scripts/drive-ui-preview.ps1 -Action reset
```

Mock更新不自动运行；追加来信才生成下一轮。重复请求需复用相同CommandId，同ID不同内容返回409。仅改物流补充字符串而未显式确认shipmentState时状态变未知。开发服务器重启清空命令队列；浏览器刷新重建预置样例并回放当前队列，手动回复/草稿等仅浏览器内存、跨页保留，刷新不持久化。静态build仅可浏览/操作构造样例，不提供开发命令桥。

此验证不等于真实Agent业务质量、真实邮箱/ERP/支付接入、正式后端权限精简或82项产品AC整体通过。后续需先确认此交互再对齐正式后端收敛范围。

最终干净样例截图：[邮件](../../tmp/ui-preview/business-scope-final-mail.jpg)、[三轮运行](../../tmp/ui-preview/business-scope-final-agent.jpg)。浏览器高DPI截图右边缘存在截取误差，完整布局依据实际DOM/视口及独审邻居对照，不把截图称为逐像素一致。
