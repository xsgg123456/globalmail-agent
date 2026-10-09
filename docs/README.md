# 项目文档索引

本目录集中保存业务、技术专题、数据准备、验证审查与交接文档。根目录固定保留五个项目文档入口；Phase1原图片质量FAIL保留，Phase2–6已交付各期工程验证，Phase7文本Agent和Phase8图文输入工程已接入，模型质量留完整链路后统一回归。Phase8/9工程四步验证及独立两阶段审查通过，下一期Phase10尚未开始；实际范围以DEV-PLAN和验证报告为准。模块说明和实验结果仍随源码存放，数据原件继续存放于 `data/`。

## 根目录入口

2026-10-09当前推进：用户要求先跑通完整项目，已停止Phase7核验局部优化，Phase8图片及Phase9内部售后申请与模拟执行工程验证通过；下一期Phase10连续跟进、异步事件、多订单与方案变更。模型质量与最终验收延期，原FAIL、拒发与权限门保持。工程验证不等于全部产品验收通过。

| 文档 | 职责 |
|---|---|
| [AGENTS.md](../AGENTS.md) | Agent 工作规则、目录约定与任务路由 |
| [Product-Spec.md](../Product-Spec.md) | 产品范围、需求和验收条件的单一事实来源 |
| [Product-Spec-CHANGELOG.md](../Product-Spec-CHANGELOG.md) | 需求变更及相关文档布局记录 |
| [AGENT-ARCHITECTURE.md](../AGENT-ARCHITECTURE.md) | 主要技术架构、状态、工具、事务及运行契约 |
| [DEV-PLAN.md](../DEV-PLAN.md) | 13个开发阶段、具体文件、依赖及82项AC归属；保留根目录 |

## 专题分类

