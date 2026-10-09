# Phase 10 第四轮独立审查（用户特许复用实例）

本轮由用户直接授权复用审查实例；不称 fresh。从 Stage 1 重新读取原文并独立核验当前源码，禁止修代码、commit、spawn、付费模型及正式库写入。

## 当前中间结论：Stage 1 FAIL / HIGH 1

本文件是修复后再次重审前的中间记录，完整结论待本活动任务完成。发现新 HIGH 后停止后续 Stage 2；已有前端、浏览器运行事实不构成完整 Stage 2 PASS。

### 当前HIGH：未知明确币种、未写数字的全额退款被自然绑定覆盖成原USD

最新真实PG反例：原订单行SIM-O-BASE-OUTON-04-L1的5499 USD退款已check.authorized=true，原合法customer_choices保留；新实际来信逐字 `Yes, I confirm a full refund in USDT.` 经validate_sources/save_understanding保存。create_execution应拒绝旧USD方案/0执行，实际建立accepted的5499 USD执行/1OP/1execution。

原OP-12c2e7567be54418b1b3391b6a14702e；最新来源8c554fbf-f282-42f2-a2d6-528de08ca779；错误执行EXEC-be6ce3054fb946c986d13cd5d7198c7d。完整有效前提和实际响应见 [原输出](artifacts/phase10/review-four/natural-currency-detail-output.txt) / [源绑定](artifacts/phase10/review-four/natural-currency-detail-tests.json)：1项、7.447s、1 failure、0 error/skip、source_changed=false。

根因：choice_binding.py:15的有限币种枚举没有USDT，无数字时第18行natural full refund仍返回true；after_sales_selection.py:64以其fallback覆盖第63行完整USD币种边界匹配失败。违反AGENT-ARCHITECTURE.md:31的“自然绑定不能覆盖明确不同币种”。choice_binding被测SHA e4ead75d89210b8901c469d29ad37c84ae09151b3e59decdcc59284606c9436f，after_sales_selection SHA 4873887435d252f0dfaa9424b01906284e4ad03911fec1b021a166789c117aa5；[原源码](artifacts/phase10/review-four/choice-binding-before-natural-currency-fix.py)与[反例源码](artifacts/phase10/review-four/natural-currency-counterexample-original.py)保留。

目标关联修后独立73项/224.312s、4边界/20.182s、2生产负正例/9.467s均0fail/error/skip/source_changed=false并绑定当前源；它们不覆盖新自然币种反例。证据名是independent-tests-frozen.json、boundary-tests-frozen.json、target-tests-frozen.json，旧*-final.json属中间SHA。主407项原输出已独立读取、当前源0差异，见final-source-binding.json；不能据此掩盖新反例。

此前Stage2真实明暗宽窄UI、邻居及空表单已完成，但新HIGH发现后不作为最终PASS。自有Chrome页1838731228已关闭、viewport已reset，实际观察见 [UI记录](artifacts/phase10/review-four/ui-before-natural-currency-fix.md)。主服务已清理，修后需从Stage1重新核验。一次无效测试入口及两次其它行正例前提未授权均保存，不计业务FAIL或PASS。

### 此前HIGH记录（未知target已修，原FAIL不覆盖）

源合同：AGENT-ARCHITECTURE.md:21、29；Product-Spec.md:452、457。客户后来明确改变商品参数时，应保留原申请并拒绝旧方案，未知新 SKU 需澄清。

实际真实 PostgreSQL 反例：有效的一件 H-CTD16-US-BK 换货已授权并创建 OP，保留原合法 customer_choices；新实际来信请求同一订单改为 H-CTD16-US-BK-NEW，最新有源 Understanding 的 target_item 也是新 SKU。create_execution 却成功建立旧 H-CTD16-US-BK 的 accepted 执行单。1 项测试 / 5.637s / 1 failure / 0 error / 0 skip，source_changed=false。

根因：application/selection_freshness.py:25 按旧申请 target 过滤 relevant，第30行将未知新 SKU 当成无相关改选；application/after_sales_selection.py:75 的旧 matching 分支第88行又过滤旧 target，因此没有执行最新原文参数校验。

完整反例、实际响应和源绑定见 [HIGH原记录](artifacts/phase10/review-four/stage1-target-finding-before-fix.md)、[原始测试输出](artifacts/phase10/review-four/target-tests-output.txt)、[源 SHA manifest](artifacts/phase10/review-four/target-tests.json)。selection_freshness SHA `da3f6a49b01999e8fba2e650e35f829e197256a551387e8d3f5829f24b75a809`，after_sales_selection SHA `4d92bf2b443f30663ad2c340278dce6cf267fb18ec7545f56abd3ec9225c5544`。

原数量/SKU两个 FAIL 的输出与 `90e72db1...` 源绑定另保留为 [参数修前 manifest](artifacts/phase10/review-four/boundary-tests-before-parameter-fix.json)、[原4项输出](artifacts/phase10/review-four/boundary-tests-output.txt)。不将旧 SHA 的失败覆盖为新 SHA PASS。

## 已运行的证据（不替代当前失败）

- 当前参数修后 70 项重点测试 201.655s / 0 failure/error/skip / source_changed=false：[原始输出](artifacts/phase10/review-four/independent-tests-final-output.txt)。
- 当前参数修后独立4边界 24.023s / 0 failure/error/skip / source_changed=false：[原始输出](artifacts/phase10/review-four/boundary-tests-final-output.txt)。这四项 target_item=None 且旧 choices 清空，不覆盖上述原选择保留+新 target 的路径。
- 前端64项测试PASS、vue-tsc exit0、build exit0/26.46s、backend compileall exit0；[测试输出](artifacts/phase10/review-four/frontend-test-output.txt)、[类型输出](artifacts/phase10/review-four/frontend-typecheck-output.txt)、[构建输出](artifacts/phase10/review-four/frontend-build-output.txt)。
- 实际独立 Chrome 页查看了订单、事项第2版、两个待消费事件、案件及人工卡片，空事实表单出现必填错误；没有提交事实。新 HIGH 发现后关闭独立页并恢复视口，后续完整 Stage 2 未完成。

21 JRN到人工结案、51业务语义、图片质量与82AC保留Phase13，原Phase1/7/8 FAIL保留。本期仅审工程合同，不把 blocked/not_run/固定响应改写成业务PASS。
