# 本轮修后再次发现的 Stage 1 HIGH（原证据）

本记录保留当前源的实际失败，不随修复覆盖。原测试入口：[target-counterexample-before-fix.py](target-counterexample-before-fix.py)；原输出：[target-tests-output.txt](target-tests-output.txt)；完整被测源 SHA：[target-tests.json](target-tests.json)。

真实私有 PostgreSQL 测试 1 项，5.637s，1 failure、0 error、0 skip，测试期间 source_changed=false。

有效初始申请为一件 H-CTD16-US-BK 换货，check.authorized=true，已经建立原 OP；原 fixture 的合法 customer_choices 保留。随后实际追加客户来信：`For the same order, please send replacement H-CTD16-US-BK-NEW instead of the old item.` 最新 Understanding 的 replacement/explicit/target_item=H-CTD16-US-BK-NEW 使用实际新消息 UUID 和完整原文，经 validate_sources 校验后持久化。

预期：新目标不能证实与原商品相同，保留原 OP 并拒绝执行/等待澄清。

实际：create_execution 返回 accepted 的执行单，item_id 仍 H-CTD16-US-BK、quantity=1；原 OP 状态 awaiting_execution，version=2。输出含实际业务响应，无固定成功替代。

根因：application/selection_freshness.py:25 先按旧申请目标过滤 relevant；未知新 SKU 被排除后在第30行返回 renewed=None。application/after_sales_selection.py:75 的旧 customer_choices matching 分支继续沿用旧选择；第88行再次过滤旧目标，因此不运行新原文参数校验。现有 test_selection_freshness.current_selection 将 target_item 固定为 None，并清空原选择，因此此前数量/SKU反例未覆盖此生产可达路径。

违反 AGENT-ARCHITECTURE.md:21、29 当前方案执行前核对原文且改选/不明确拒绝，以及 Product-Spec.md:452、457 的替代型号选择须澄清与改变方案先处理原操作。

本问题出现后停止后续 Stage 2；已完成的前端测试/构建和浏览器操作保留为运行事实，不形成当前完整 Stage 2 PASS。
