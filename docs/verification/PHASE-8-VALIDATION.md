# Phase 8 图片工程验证

日期：2026-10-09。基线：Phase7本地提交`09a818f`。本期实现图片输入、受控预览、图文联合Understanding、逐图证据、人工更正和即时撤销。最终319项冻结后端全量与55项前端、类型构建及实际页面验证通过，第七轮独立Stage1本期工程PASS/Stage2 PASS，工程四步验证通过，无待修HIGH/MEDIUM工程阻塞。模型质量验收延期，未将82项产品AC勾选为完成。

## 验证范围与方法

依据[实施步骤](../planning/PHASE-8-IMPLEMENTATION.md)、Product-Spec REQ014/AC065–082、主架构4.4及DEV-PLAN Phase8。测试使用真实PostgreSQL私有随机schema、独立对象目录、真实Pillow解码及HTTP，结束自动清理；没有向正式数据库导入测试消息或图片。API/工作台页面使用隔离端口18181/15174，模型响应为明确的有限工程序列。

本期没有付费模型请求，没有更换模型、放宽权限/预算/来源/拒发/人工接管栅栏。固定响应证明实际SDK字节、Graph、事务、来源、版本和页面交互，不证明Qwen识别准确率、危险识别或业务话术质量。

| 验证 | 实际结果与证据 |
|---|---|
| 机器JSON读取修复专项 | 68项、0失败/错误/跳过，156.133秒，source_changed=false。含全部5个附件模块、4个视觉模块、旧知识迁移及Agent工具/理解修订/草稿验证；覆盖全部机器JSON读取改动，早于最后风险去重修复。见[冻结结果](artifacts/phase8/focused-tests-68-before-risk-fix.json)、[原日志](artifacts/phase8/focused-tests-final.txt)。此前37项稳定图片专项另保留[快照](artifacts/phase8/focused-tests-37-before-strict-json.json) |
| 风险去重最终专项 | 16项、0失败/错误/跳过，57.693秒，source_changed=false。新增真实PG/Graph旧图撤销→新图同类危险→人工keep_active→普通来信反例，验证新风险保存及后续0模型/0自动出站；并回归显式人工解决、图像联合撤销、更正和危险HITL。见[冻结结果](artifacts/phase8/risk-tests-final.json)、[原日志](artifacts/phase8/risk-tests-final.txt) |
| 前端单测 | 缩略图及长文件名补丁后最终55项、0失败/跳过，2630.1033ms；[最终原日志](artifacts/phase8/frontend-tests-final.txt)。修前55项保留[原日志](artifacts/phase8/frontend-tests.txt) |
| 前端类型和构建 | 最终`npm run build`内`vue-tsc --noEmit`零错误，Vite构建35.44秒；[最终原日志](artifacts/phase8/frontend-build-final.txt)。修前30.45秒保留[原日志](artifacts/phase8/frontend-build.txt) |
| 后端编译 | 最终`compileall -q`覆盖src/tests/migrations，exit0；[命令结果](artifacts/phase8/backend-compile-final.json) |
| 完整后端回归 | 最终319项、0失败/错误/跳过，787.719秒，source_changed=false；[冻结结果](artifacts/phase8/backend-tests-final.json)、[最终原日志](artifacts/phase8/backend-tests-final.txt)。此前317项677.333秒/source_changed=true另保留[原结果](artifacts/phase8/backend-tests-317-before-final-risk-fix.json)、[原日志](artifacts/phase8/backend-tests-317-before-final-risk-fix.txt)，不能冒称当时冻结源通过。首轮316项旧迁移种子错误保留[原结果](artifacts/phase8/backend-tests-initial.json)和[日志](artifacts/phase8/backend-tests-initial.txt) |
| 页面主链 | 真上传→仅图新会话→真实Graph工程序列→HITL→原图/证据抽屉→人工更正→撤销→仅图追加。更正后有效证据来自人工，撤销后preview/evidence均410，追加不启动新run；[HTTP读回断言](artifacts/phase8/browser-api.json)、[页面](artifacts/phase8/revoked-and-append.png) |
| 页面失败和重试 | 浏览器拦截一次保存503，邮箱/正文/已上传图仍保留，再次点击实际API成功。503是明确的工程故障注入，重试成功不是模型测试；[保留图片截图](artifacts/phase8/send-failed-retains-image.png) |
| 抽屉及邻居视觉 | 主Agent实际检查1280×720与900×900，沿用Element Plus抽屉/表单/危险确认，正文和按钮可滚动操作；[900截图](artifacts/phase8/evidence-drawer-900.png)。第三轮独审另对照现有人审和知识库抽屉 |
| 时间线缩略图 | 真实受控缩略图decoded宽512/显示112，原图仍在详情抽屉；仅缩略图注入503后显示无法预览，详情/证据及真实确认撤销均可用，撤销后DOM图片0、文件名按钮disabled，原图/缩略图/证据实际HTTP410。见[读回断言](artifacts/phase8/timeline-thumbnail-proof.json)、[失败回退](artifacts/phase8/timeline-thumbnail-failed-900.png)、[移除后](artifacts/phase8/timeline-thumbnail-revoked-900.png) |
| 代码范围 | 最终83个变更/新代码文件，最大300行、0超限；[行数与SHA](artifacts/phase8/final-code-audit.json) |
| 正式数据及清理 | 正式仍0005/54表，原列/行/SHA、设置及160原件不变，知识22文档/22版本、构建/发布/缓存0。3个自有测试schema和对象目录已清理，15174/18181关闭；[只读核验](artifacts/phase8/formal-readonly-and-cleanup.json) |