| 分类 | 文档 | 用途 |
|---|---|---|
| business | [BUSINESS-SCENARIOS.md](business/BUSINESS-SCENARIOS.md) | 七类业务、连续场景及图片专项分支 |
| architecture | [BACKEND-ARCHITECTURE.md](architecture/BACKEND-ARCHITECTURE.md) | 后端总览与取舍；具体运行契约以根目录主架构为准 |
| architecture | [TECH-SELECTION.md](architecture/TECH-SELECTION.md) | 技术选择、依赖版本、已有验证及能力边界 |
| architecture | [KNOWLEDGE-DESIGN.md](architecture/KNOWLEDGE-DESIGN.md) | 知识维护、解析、切分、向量化及版本生命周期 |
| data | [DATA-PREPARATION.md](data/DATA-PREPARATION.md) | 数据盘点和准备清单，保留各批次证据 |
| data | [DATA-CATALOG.md](data/DATA-CATALOG.md) | 三品牌商品、案例和资料候选目录 |
| data | [DATA-BUILD-PLAN.md](data/DATA-BUILD-PLAN.md) | 首批资料制作计划、调整及离线验收记录 |
| verification | [AGENT-ACCEPTANCE.md](verification/AGENT-ACCEPTANCE.md) | 产品验收映射与故障时序设计，区别于已通过测试 |
| verification | [KNOWLEDGE-VALIDATION.md](verification/KNOWLEDGE-VALIDATION.md) | 知识专项实验结果及尚未验证部分 |
| verification | [VISUAL-VALIDATION.md](verification/VISUAL-VALIDATION.md) | Phase 1真实图片实验、关键失败、用量和人工核对边界 |
| verification | [PHASE-2-VALIDATION.md](verification/PHASE-2-VALIDATION.md) | 本机API、PG持久化、前端外壳与启停实测 |
| verification | [PHASE-2-REVIEW-FINAL.md](verification/PHASE-2-REVIEW-FINAL.md) | Phase 2独立两阶段复审与修复验证 |
| verification | [PHASE-2-REVIEW.md](verification/PHASE-2-REVIEW.md) | Phase 2初审原始问题与证据 |
| verification | [PHASE-3-VALIDATION.md](verification/PHASE-3-VALIDATION.md) | 会话/回放/人审/调度协议、隔离PG/SSE和实际GUI验收范围 |
| verification | [PHASE-3-REVIEW-PASS.md](verification/PHASE-3-REVIEW-PASS.md) | Phase 3最终fresh两阶段审查，以文件结论为准 |
| verification | [PHASE-3-REVIEW.md](verification/PHASE-3-REVIEW.md)、[第二轮](verification/PHASE-3-REVIEW-FINAL.md)、[第三轮](verification/PHASE-3-REVIEW-3.md) | 历次发现的原始问题与证据，保留FAIL |
| verification | [PHASE-4-VALIDATION.md](verification/PHASE-4-VALIDATION.md) | 业务账本、精确查询、证据/选择/库存条件、数据库到HTTP反例和实际GUI结果 |
| verification | [PHASE-4-REVIEW-CLOSED.md](verification/PHASE-4-REVIEW-CLOSED.md) | Phase 4最终fresh两阶段PASS、独立测试与82项AC归属及未完成限制 |
| verification | [PHASE-4-REVIEW.md](verification/PHASE-4-REVIEW.md)、[第二轮](verification/PHASE-4-REVIEW-FINAL.md)、[第三轮](verification/PHASE-4-REVIEW-PASS.md) | Phase 4历次FAIL原始证据；第三轮文件名含PASS，正文实际FAIL |
| verification | [PHASE-5-VALIDATION.md](verification/PHASE-5-VALIDATION.md) | 知识原件/版本/适用范围、独立解析、持久任务、人工核对及真实页面/故障实测 |
| verification | [PHASE-5-REVIEW-CLOSED.md](verification/PHASE-5-REVIEW-CLOSED.md) | Phase 5第三轮fresh两阶段PASS、历史问题关闭及实际验证范围 |
| verification | [PHASE-5-REVIEW.md](verification/PHASE-5-REVIEW.md)、[第二轮](verification/PHASE-5-REVIEW-FINAL.md) | 两轮FAIL原始证据：PDF替换/结构化资料修订及队首坏原件阻塞 |
| verification | [PHASE-6-VALIDATION.md](verification/PHASE-6-VALIDATION.md) | 向量构建/发布/回滚/下架、检索实际评测与页面/故障证据 |
| verification | [PHASE-6-REVIEW.md](verification/PHASE-6-REVIEW.md)、[第二轮](verification/PHASE-6-REVIEW-FINAL.md)、[第三轮](verification/PHASE-6-REVIEW-CLOSED.md) | 三轮FAIL原始证据；第三轮文件名含CLOSED，正文实际FAIL |
| verification | [PHASE-6-REVIEW-4.md](verification/PHASE-6-REVIEW-4.md) | 第四轮FAIL：真实清空候选/未知响应重开导致意外发布；与前三轮原证据一起保留 |
| verification | [PHASE-6-REVIEW-5.md](verification/PHASE-6-REVIEW-5.md) | 第五轮Stage 1/2 PASS：真实清空/同请求重试、完整页面流程与明暗宽窄通过；保留KQ-058检索漏项 |
| verification | [AGENT-ARCHITECTURE-REVIEW.md](verification/AGENT-ARCHITECTURE-REVIEW.md) | 原架构设计审查，结论限于报告指定版本 |
| verification | [AGENT-VISUAL-REVIEW.md](verification/AGENT-VISUAL-REVIEW.md) | 客户图片能力增量设计审查 |
| verification | [DOCUMENT-CONSISTENCY-REVIEW.md](verification/DOCUMENT-CONSISTENCY-REVIEW.md) | 本轮文档偏差、修订依据及开发计划覆盖自检 |
| planning | [SESSION-HANDOFF.md](planning/SESSION-HANDOFF.md) | 当前进度、已有产出、未完成项和下一步 |
| planning | [PHASE-3-IMPLEMENTATION.md](planning/PHASE-3-IMPLEMENTATION.md)、[PHASE-3-CONTRACT.md](planning/PHASE-3-CONTRACT.md) | Phase 3实施步骤、表/API及集成细节；主架构仍为契约主入口 |
| planning | [PHASE-4-IMPLEMENTATION.md](planning/PHASE-4-IMPLEMENTATION.md) | Phase 4资料/账本、查询、政策预览和工作台集成步骤及接口 |
| planning | [PHASE-5-IMPLEMENTATION.md](planning/PHASE-5-IMPLEMENTATION.md) | Phase 5原件/版本、解析、核对与知识维护页面；包含受控JSON/JSONL契约 |
| planning | [PHASE-6-IMPLEMENTATION.md](planning/PHASE-6-IMPLEMENTATION.md) | Phase 6切分/向量、发布/回滚/下架、检索与前后端接口及验证步骤 |
| planning | [PHASE-7-IMPLEMENTATION.md](planning/PHASE-7-IMPLEMENTATION.md) | Phase 7文本Agent、预算/检查点/终局与工作台闭环实施及验证标准 |
| planning | [PHASE-8-IMPLEMENTATION.md](planning/PHASE-8-IMPLEMENTATION.md) | 图片接收/消息绑定/联合理解/证据更正/工作台工程闭环，模型质量留统一回归 |
| planning | [PHASE-9-IMPLEMENTATION.md](planning/PHASE-9-IMPLEMENTATION.md) | 内部售后申请、取消与未知对账、独立模拟执行及Agent/页面接入；工程四步验证通过 |
| verification | [PHASE-9-VALIDATION.md](verification/PHASE-9-VALIDATION.md) | 五类售后、真实事务/Graph/控制台与故障回归；352后端/61前端、编译/浏览器/独审及清理证据 |
| verification | [PHASE-9-REVIEW-INITIAL.md](verification/PHASE-9-REVIEW-INITIAL.md) | 初轮fresh Stage1 FAIL/Stage2未执行：政策发布竞争HIGH和质检结果误标MEDIUM，修前证据保留 |
| verification | [PHASE-9-REVIEW-FINAL.md](verification/PHASE-9-REVIEW-FINAL.md) | fresh完整Stage1/2 PASS；独立70/6/61、三值质检真实HTTP及宽窄/邻居页面实证，原FAIL保留 |
| verification | [PHASE-7-PROMPT-ADAPTATION.md](verification/PHASE-7-PROMPT-ADAPTATION.md) | Qwen来源/格式/采样适配、自评与真实回归区别，冻结业务目标不变 |
| verification | [PHASE-7-VALIDATION.md](verification/PHASE-7-VALIDATION.md) | 容量专项92/评测43/独审18项及编译通过；唯一新负控制整体FAIL、两项局部进展，停止本配置付费，模型语义仍HIGH；历史全量及正式保旧证据保持 |
| verification | [PHASE-7-REVIEW-INITIAL.md](verification/PHASE-7-REVIEW-INITIAL.md)、[第二轮](verification/PHASE-7-REVIEW-FINAL.md) | 两轮FAIL原始证据；第二轮文件名含FINAL，正文实际FAIL |
| verification | [PHASE-7-REVIEW-3.md](verification/PHASE-7-REVIEW-3.md) | 经用户授权本次复用实例的第三轮审查；Stage1未过、Stage2未执行，局部优化已停止 |
| verification | [PHASE-8-REVIEW-INITIAL.md](verification/PHASE-8-REVIEW-INITIAL.md)、[第二轮](verification/PHASE-8-REVIEW-FINAL.md) | 两轮原FAIL：控制包/元数据、人工来源、派生读取与预览失败撤销；第二轮文件名FINAL不表示通过 |
| verification | [PHASE-8-REVIEW-CLOSURE.md](verification/PHASE-8-REVIEW-CLOSURE.md) | 第三轮Stage1工程通过/Stage2 FAIL：联合分析撤销接口500与单文件301行，保留修前证据 |
| verification | [PHASE-8-REVIEW-ENGINEERING-FINAL.md](verification/PHASE-8-REVIEW-ENGINEERING-FINAL.md) | 第四轮Stage1工程通过/Stage2 FAIL：共同分析失效后的更正POST返回500；文件名FINAL不表示通过 |
| verification | [PHASE-8-REVIEW-5.md](verification/PHASE-8-REVIEW-5.md) | 第五轮Stage1 FAIL/HIGH、Stage2未执行：旧撤销来源吞掉新危险风险，保留实际失败时序 |
| verification | [PHASE-8-REVIEW-6.md](verification/PHASE-8-REVIEW-6.md) | 第六轮关闭风险HIGH，保留CMP-002缺缩略图的MEDIUM；修前整体仍未闭合 |
| verification | [PHASE-8-REVIEW-7.md](verification/PHASE-8-REVIEW-7.md) | 第七轮fresh Stage1本期工程PASS/Stage2 PASS；独立图片与页面反例关闭剩余工程缺口，模型语义延期 |
| verification | [PHASE-8-VALIDATION.md](verification/PHASE-8-VALIDATION.md) | 图片输入/联合理解/证据更正撤销、真实PG/HTTP/SDK及页面工程验证；AC082模型质量延期 |

## 任务阅读与新增文档

1. 先读根目录工作规则、需求、主架构及已有开发计划，再读当前交接；只按本轮任务加载相关专题。
2. 优先更新已有专题；确需新文档时按上表分类并补充索引。验收方案、实测报告和历史审查应明确各自状态，不改写旧结论。
3. 可选设计规范 `Design-Brief.md` 后续放 `docs/architecture/`；`DEV-PLAN.md` 始终保留根目录。技能中只写文件名时按 AGENTS.md 的定位约定处理。
4. Markdown 链接相对所在文件；正文代码片段中的项目路径默认相对仓库根目录，另有明确运行目录说明时从其说明。搬迁须同步链接和生成脚本输出路径，禁止留下根目录重复副本。

当前图片专项已制作35个合成场景并完成108次最终真实请求，存在关键业务失败，人工标签未确认。未改变业务范围、需求/架构版本或既有历史验证结论。数据盘点/制作记录保留批次时间，项目当前进度以DEV-PLAN及交接顶部为准。
