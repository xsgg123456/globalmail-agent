# Phase 3 会话、回放、人审与持久任务实测

日期：2026-10-08。状态：四步技术验证及最终独立两阶段审查通过，待用户查看。

## 本次实际交付

- 可操作工作台：新建模拟会话、同演示邮箱追加客户来信、上传受控历史 JSON、逐封推进、人工接管、保存草稿、完成人工回复、人工结案与新来信重开。
- PostgreSQL 持久身份/消息/事项/来源事实、人审、cycle/run/job、幂等请求和有序 UI 事件；Alembic `0002_conversations_jobs` 与运行 metadata 对齐。
- Agent 单槽及知识独立槽、数据库时钟租约/fence、停止/接管/新输入使旧提交失效；重启或失效租约留下 interrupted，必须显式重试，同一 cycle 新建 attempt。
- SSE 按已提交 seq 补读并发送心跳。GET、刷新与重新订阅不创建任务。人审/人工等待期间内部业务通知只记账，不恢复自动处理；新客户来信才恢复。

自动 runner 仅验证任务协议，结果为 `protocol_verified_model_not_connected`。本次没有调用模型，没有自动 AI 回复，也没有向真实邮箱发信。文本模型在 Phase 7 接入；订单历史快照 Phase 4、知识管线 Phase 5/6、业务等待唤醒 Phase 10、图片 Phase 8、完整删除 Phase 12。本次不把这些后续能力或整项产品 AC 标为通过。

## 四步验证与当场输出

测试均连接本项目本机 PG，但创建随机独立 schema；对象正文放 TemporaryDirectory。测试结束删除 schema/临时对象，没有往用户会话库写测试邮件。浏览器使用隔离 API 18181、页面 15174，不使用正式页面 15173 的数据。

### 1. 独立 Code Review

- [初审](PHASE-3-REVIEW.md)：HIGH，旧草稿保存后刷新会把输入版本错误绑定到最新来信；保留原 FAIL。
- [第二轮复审](PHASE-3-REVIEW-FINAL.md)：旧 HIGH 独立关闭，但发现结案后接管状态、知识槽锁顺序两项 MEDIUM；浏览器随后发现响应式 JSON 导入 HIGH，保留本轮 FAIL。
- [第三轮复审](PHASE-3-REVIEW-3.md)：前四项独立关闭；真实浏览器补测发现首次打开溢出会话静止阅读时新邮件拉到底部，MEDIUM。修复后再次 fresh 审查。
- [最终fresh审查](PHASE-3-REVIEW-PASS.md)：Stage 1 PASS、Stage 2 PASS，五项旧缺陷关闭，无HIGH/MEDIUM；独立34/34（16.593s）、18/18（530.4119ms）、build27.15s及compileall0、metadata=[]、双连接事件顺序和8张实图证据。保留非阻塞LOW任务错误文案字典建议，未扩大本轮修改。

### 2. 测试完整性

运行目录为仓库根，数据库连接串只从本机私有配置读入，不输出：

```powershell
$phase3Settings = Get-Content .local-data/runtime/settings.json -Raw | ConvertFrom-Json
$env:GLOBALMAIL_TEST_DATABASE_URL = $phase3Settings.database_url
$env:PYTHONPATH = (Resolve-Path globalmail-agent/backend/src).Path
& globalmail-agent/backend/.venv/Scripts/python.exe -m unittest discover -s globalmail-agent/backend/tests -v
```

最后滚动修复后的当场结果：`Ran 34 tests in 15.783s / OK`，没有数据库 skip。6 项 API、6 项基础 PG、10 项会话/回放、4 项人审/事件、8 项调度协议。

实际覆盖正常流程和失效路径：邮箱加号/句点不被归并、未验证身份不跨案例合并、同 key 同参重读/异参409、来源消息去重、历史真实前缀、active run 阻止推进、独立人工对照、scope FK 与失败事务文件清理、旧草稿刷新、人审与业务通知不同提交顺序、结案/重开、单槽并发领取、双槽独立租约、过期旧任务、stop/retry 同 cycle、接管/新输入旧提交拒绝和重启队列保留。

知识槽锁序用受控 Event 暂停持槽的真实 completion；`pg_blocking_pids` 确认追加来信确实等待槽锁，第三连接 `Conversation FOR UPDATE NOWAIT` 能成功。放行 completion 后追加来信收到合法版本409，刷新重试成功。此证据证明不存在原先的 slot↔conversation 锁环，不靠随机 sleep 碰竞态。

前端运行目录 `globalmail-agent/frontend`：

```powershell
pnpm exec tsx --test scripts/*.test.ts
```