## 行为覆盖

接收与存储：JPEG/PNG/静态WebP按真实字节解码；拒绝伪类型、损坏、动画、路径、超10MiB/20M像素；每封4张/合计20MiB。上传不生成消息、不启动模型，首封前暂存会话隐藏；消息绑定整组原子提交、CID清单不可变，重复键重放一致，跨客户/模式/分支/用途/历史截点拒绝。取消和24小时过期只清未绑定且无依赖对象，不删除已提交图片。

上下文与来源：API接受缺字节元数据并明确missing/unsupported，不能借此创建仅图来信；受控案例包按manifest相对路径和SHA校验后真实入库，历史未来图片不暴露。EXIF方向校正和受限整图视图保留原件，SDK临时构造data字节，Graph/checkpoint只保存受控引用；无跨run默认复用或写共享知识库。提取、可见观察、推测、不确定和风险分层，图片不能冒充客户陈述或账本事实。

预算与控制：图文共用原6模型请求/12工具/120秒活动时间/16k输入/80k累计，网络重试重新授权并计入累计6视图；未知usage保守预留。4图超额重试在第二次网络前拒绝；危险标记直接同事务HITL，不等额外模型。停止、新客户输入、人工接管和撤销期间晚到结果不落有效理解/分析、不出站，并解除processing状态。

更正与撤销：要求人工处理权、row/input/epoch版本；更正留人工依据且不自动恢复。sku/model/error_code/order_number四字段正式Graph反例证明旧顶层facts、同字段候选和旧有效source不继续给decision，原模型结果仅留受控审计。撤销递归禁用图像派生summary/facts/人工note/draft/reply、run和checkpoint读取；多图联合分析撤销A后，B原图仍200，旧共同证据及基于它的更正明确410，失败不推进row/epoch。所有机器JSON读取已查齐使用受控字节门，只有文本展示返回撤销占位文字。

风险持久化：撤销旧危险图片后，其派生风险不再作为有效依据；同类新危险不能被这个旧active行去重吞掉。新图危险仍保存新的风险ID和图片来源。人工普通回复keep_active后，再来一封普通邮件，实际Graph在模型前转人工，0模型/0自动出站；风险只能按原人工决定门解除，不借修复恢复已撤销证据。

## 审查和原失败保留

