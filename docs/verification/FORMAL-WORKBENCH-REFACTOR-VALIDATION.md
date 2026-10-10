# 正式邮件与Agent运行台改造验证

日期：2026-10-09。依据Product-Spec v1.18、主架构当前正式运行契约及[实施规划](../planning/WORKBENCH-REFACTOR-IMPLEMENTATION.md)。范围为Phase14–16的工程实现；不把Mock/ScriptedModel测试视为真实Qwen业务质量或82项AC整体验收。验证期间没有暂存、提交或推送Git；2026-10-10用户随后授权本地提交，验证结论和原失败记录保持不变。

## 交付行为

1. 四类商业售后由源材料识别后进入持久人工：Agent仅查询、内部建议和可选未发送草稿。客服发送后持续主导；下一封来信新增human_assist轮次并包含客服历史。商业申请/取消/模拟执行移出默认HTTP及模型工具菜单，事务提交再次阻止自主发信。
2. 普通咨询、排障、物流继续使用既有有据回复；风险/未知/不确定性保持人工。已结案后来信只登记；接管、发送及重试不允许绕过结案。业务事实变更只更新事实、使旧建议失效，不排队或发送。
3. 正式邮件页保留往来、建议抽屉、个人草稿/备注、接管/人工发送/结案；独立运行台按会话→客户轮次→尝试→节点显示真实账本。完整system/user/tool、工具和响应Schema、实际参数、输出/失败逐次保存；只显示供应商返回的reasoning，历史未采集/未返回明确空态。
4. 采用建议需要确认并二次核对run/输入版本/时效；等待中若客服继续输入则拒绝覆盖。旧个人草稿不自动核对新review，发送/保存入口也拒绝过期。历史轮次与工具节点跨页保留，新来信不抢选中；显式跨会话run链接显示错误，不偷偷换成最新轮。
5. 正式导航仅邮件、Agent运行台、知识、系统状态；无业务中心、实验室或测试UI。脚本/API使用隔离session；操作说明见[测试入口](WORKBENCH-API-TESTING.md)。15175批准预览保留，但正式页面不依赖其fixtures/control。

## 当场工程检查

| 检查 | 实际命令与结果 | 证据 |
|---|---|---|
| 后端全量 | 根目录`globalmail-agent/backend/.venv/Scripts/python.exe tmp/run-refactor-tests.py`；422/422，1173.482s，0 fail/error/skip | [全量日志](artifacts/phase16/backend-full-tests.log) |
| 最末提示词修订回归 | 同启动器指定`test_agent_validation test_agent_validation_budget test_human_assistance`；21/21，81.703s | [追加日志](artifacts/phase16/backend-prompt-regression.log) |
| 前端完整测试 | frontend中`pnpm test`；86/86，3277.9707ms，0 fail/skip | [测试日志](artifacts/phase16/frontend-tests.log) |
| 前端编译构建 | frontend中`pnpm build`含`vue-tsc --noEmit`；退出0，Vite 25.66s | [构建日志](artifacts/phase16/frontend-build.log) |
| 后端编译与依赖 | `python -m compileall -q`源码/迁移/脚本退出0；`uv pip check --python …`，58 packages compatible | 主Agent及fresh独审均当场执行 |
| fresh独立复审 | 新实例从Stage1开始核对8个当前契约及本期AC，再Stage2；Stage1/2 PASS，无未关HIGH/MEDIUM；自有29后端/86前端及CLI守卫独立通过 | [最终审查](FORMAL-WORKBENCH-REFACTOR-REVIEW-FINAL.md) |

全量后端使用真实PG的随机schema、临时对象目录和当前app/Graph；测试替身模拟模型网络响应，来源、版本、事务及权限均走实际实现。迁移测试实际建立旧0009库，覆盖有售后意图/进行中run/处理中图片和已人工发送等非空状态。历史旧应用测试仍可调用旧内部实现来验证数据，不表示默认应用还提供商业写权限。

原失败保留：[后端初审](FORMAL-BACKEND-REFACTOR-REVIEW-INITIAL.md)及[前端初审](FORMAL-FRONTEND-REFACTOR-REVIEW-INITIAL.md)；后者Stage1 FAIL/Stage2未执行。第一次草稿修复仍漏无review前输入、fresh永久用例还揭示发送函数缺入口守卫，均修复后重验。旧全量416项的14失败/12错误反映过时重业务断言和旧迁移fixture未冻结版本，日志留`tmp/refactor-full-tests-3.log`；替换为新权限断言/固定旧schema后全量422项通过。未重写原FAIL为PASS。

## 实际GUI与API

