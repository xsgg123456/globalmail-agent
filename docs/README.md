# 项目文档索引

本目录集中保存业务、技术专题、数据准备、验证审查与交接文档。根目录固定保留五个项目文档入口，Phase 1本轮探索已结束、保留原失败项；Phase 2运行基础及Phase 3会话/人审已实现，进度以DEV-PLAN和验证报告为准。模块说明和实验结果仍随源码存放，数据原件继续存放于 `data/`。

## 根目录入口

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
| verification | [AGENT-ARCHITECTURE-REVIEW.md](verification/AGENT-ARCHITECTURE-REVIEW.md) | 原架构设计审查，结论限于报告指定版本 |
| verification | [AGENT-VISUAL-REVIEW.md](verification/AGENT-VISUAL-REVIEW.md) | 客户图片能力增量设计审查 |
| verification | [DOCUMENT-CONSISTENCY-REVIEW.md](verification/DOCUMENT-CONSISTENCY-REVIEW.md) | 本轮文档偏差、修订依据及开发计划覆盖自检 |
| planning | [SESSION-HANDOFF.md](planning/SESSION-HANDOFF.md) | 当前进度、已有产出、未完成项和下一步 |
| planning | [PHASE-3-IMPLEMENTATION.md](planning/PHASE-3-IMPLEMENTATION.md)、[PHASE-3-CONTRACT.md](planning/PHASE-3-CONTRACT.md) | Phase 3实施步骤、表/API及集成细节；主架构仍为契约主入口 |

## 任务阅读与新增文档

1. 先读根目录工作规则、需求、主架构及已有开发计划，再读当前交接；只按本轮任务加载相关专题。
2. 优先更新已有专题；确需新文档时按上表分类并补充索引。验收方案、实测报告和历史审查应明确各自状态，不改写旧结论。
3. 可选设计规范 `Design-Brief.md` 后续放 `docs/architecture/`；`DEV-PLAN.md` 始终保留根目录。技能中只写文件名时按 AGENTS.md 的定位约定处理。
4. Markdown 链接相对所在文件；正文代码片段中的项目路径默认相对仓库根目录，另有明确运行目录说明时从其说明。搬迁须同步链接和生成脚本输出路径，禁止留下根目录重复副本。

当前图片专项已制作35个合成场景并完成108次最终真实请求，存在关键业务失败，人工标签未确认。未改变业务范围、需求/架构版本或既有历史验证结论。数据盘点/制作记录保留批次时间，项目当前进度以DEV-PLAN及交接顶部为准。