[第一轮](PHASE-8-REVIEW-INITIAL.md)Stage1 FAIL：控制包字节、missing元数据、人工来源覆盖、派生撤销、失败原因及旧状态卡；[第二轮](PHASE-8-REVIEW-FINAL.md)Stage1 FAIL：顶层自动字段仍有效和预览失败阻断真实撤销；[第三轮](PHASE-8-REVIEW-CLOSURE.md)Stage1工程通过、Stage2 FAIL：联合分析撤销GET返回500和单文件301行；[第四轮](PHASE-8-REVIEW-ENGINEERING-FINAL.md)Stage1工程通过、Stage2 FAIL：合法更正POST同类500；[第五轮](PHASE-8-REVIEW-5.md)Stage1 FAIL/HIGH：旧已撤销风险吞掉新同类危险记录，Stage2未执行。五份原报告及原失败不改写；全部修复由68项JSON读取专项和16项最终风险专项分批验证，第六轮fresh仍从Stage1完整重审。

[第六轮](PHASE-8-REVIEW-6.md)无新增HIGH，独立42项与自写连续危险/人工解除1项均通过；原危险记录HIGH关闭。新增MEDIUM为CMP-002已提交时间线缺缩略图，修前整体仍未闭合。现已补齐最小受控缩略图及失败回退、撤销移除，前端55项/类型构建和实际浏览器验证通过。六份原FAIL/部分未通过报告均保留，不改修前结论。

[第七轮](PHASE-8-REVIEW-7.md)fresh从Stage1完整独立复核：本期工程Stage1 PASS、Stage2 PASS，CMP-002关闭，无待修HIGH/MEDIUM工程阻塞。独立28项（27项生产路径及1项自写EXIF/真实缩略字节/越域/no-store/撤销HTTP反例）通过，后者另有1项干净重跑；前端55项/0skip/2538.1949ms、vue-tsc/Vite28.35秒和compileall通过。审查员自己新建仅图会话，验证512px缩略图渲染112px、原图800px、缩略503回退及真实确认撤销后DOM清除/HTTP410；84个源码/提示词快照无漂移，其中83个代码SHA与主Agent冻结结果一致。原始诊断、截图及SHA已归档于[review7](artifacts/phase8/review7/README.md)，不以固定模型响应宣称语义质量通过。

首轮完整回归错误来自旧升级测试在0003结构上调用当前服务；现按旧消息/事件/job/cycle/run结构准备历史数据，再升级head验证保留，未为了测试放宽图片撤销读取门。新增两图反例初次默认请求JPEG缩略图却断言PNG；保留[失败结果](artifacts/phase8/focused-tests-before-preview-assertion-fix.json)，修为显式`thumbnail=false`原图请求后通过。

## 保留边界和后续

AC082以及Phase1/7原模型质量FAIL、视觉字段/观察/推测/业务分流语义均留完整项目链路后统一回归。危险识别准确率也没有凭固定风险输出宣布通过。Phase9内部售后申请和模拟执行、Phase12完整副本删除/备份恢复仍未实现；本期只证明撤销即时失效，不声称物理删除成功。正式数据结构仍0005，本期0007只在隔离环境迁移验证，未正式升级或重启服务。

本期所有浏览器属于专用测试实例，root与最终reviewer均关闭/delete-data；私有schema、对象目录和临时端口的清理已实测。工程辅助脚本/失败原始记录按文档约定保留于tmp或验证归档，未清掉用户目录.idea或本地反馈队列。

依赖用法已核对官方[Pillow Image](https://pillow.readthedocs.io/en/stable/reference/Image.html)和[Qwen视觉模型](https://help.aliyun.com/zh/model-studio/vision)：本期Pillow12.3.0；实际受限视图按32×32 patch保守估计视觉输入，未依赖被忽略的服务端max_pixels参数。

缩略图沿用官方[Element Plus Image](https://element-plus.org/en-US/component/image.html)的contain、原生lazy加载及placeholder/error槽，未添加绕过受控API的外链或宽松Vue类型声明。