最后滚动修复后的当场结果：`tests 18 / pass 18 / fail 0 / skipped 0`，532.1888ms。覆盖实际 200/202 envelope、Vue reactive 嵌套导入快照、错误输入、未知网络结果同 key/原 payload 重试、409保留输入、切会话晚到响应、分页/过滤、草稿 review 版本与回复 input 版本、SSE 作用域/顺序/断线/晚到事件、既有状态及页签兼容。

本次不评价 AI 的读材料、业务判断或回复质量。测试只给受控邮件正文、来源/时间及当前可见截点，业务通知为内部记账控制；没有提供模型任务提示，也没有调用供应商。不能据任务协议测试推断模型能力。人工对照只是独立持久记录，不是 AI 输出。

### 3. 编译与依赖

```powershell
& globalmail-agent/backend/.venv/Scripts/python.exe -m compileall -q globalmail-agent/backend/src globalmail-agent/backend/migrations globalmail-agent/backend/tests globalmail-agent/scripts/phase3-test-server.py globalmail-agent/scripts/phase3-network-check.py
uv pip check --python globalmail-agent/backend/.venv/Scripts/python.exe
# globalmail-agent/frontend
pnpm build
```

最后滚动修复后的当场结果：compileall 退出0；`Checked 24 packages / All installed packages are compatible`；`vue-tsc --noEmit && vite build` 退出0、3255 modules、`built in 24.74s`。未升级依赖锁文件。

```powershell
pwsh -File globalmail-agent/scripts/test-local.ps1
```

既有脚本3项仍通过：重复初始化保留凭据、占用端口明确拒绝、登记进程创建时间/JSON往返与停止。

### 4. 真实 HTTP/SSE 与浏览器

隔离服务入口：

```powershell
# 保持上面的 GLOBALMAIL_TEST_DATABASE_URL 私有环境变量
& globalmail-agent/backend/.venv/Scripts/python.exe globalmail-agent/scripts/phase3-test-server.py
# 另一终端，仅向该隔离服务运行
& globalmail-agent/backend/.venv/Scripts/python.exe globalmail-agent/scripts/phase3-network-check.py
# 停止隔离进程，清理随机 schema/对象目录
New-Item -ItemType File -Path tmp/phase3-browser.stop -Force
```

网络脚本当场 `status=passed`、`provider_calls=0`：真实 SSE 用 after_seq/Last-Event-ID 断线补读仍有序且作用域一致；等待实际15秒 heartbeat 和多次 GET 没新增任务；负数游标422、未来游标409；真实 HTTP 历史前缀与独立人工审阅隔离。原始安全结果 `tmp/phase3-network-check.json` 为临时证据，不含客户正文或配置。

浏览器使用 Playwright CLI 的 `phase3` 会话执行以下实际页面流程（不通过 DOM 注入假结果）：

| 操作 | 页面与数据实测 |
|---|---|
| 新建模拟 | 演示邮箱 ui.customer@example.test，主题“遥控器无法控制灯”，首封来信“灯能亮，但遥控器按键没有反应。”；持久任务协议完成，消息只有客户邮件 |
| 接管/新输入/旧草稿 | 草稿“请补充遥控器电池型号，我再核对。”；追加“我已经更换了电池，仍然没有反应”；保存旧草稿、整页刷新、重新选会话，草稿还在，完成按钮仍禁用 |
| 明确核对/人工回复 | 点击“我已核对最新邮件”后才能完成；正文“我已看到更换电池仍无反应，下一步请提供订单号供核对。”；中间显示“模拟人工·本机已发送”，右侧等待客户，没有再发自动邮件 |
| 新客户来信恢复 | “我的演示订单号是 DEMO-2001。”加入后恢复可接管及 agent 资格；共4封真实可见邮件 |
| 人工结案/重开 | 独立确认弹窗后已结案；追加“结案后又出现同样的问题。”重开原会话，共5封邮件，原人工记录保留 |
| 文件导入 | 选择 backend/fixtures/historical-example.json → 校验并导入成功，最初只显示1封客户邮件，未来两封不可见 |
| 历史人审/推进 | 本轮审阅单独保存；加载下一封后只显示3封真实历史邮件，不把人工审阅插入中间；回放已结束仍未人工结案 |
| 主题/窄屏 | 实际顶栏切换明暗，1600×1000三栏、1280×800处理详情drawer；暗色选中邮件和人工表单均实际渲染，页面/body横向宽度不超过视口 |
| 网络故障/重试 | 实际拦截本地人审PATCH连接，页面显示“无法连接本地服务…输入已保留”；草稿不丢，解除拦截后重试成功，捕获两次真实请求的Idempotency-Key相同 |
| 阅读位置 | 修复前首次打开已有溢出邮件且scrollTop=0时外部来信强跳到底525；改按真实DOM距离判断。修复后整页刷新静止阅读：top=0、scrollHeight=939、clientHeight=324，真实HTTP新来信经SSE更新后top仍0。真实滚轮上翻后另一封外部来信仍top=0；用户主动追加则top=1043、height=1327、clientHeight=284，准确滚到末尾 |

