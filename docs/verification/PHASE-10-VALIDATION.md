# Phase 10 工程验证

2026-10-09；基线6bbc075。本期工程四步验证与独立Stage1/2审查通过，测试环境已清理；待用户查看。模型语义与全项目验收按用户决定留到Phase13；本文不覆盖原Phase1/7/8质量FAIL，不勾产品82项AC。

## 实现及范围

- 0009增量扩展已有CaseIssue、等待、wake、事件及观察run；多订单事项稳定关联，多个等待可独立保存。业务结果经同一锁和任务队列触发；早到/晚到/重复/无关/乱序有真实事务验证，正常等待没有模型轮询。
- 本轮完成提交仅消费上下文实际观察的事件和版本。人工接管、人工回复后待客户、停止需重试及结案保持记录屏障；排队不是消费。
- 方案变化先核对原申请及执行；未知执行不释放赔付。明确未执行取消回执释放一次。原成功发件的纠错尝试独立记录库存，保留同申请和原赔付份额；纠错未执行只释放该次库存，可凭证明重试。
- 人工连续事实接口包含真实订单行、记录人、来源回执、原因和版本；库存必须精确规格与快照，地址须最新可见客户逐字来源并按订单行保存。原包裹、退件资料和质检修订保留历史。新客户消息后，旧申请执行前必须重新理解；相同方案的明确重确认沿用原申请并保存当前来源，撤销、条件或变更金额币种仍阻止旧方案。无数字的“全额退款”也不能将明确USDT等不同/不支持币种绑定为原USD；未知新商品不能被保留的旧选择忽略。
- 连续驱动将控制文件与Agent输入隔离，调用实际会话、业务和Graph服务，未知gate/缺前提默认阻塞；文本checkpoint需要人工证据。运行报告及持久cursor支持实际run时间字段，不用预期结果冒充运行。
- 工作台继承既有Element Plus/Art Design Pro，展示事项、方案、等待、事件版本及消费run；连续事实与更正、取消回执、纠错执行均为独立人工模拟操作。丢响应沿用原幂等键及参数核对。

## 当前证据

| 验证 | 结果与证据 |
|---|---|
| 主线程后端全量 | `uv run --frozen --project globalmail-agent/backend python tmp/phase10-tests-parallel.py`：68模块409项/0失败/错误/跳过、364.703秒，4组退出0，source_changed=false；[冻结报告](artifacts/phase10/backend-tests-frozen.json)及4组原输出。旧407项保存在[自然币种修前报告](artifacts/phase10/backend-tests-before-natural-currency.json)，不套当前源码 |
| 前端测试/编译 | 修后重新执行`pnpm test`：64项，0失败/跳过，3034.6458ms；`pnpm build`：vue-tsc零错误、Vite34.02秒；[测试](artifacts/phase10/frontend-tests.txt)、[构建](artifacts/phase10/frontend-build.txt) |
| 编译及文件审计 | 当前compileall退出0；72个变更程序文件最大291行；[审计](artifacts/phase10/code-audit.json)。264个后端文件与全量409及独审75/8的before/after、当前源码逐一相同；[提交前核对](artifacts/phase10/precommit-source-check.json) |
| 独立审查 | [第四轮Stage1 PASS、Stage2 PASS](PHASE-10-REVIEW-4.md)，无待修HIGH/MEDIUM。独审当前75项229.500秒及8个实际交易边界54.625秒均0失败/错误/跳过、source_changed=false：[当前源码绑定](artifacts/phase10/review-four/final-current-source-binding.json)。原三轮及本轮各次FAIL保留；新建实例被thread limit拒绝，用户本次批准复用实例，不称fresh |
| 实际页面 | 库存事实从表单提交HTTP200，实际事件b37e0f9e-2572-4e2c-a61d-9cdf816e0242及对应wake均pending、observed_run_id=null；[API/宽度实测](artifacts/phase10/browser-observation.txt)，空表单拒绝请求。[真实主题切换后的明色](artifacts/phase10/browser-narrow-light.txt)及[暗色](artifacts/phase10/browser-narrow-dark.txt)中事项/事件展开、待消费可见，390/document390；宽屏1440/document1440 |
| 连续输入报告 | [72项逐项报告](artifacts/phase10/scenario-engineering.json)：51环节与21JRN实际初始化，71项实际初始Graph、1项SCN-028原人工屏障没有初始run；首事件gate与294个后续not_run保留；不是21条完整旅程通过 |
| 正式库与原件 | 最终`uv run --frozen --project globalmail-agent/backend python tmp/phase10-formal-cleanup.py`退出0：[只读与清理核对](artifacts/phase10/formal-readonly-and-cleanup.json)。0005/54表列行SHA、设置及160原件相同，没有正式升级；自有浏览器关闭，15174/18181关闭，专属schema及对象目录均不存在 |

## 已知未验及推进边界

源变更期、中间FAIL和原审查输出保留，不覆盖成最终PASS。一条手工focused命令误写不存在的`test_after_sales_fulfillment`，19项中1个ImportError，见[test-invocation-error](artifacts/phase10/test-invocation-error.json)及原输出；不算业务缺陷，也不用于通过声明。当前冻结门为409项；旧407项及独审73/6为自然币种修前结果。独立实际页面观察在最后币种后端修复前，14个前端程序字节与当前相同；新的交易拒绝/合法执行由当前75/8真实PG验证，不声称在旧浏览器执行了新退款反例。

审查报告中的文档SHA记录审查时原文。审查结束后仅回填根入口、交接及本报告的进度/实测结果，未改业务合同、82项AC或已审程序；源码仍与冻结回归和独审manifest逐一相同。

21 JRN的81个文字checkpoint没有自动可判结论；原库存等资料有缺规格/来源字段，系统不会默补。当前21条均awaiting_checkpoint，另51项为31 in_progress、20 blocked；各步、gate原因、实际编号和未运行项均保留。固定两响应转人工只验证运行与隔离，不证明模型能完成退款、补件或整段连续旅程。原51业务语义、图片质量、21旅程到人工结案和82产品AC继续在完整项目Phase13验收。当前不存在全项目或生产准确率通过声明。

正式库保持0005，不启用新迁移；本期只使用随机私有PG schema及独立对象目录。`.idea/`原有文件不编辑、不提交。没有付费模型调用、真实退款/寄件、Git push或外部发布。
