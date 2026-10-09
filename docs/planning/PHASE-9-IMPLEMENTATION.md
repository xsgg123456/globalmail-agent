# Phase 9 内部售后申请与模拟执行实施步骤

日期：2026-10-09。基线：Phase8提交`6b55d03`。用户明确继续Phase9；沿用先完成功能、完整链路后统一模型质量回归的决定，Phase1/7原FAIL、AC082及82项最终验收保持未通过。消费Product-Spec REQ008/011/012/014、DEV-PLAN Phase9、主架构3.3/5/6、已有Phase4同一业务账本和Phase6不可变知识发布，不接真实支付或ERP。

| 步骤 | 目标 | 完成标准 |
|---|---|---|
| 1 | 扩展同一售后账本及冻结0008迁移 | 保留0001–0007及旧数据；新增补偿和库存占用、命令映射及版本约束；完整scope/FK/整数金额/数量约束，正式库不写测试资料 |
| 2 | 实现已发布政策资格与内部申请 | 同一release规则/说明/适用与来源核验；退款、退货、换货、补件、查件；客户明确选择、准确订单行/份额、实付/币种、地址/适配及仓库条件；未发布不能授权，图片不能变账本事实 |
| 3 | 实现取消、重放与未知对账 | 效果、占用、事件、稳定命令映射和工具凭证同事务；新run/新键/新issue不能重复补偿；未知和失败默认保留占用，明确未执行才释放，成功不可假取消 |
| 4 | 实现独立模拟控制及执行结果 | 只对当前分支有效申请推进；支付回执、退货资料/收件质检、精确规格库存占用和物流分别记录；实际执行时重新核验条件，内部申请不扣ERP库存；状态非法、匹配失败、历史模式明确拒绝 |
| 5 | 接入Agent工具与工作台 | Agent仅检查/申请/查询/取消，不注册控制器；处理权/停止/输入/知识/图片/租约栅栏保持；页面显示真实申请/执行/回执，模拟控制明确确认、加载/错误/空态、跨会话请求隔离与失败保留输入 |
| 6 | 完整工程验证和独立审查 | 真实PG/HTTP/有限Graph序列贯通申请→控制台→查询，FT03–06及图片依据反例；后端全量、前端测试/类型构建、真实浏览器正常及故障操作；fresh两阶段独审通过后本地提交 |

主Agent负责源文档、Agent/工具/Context/最终提交集成、整体回归和审查提交；后端售后领域/应用/迁移可隔离交给fresh worker，前端可另交fresh worker。各worker只编码与自检，不spawn、不commit，不撤销他人修改。单文件≤300行；运行测试用随机私有PG schema和独立对象目录，不升级或重启正式0005库。Phase10连续21条旅程/多事项方案转换、Phase11观测、Phase12完整删除恢复不在本期冒称完成。

## 集成边界

页面沿用会话API公开模式`interactive_simulation`/`historical_replay`，不能误用服务内部`simulation`判断控制台权限。两者测试按实际HTTP DTO执行。完成回复只显示进入等待，具体客户/业务等待由真实wait记录说明。

写入回包丢失时，页面保留原请求及幂等键，提供“核对原请求结果”；即使刷新后原事件不再可选，也能经确认重放原请求并读取已提交结果，不重新生成命令。在核对完成前不发起其他模拟写入；明确409/422拒绝可用当前版本重新提交，跨会话或历史模式不能重试旧请求。

“确认未执行”对账表单必须同时提供原尝试核对回执编号、原因和明确勾选确认，不能只凭一个复选框解除占用。

发货与送达表单提供并校验实际承运商回执编号；发货还须核对已保存的承运商和运单。不能仅填写运单便宣称承运商收件或送达。

质检事件统一显示“记录仓库质检结果”，人工确认框同时显示本次选定的通过/未通过/有争议；事件名称不能预先宣称通过。

收件/质检数量表示实际收件或受检的总数量，表单不能把未通过或有争议时的数量称为合格数量。

售后服务在调用者已经持有的短事务中工作，复用BusinessQueries的同一读模型和当前知识manifest；不另建查询影子账本。规则允许内部申请进入waiting_condition，但只允许政策明确的库存/仓库等待；缺身份、客户选择、地址、兼容、金额/币种或安全例外不能借等待状态绕过授权。执行前复查全部当前条件和原方案，不能用旧decision当永久令牌。

人工控制台事务沿用slot→branch→conversation顺序，在订单行/申请/库存锁之前创建或锁定当前knowledge head，直到效果和命令回执提交才释放。政策publish/rollback与执行必须串行，不能校验旧epoch后在新epoch已发布时继续提交；空head也须可锁定，不能在库存锁后临时补头锁。