真实导入第一次暴露 `structuredClone` 无法复制 Vue Proxy；修复为与 HTTP 一致的 JSON 编码快照并重跑实际导入成功。测试过程中的错误保留，不将失败阶段截图当最终通过证据。

## 视觉证据

继承 Art Design Pro 外壳、主题变量、ElForm/Alert/Button/Dialog/Drawer/Collapse；与既有知识库页面实际打开对比。截图均为真实隔离服务页面，只含安全演示数据：

- [明色三栏](../../output/playwright/phase3-light-wide.png)
- [真实历史前缀及独立审阅](../../output/playwright/phase3-history-light.png)
- [明色窄屏详情抽屉](../../output/playwright/phase3-light-narrow-drawer.png)
- [暗色三栏邮件](../../output/playwright/phase3-dark-wide.png)
- [暗色窄屏人工表单](../../output/playwright/phase3-dark-narrow-drawer.png)
- [暗色未选会话空状态](../../output/playwright/phase3-dark-narrow.png)
- [故障时保留人审输入](../../output/playwright/phase3-network-error.png)
- [知识库明色基准](../../output/playwright/phase3-knowledge-light.png)、[暗色基准](../../output/playwright/phase3-knowledge-dark.png)

1600视口内容区左栏260px、右栏360px，中间占剩余；内容区小于1024px时右栏改drawer，小于640px时列表/邮件纵向布局。截图证明本次桌面和窄面板检查，不声称完整手机端适配已完成。邮件/输入保留换行、纯文本渲染。

## 故障时序归属与剩余边界

| 规划故障时序 | 本次有证据的层 | 仍需后续阶段验证 |
|---|---|---|
| FT-01 旧run→新来信/接管→旧返回 | 真实PG旧任务提交被fence/输入版本/处理权拒绝，新输入归原客户；旧草稿刷新仍须核对 | Phase7真实旧模型返回及正式业务写入 |
| FT-02 human_reply与business_event交换提交顺序 | 两种内部真实事务顺序只记suppressed、重复通知不新建任务；过期表单409，后续新客户恢复 | Phase10业务执行/通知/等待匹配与唤醒 |
| FT-05 已提交业务但checkpoint失败 | cycle/attempt框架与旧提交栅栏已准备；中断/显式retry已测 | 未接业务账本及checkpointer，未执行完整FT-05 |
| FT-07 结果先于wait注册 | domain event持久记账、原事务去重控制入口 | 无完整wait注册/补查，未执行完整FT-07 |
| FT-08 历史A对照→推进B/未来哨兵隔离 | 真实PG/API/GUI前缀与独立人工对照隔离；导入未来事件/答案/路径等额外字段拒绝，group_id不授权身份 | Phase4未来业务快照、Phase6未来资料及Phase7模型对照完整哨兵集 |

另测停止、中断、租约过期、独立知识槽和只读GET不自动retry；没有把这些工程检查误标为FT-08。可控启动失败后恢复在真实PG上验证，未据此声称物理数据库断电/模型在途恢复已完整实测。

CaseIssue 本期为稳定 correspondence 基础事项；邮件原文创建带来源与可见seq的 customer_report/historical_claim，不由自由人工备注授权业务。语义多事项、人工结构化事实修改、订单/库存/政策精确查询尚未接入。受控跨源身份复核入口未开放，浏览器不能把 identity_verified=true 变为授权。

## 收尾

本机正式服务已用stop-local/start-local -SkipInstall升级至0002，保留用户数据。实际ready=200、features.conversations=true、正式会话数0（没有写入测试邮件）；check-runtime的API及前端代理6项均200、非法host/origin拒绝。正式本机页面 http://127.0.0.1:15173/#/workbench，后续从 Phase 4 业务数据与精确查询继续。

最新隔离测试服务经停止文件正常退出0，自动删除schema/对象目录；已核实全部phase3_browser schema清空。更早一次中断留下的旧目录globalmail_phase3_browser_xmq_5lg1只有api.log/web.log；自动审批拒绝删除这两个旧日志，原因仅“blocked by policy”，暂保留在系统临时目录。没有保留测试数据库或客户正文对象；本次不声称这两份日志已删除。
