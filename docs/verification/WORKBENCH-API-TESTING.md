# 邮件与Agent脚本/API测试

正式页面不提供场景实验室或测试控制。下面入口只操作独立schema和临时对象目录；不向正式18080/15173写测试会话。启动脚本复用本机私有配置，不打印凭据。

从仓库根目录启动：

```powershell
pwsh -File globalmail-agent/scripts/start-workbench-test.ps1
```

默认18186 API、15177前端。启动输出`session`文件路径，复制到后续命令的`<session.json>`。服务器正常退出或创建`tmp/phase16-browser.stop`后，清理本次进程/schema/对象目录。保持启动终端运行；每次启动都是新测试环境。

```powershell
globalmail-agent/backend/.venv/Scripts/python.exe globalmail-agent/scripts/mail-test-api.py --session <session.json> scenarios
globalmail-agent/backend/.venv/Scripts/python.exe globalmail-agent/scripts/mail-test-api.py --session <session.json> create BASE-OUTON-04
globalmail-agent/backend/.venv/Scripts/python.exe globalmail-agent/scripts/mail-test-api.py --session <session.json> show <conversation_id>
globalmail-agent/backend/.venv/Scripts/python.exe globalmail-agent/scripts/mail-test-api.py --session <session.json> incoming <conversation_id> --body-file tmp/customer-mail.txt
globalmail-agent/backend/.venv/Scripts/python.exe globalmail-agent/scripts/mail-test-api.py --session <session.json> replay-next <conversation_id>
globalmail-agent/backend/.venv/Scripts/python.exe globalmail-agent/scripts/mail-test-api.py --session <session.json> facts <branch_id> --json-file tmp/fact.json
```

`incoming`从UTF-8文件读取完整邮件正文，默认先读取当前row_version再提交；发生版本竞争返回错误，重读后重试，不自动覆盖。写命令接受`--key`；来信/历史推进重试原请求时，必须同时复用原来的`--expected-version`和正文，避免自动重读的版本改变请求内容。新建固定版本0，facts沿用JSON内版本。`show`只输出状态、消息角色、运行ID和分支ID，完整邮件/提示词在测试前端及既有只读API查看。

默认后台使用已配置供应商执行真实模型请求，仍只模拟发送邮件；不会接真实Amazon、支付或仓储接口。若只验证API/界面工程，用`-ManualAgent`关闭后台模型执行，运行会保持排队，不能将它当作模型质量通过。自动工程测试使用测试套件里的ScriptedModel；真实模型语义验收另行执行。

`facts`的完整JSON格式见`backend/src/globalmail_agent/domain/business_events.py:BranchFact`，包括conversation_id、expected_version、source_event_id、order_line_id、业务版本和人工来源。入口为`POST /api/v1/testing/branches/{branch_id}/facts`：只更新Mock事实并使旧建议失效，不建立新Agent任务，不退款、不发货。原商业申请/取消/模拟执行HTTP入口已移出默认应用。

重点检验：四类首次来信转持续人工；客服发送后每封客户新信产生内部辅助轮次且无Agent发信；普通咨询保留自主回复；新信/接管/结案使旧结果失效；工具及模型输入输出在运行台来自实际记录。采用建议只复制到个人草稿，发送由客服操作。
