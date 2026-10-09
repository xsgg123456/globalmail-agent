# Phase 9 售后工程验证

日期：2026-10-09。基线：Phase8工程提交`6b55d03`及获批汇报规则提交`3b4fff0`。本期五类内部申请、取消/未知对账、独立人工模拟执行及工作台已实现；工程四步验证和[fresh独立两阶段审查](PHASE-9-REVIEW-FINAL.md)均通过，Phase9工程完成。原Phase1/7/8模型质量FAIL及82项产品AC保持未完成，不追加付费模型微调。

## 已验证范围

依据[实施步骤](../planning/PHASE-9-IMPLEMENTATION.md)、Product-Spec REQ008/011/012/014和主架构3.3/5/6。后端使用真实PostgreSQL随机私有schema及独立对象目录，HTTP和有限Graph响应实际贯通订单→资格→申请→草稿→独立核验→提交等待；不证明自然语言模型质量，没有付费模型请求、ERP、支付或真实邮件投递。正式库未升级，仍0005。

| 验证 | 证据及当前结果 |
|---|---|
| 初轮完整回归 | 351项883.365秒，1失败/1错误，源码期间改变；[原结果](artifacts/phase9/backend-tests.json)、[原日志](artifacts/phase9/backend-tests-initial.txt)。随后351项890.057秒仍有压力菜单失败，[结果](artifacts/phase9/backend-tests-final.json)、[原日志](artifacts/phase9/backend-tests-before-pressure-fix.txt)。两次均不能作最终源通过证据 |
| 原缺陷修复专项 | 16项0失败/错误/跳过、63.359秒、源码稳定；覆盖未知晚到发货、压力菜单、全Graph及完整来源核验。[原日志](artifacts/phase9/regression-16-before-policy-lock.txt) |
| 政策锁修复前全量 | 60模块351项0失败/错误/跳过、311.375秒、source_changed=false；四个独立进程的真实PG分组共351项。[冻结结果](artifacts/phase9/backend-tests-351-before-policy-lock.json)。独审后发现并发授权缺口，此证据不等于已修当前源通过 |
| 政策锁及售后专项 | 20项0失败/错误/跳过，116.75秒、source_changed=false；含发布必须等待控制台事务提交，以及发布后旧decision不得再支付。[结果](artifacts/phase9/focused-tests-final.json)、[原日志](artifacts/phase9/policy-regression.txt) |
| 最终全量 | 61模块352项、0失败/错误/跳过、303.875秒，4组各88项、退出码均0，source_changed=false；[冻结结果](artifacts/phase9/backend-tests-frozen.json)记录全部模块、实际执行数和before/after SHA，[执行器](artifacts/phase9/backend-frozen-runner.py)及4组原日志保留。[提交前复核](artifacts/phase9/current-source-evidence.json)确认236个后端文件仍与冻结源逐一相同 |
| 前端 | 最后数量标签修正后，新控制台及原页面共61项、0失败/跳过、2662.4437ms；vue-tsc类型校验退出0，Vite构建29.38秒通过。[单测](artifacts/phase9/frontend-tests-final.txt)、[构建](artifacts/phase9/frontend-build-final.txt) |
| 独立审查 | fresh Stage1/2均PASS，本期HIGH/MEDIUM/LOW均0。独立70项/0skip/285.5秒，原source_changed=true保留（手写数量标签和忽略的Vite生成声明变化，后端未变）；另跑6政策竞争反例/0skip/37.547秒、source_changed=false。独立前端61项/0skip/2441.5846ms及类型/Vite26.35秒通过；[报告](PHASE-9-REVIEW-FINAL.md)、[70项结果](artifacts/phase9/reviewer-final-tests.json)、[6项当前源结果](artifacts/phase9/reviewer-final-policy.json)、[实际页面摘要](artifacts/phase9/reviewer-final-browser.json) |
| 编译和文件 | 最后标签修正后compileall覆盖src/tests/migrations退出0；70文件最大288行，无超过300行文件。[编译](artifacts/phase9/backend-compile.json)、[行数/SHA](artifacts/phase9/code-audit.json) |
| 正式数据及清理 | 只读比对：0005/54表旧列/行/SHA一致、设置不变、160原件不变，知识22文档/22版本、构建/发布/缓存0。所有本期浏览器schema、临时对象目录已删除，15174/18181关闭；[只读证据](artifacts/phase9/formal-readonly.json)、[清理后证据](artifacts/phase9/formal-readonly-and-cleanup.json)、[服务退出原日志](artifacts/phase9/browser-server-current.txt) |

## 页面实际操作

在隔离端口15174/18181操作真实工作台，不写正式库。首次发现公开模式`interactive_simulation`误用内部`simulation`导致误判只读，已修正并按真实DTO验证。

回包丢失：浏览器让服务器真实保存后abort一次回包，再刷新并点击“核对原请求结果”。两次请求key、完整payload及原版本相同，仍为1申请/1执行；[恢复页面](artifacts/phase9/lost-response-recovered.png)。补丁前刷新后事件不再允许，原请求无法核对；原故障保留并修复，没有以假成功覆盖。

退款未给实际回执时表单拒绝；填模拟支付回执后真实账本退款5499 minor USD、待退款0。补件缺货时只允许库存更新；人为注入过期操作版本真实HTTP409后输入保留，再以当前版本提交，建立执行单。标签仍为label_created，[标签页面](artifacts/phase9/spare-label-not-shipped.png)；仅给运单的发货请求被422拒绝，[修前证据](artifacts/phase9/browser-before-shipping-receipt-fix.txt)，现表单提供并必填承运商回执，发货→执行成功→送达已实际通过。

退货未给完整地址/包装/授权资料时拒绝。填客户自付模拟资料后建立授权，再输入仓库收件回执与数量1、质检回执与数量1和实际passed，最终执行成功，[退货页面](artifacts/phase9/return-completed.png)。三条流程真实HTTP读回均为succeeded、各1执行，[最终结果](artifacts/phase9/browser-flows-final.json)；[丢回包原键核对结果](artifacts/phase9/browser-retry.json)。业务控制不能用标签替代收件、不能用图像金额覆盖账本。

部分浏览器组合脚本曾因为Escape关闭抽屉、切换会话尚未加载及下拉框关闭动画而超时，属于测试器前提错误；修正脚本后继续实际操作，不能把这些超时当业务授权失败或吞掉真实422。

## 独立审查与边界

fresh初轮发现政策发布并发HIGH和质检确认文案MEDIUM，原反例保留，[政策竞争证据](artifacts/phase9/reviewer-policy-race.json)、[初轮FAIL/Stage2未执行](PHASE-9-REVIEW-INITIAL.md)。HIGH修为控制台事务在订单行/库存之前持KnowledgeReleaseHead锁到提交，新增真实并发回归；质检菜单和确认框按实际结果显示。另一fresh实例已从Stage1完整复核后进入Stage2，均PASS；六个真实政策竞争反例验证创建执行/退款成功/实际发货的两个先后顺序，三值质检均真实UI HTTP200，未通过/有争议时不得成功。[最终独审](PHASE-9-REVIEW-FINAL.md)逐项列出源码位置、真实HTTP、原始日志和实际邻居宽窄页面对比，未用主Agent自检替代。

Phase10的21条连续旅程、多事项切换和乱序全链路、Phase11观测、Phase12完整删除恢复、Phase13统一模型及全部AC验收尚未执行；不能把本期工程通过写成全项目通过。