工具`check_after_sales_eligibility`接收既有EligibilityRequest字段，追加issue_id、selection_ref（可见客户message_id及逐字quote）、可选address_ref/address_version/affected_unit_ids；返回持久decision_id及条件。`create_after_sales_operation`接收decision_id与同一规范方案/selection_ref，服务复算并按订单行份额复用或拒绝。`cancel_after_sales_operation`接收operation_id、expected_operation_version及客户改选的source引用；无法确认原结果时返回unknown且不释放占用。模型参数不能含scope、成功状态或控制器权限。选择证据按可见已核验fixture/人工依据或当前有源且明确无条件的理解校验，模型单独提供accepted不能授权；图像中的数字不能替代实付、退款回执或库存。

工作台读路由为`GET /api/v1/conversations/{id}/operations`与`GET /api/v1/operations/{operation_id}?conversation_id=...`。列表data含branch_id、branch_generation、operations、executions、shipments、returns及会话版本；记录包含原有外部编号、状态、版本、精确金额/数量、来源、关联和合法可用事件，原始对象路径不暴露。

模拟写路由为`POST /api/v1/simulation/branches/{id}/events`（Idempotency-Key）。command包含conversation_id、expected_version、operation_id、expected_operation_version、event及严格可选字段execution_id、receipt_ref、tracking_number、carrier、reason、quantity、confirmed_not_executed、on_hand。事件包括create_execution/processing/succeeded/failed/unknown/reconciled_not_executed/label_created/shipped/delivered/return_in_transit/received/inspected/inventory_changed，由操作类别及当前真实状态限制。回执成功必须有对应类别证据；数量金额由原申请复核而非自由造数。manual来源及事件ID由服务记录，同键异参拒绝；事件事务更新同一账本及有序UI事件。沿用已交付的wait/wake基础支持关联结果查询，人审或停止门关闭时仅记账/提示；Phase10再扩展完整连续流程与乱序旅程验收。

备用关联路由`POST /api/v1/simulation/branches/{id}/execution-links`只允许现有同分支、订单行、类别和份额相符的真实模拟执行记录，不能用关联造成功或移走另一申请的记录。

退货资料由模拟控制台明确输入并落入同一退件记录：return_address、packing_instructions、postage_responsibility（customer/merchant）、授权reference；商家承担邮费时另需prepaid_label_ref。没有完整资料不能标为退货授权或生成寄回指引；不从未来controller-events偷读结果、不默填虚构仓库地址。前端只展示记录中实际提供的资料，模拟资料不冒称可用于真实物流。

## 验证证据

售后完整流程的独立回复审查使用原有严格OutcomeReview验证及所有来源；请求中将观察的JSON字符串解码为同等完整对象，减少嵌套转义，schema删去重复标题/长度注释但仍由原Pydantic约束检查。审查来源构造兼容原字符串与完整对象；旧流程格式不变，不能跳过独立审查或少喂原文。

Graph按当前有源业务阶段展示售后写工具：未取得准确订单行先保留已有查询菜单；取得行后开放资格检查；当前授权decision后开放对应内部申请。输入压力时缩减无关工具schema、优先保留本步申请与人工终点；保留全部消息和工具结果，不放宽16000输入/6次请求/费用预算，也不把内部申请合并成模拟执行。整条冻结Graph必须实际建立申请并正常提交等待。

未进入已授权申请阶段时，输入压力优先移除可稍后核验的售后检查/取消schema，保留现有精确业务及知识查询；只有完整查询菜单仍超限时才缩到安全终点，不能因新增工具提前丢掉原查询能力。

给Agent的创建结果中，完全相同的单笔operation不同时重复放入operation与operations；重复的plan用plan_field_map引用同一operation字段（action对应kind），conditions用condition_fields与逐行值无损表示，必须能还原全部字段和所有条件。查询/页面列表契约不变，旧审计对象不重写。请求指令压缩重复说明并保留原行为约束。预算边界测试核验当前生产prompt下真实可达输入及完整正文保留，不能只改字符数让断言变绿。

本轮合法内部申请/取消会改变同一业务账本。原成功查询的对象、SHA及结果保持原样；旧business_digest的工具凭证标为stale并在新结果里明确列出失效来源，不能冒充当前草稿事实。新效果的工具结果凭证与账本同事务保存，后续当前查询/写结果提供新digest；最终提交只接受仍有效的来源，外部事件仍递增输入版本并使旧run失效。不得为绕过stale_context改写旧查询的摘要或把全部业务版本检查删除。

当前状态：六步工程交付与四步验证完成，[fresh独立Stage1/2](../verification/PHASE-9-REVIEW-FINAL.md)均PASS，本期HIGH/MEDIUM/LOW均0。后端352项/0skip/303.875秒、前端61项/0skip及类型构建通过；真实退款/退货/补件、原键丢包核对、三值质检及六个政策竞争反例已有证据。正式0005/54表、设置和160原件保持；测试schema/目录/端口已清理，详见[验证记录](../verification/PHASE-9-VALIDATION.md)。新增报告和原始失败证据归docs/verification，含正文/模型请求的临时材料只放Git忽略tmp。付费模型语义质量不在本期追加微调；工程固定响应只证明真实事务、工具和页面行为。