FastAPI18184/Vite15176、独立`phase10_browser_*`schema、独立对象目录，后台模型worker关闭，由工程驱动推进实际Graph的ScriptedModel。不是15175前端假timeline，也没有使用正式库。

退款第一轮保存建议无Agent发信；GUI个人输入跨页保留，取消覆盖保持原文，确认采用只复制，客服接管并手动发送后只有一封simulated_human。追加客户追问产生第二轮human_advice，包含真实客服历史；最终3封邮件（客户/客服/客户）、2run，无Agent邮件。退货、换货、补件各1客户邮件、1内部辅助run、持续人工且无Agent发信。实际最终响应见[API快照](artifacts/phase16/isolated-api-outcomes.json)。

已实测历史run+工具节点从触发邮件返回恢复，触发入口定位第3封客户邮件，新轮不抢历史选择；供应商未返回reasoning明确提示；打开结案确认期间跨会话/页面后拒绝结案，四个测试会话仍open；把另一会话run放入退款深链接显示作用域错误，重新选合法轮恢复。CLI真实启动18186/15177的新隔离环境，列表、创建、show、完整正文追加、同幂等键同消息/run ID及409错误均验证。来信重试需复用原expected-version，不能自动换版本覆盖。

1440×1000及1280×720的scrollWidth分别1440、1280；1280明暗邮件/运行台与知识基准逐张核对继承Art控件、边距和主题。原始观测与边界见[GUI记录](artifacts/phase16/gui-observations.json)。800窄屏保留现有Art移动菜单覆盖层，不计手机精细适配通过。

| 页面 | 证据 |
|---|---|
| 运行台桌面 | [1440完整执行](artifacts/phase16/formal-agent-desktop.png)、[1280明色](artifacts/phase16/formal-agent-1280-light.png)、[1280深色](artifacts/phase16/formal-agent-1280-dark.png) |
| 邮件与内部建议 | [邮件明色](artifacts/phase16/formal-mail-1280-light.png)、[邮件深色](artifacts/phase16/formal-mail-1280-dark.png)、[建议抽屉](artifacts/phase16/formal-advice-1280.png) |
| 邻居与错误 | [知识基准](artifacts/phase16/formal-knowledge-baseline.png)、[运行作用域错误](artifacts/phase16/formal-run-scope-error.png) |

## 正式数据与交付状态

升级前正式库为0009，0邮件会话/0进行中Agent run。完整public自定义格式dump、70对象文件及本机私有配置已备份至`.local-data/backups/before-0010-20261009-233425`；dump目录可读取，所有复制对象SHA256一致。没有执行备份恢复演练，不能称Phase12完成。

2026-10-10收尾：正式增量升级至0010成功；77张旧表非授权变动列摘要、70对象文件及设置全部一致，授权变动列逐项列在[保留核对](artifacts/phase16/formal-preservation.json)。当前正式库0会话/0活动run，非空商业权限/图片中断迁移的证明来自永久隔离迁移测试，不能用正式空库冒充这些场景已实测；[本机迁移状态核对](artifacts/phase16/formal-transition-check.json)明确0计数。dump只校验可读目录及复制对象哈希，未作恢复演练。

`pwsh -File globalmail-agent/scripts/start-local.ps1 -SkipInstall`启动正式API18080/前端15173，直连及前端代理ready均200，database/schema/object_store均ready，runtime phase16、human_assistance/model_call_records=true、simulation_control=false、model_configured=true，见[真实响应](artifacts/phase16/formal-ready.json)。正式邮件和运行台显示真实空会话状态，原知识数据保留；没有向正式库塞样例。[正式邮件](artifacts/phase16/formal-delivery-mail.png)、[正式运行台空态](artifacts/phase16/formal-delivery-agent.png)在1440×1000截取，实读四个导航名称正确、scrollWidth=1440，无编造run/统计。

两套隔离环境通过各自stop文件退出0，进程/schema/对象目录清理日志明确`cleaned`；CLI临时session路径已不存在。[实际清理核对](artifacts/phase16/isolated-cleanup.json)读取PG确认两临时schema不存在、四临时端口停止、CLI对象目录删除。正式服务与15175已批准预览保留运行，临时浏览器标签关闭，视口恢复默认。CLI、Graph联调及自动回归都不能计入正式邮箱/ERP接入。

模型语义质量、七类完整真实Qwen旅程、Langfuse及联合备份恢复仍归后续11–13。当前实际请求与SSE在调用/步骤完成后展示全文，不是供应商逐token流式界面。业务工具仍为有源标识的Mock，发送仍为本机模拟。
