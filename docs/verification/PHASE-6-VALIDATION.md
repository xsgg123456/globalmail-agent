# Phase 6 验证记录

日期：2026-10-08；基线：Phase5 `d0833a4`。**四步技术验证及独立Stage 1/2审查通过，待用户查看。** 对照[实施计划](../planning/PHASE-6-IMPLEMENTATION.md)、Product-Spec v1.13、主架构第6–8节和DEV-PLAN Phase6。

## 本期行为

人工核对后的不可变内容可构建真实1024维索引，完成后明确发布；构建失败保留原生效版本。完整清单按发布头版本防止并发覆盖；换模型需要整批覆盖，回滚重新核验并生成新记录。检索先核对SKU/品牌/用途/可用时间/撤销资格，再做PG精确余弦，最多20候选、5份父证据、4500代理tokens。下架立即撤销旧构建/引用资格，原件和维护记录仍保留。

界面新增构建/发布/下架、完整发布清单/模型切换、检索试查/引用核验及独立发布状态筛选。未知响应按同一请求内容和幂等键重试；抽屉关闭后保留非默认构建和明确清空的候选选择。短SOP/案例整篇保留，必要安全前提按原块SKU资格连接，不同型号的前提分开，保留每块自身章节/页位置。

## 四步检查

| 检查 | 当场证据 | 当前结果 |
|---|---|---|
| 两阶段独立审查 | [初审](PHASE-6-REVIEW.md)、[第二轮](PHASE-6-REVIEW-FINAL.md)、[第三轮](PHASE-6-REVIEW-CLOSED.md)、[第四轮](PHASE-6-REVIEW-4.md)、[第五轮](PHASE-6-REVIEW-5.md) | 第五轮Stage 1/2 PASS，仅覆盖Phase6；无HIGH，保留KQ-058非阻塞MEDIUM；四轮FAIL原样保留 |
| 测试完整性 | PG→HTTP→真实parser/worker，供应商故障、租约、取消、晚到、模型空间、回滚/下架、缓存、政策同版及既有会话协议 | 最终后端158项284.276s，0失败/错误/跳过；前端40项通过；实际组件清空、丢响应及同请求重试通过 |
| 编译与环境 | `pnpm build`包含`vue-tsc --noEmit`；API/source/scripts/eval `compileall`；`uv pip check` | 前端最终构建28.55s/exit0；Python编译exit0，API32包/parser115包兼容 |
| 实际功能 | 隔离API/Vite/PG页面操作、真实Embedding与72条冻结查询、明暗宽窄及邻居对照 | 知识构建/发布/检索/下架流程通过；正例49/50找全、边界16/16无证据；12种页面组合及抽屉通过 |

前端`pnpm exec tsx --test scripts/*.test.ts`：40项、0失败、0跳过，最终2514.5697ms，见[输出](artifacts/phase6/frontend-tests.txt)、[最终构建](artifacts/phase6/frontend-build.txt)。独立parser结构测试4项通过（0.183s）。`pwsh -File globalmail-agent/scripts/test-local.ps1`：重复初始化保留凭据、端口拒绝、登记进程创建时间与自有进程停止3项通过，见[输出](artifacts/phase6/local-script-tests.txt)。

后端首轮151项出现1个测试夹具错误：旧parser指纹测试的部分job字典缺少本期新增`knowledge_operation`，实际数据库记录已有默认值。已补齐夹具；[原失败](artifacts/phase6/backend-tests-initial.txt)保留，不改写当时结果。安全前提原反例和发布状态筛选由独立审查发现；修复后真实PG定向回归通过，另保留初审完整证据。

最终源码下执行`python -m unittest discover -s tests -v`，启用真实本项目PG但全部写随机schema/私有对象：158项284.276s，0失败、0错误、0跳过，进程exit0并完成fixture cleanup，见[完整输出](artifacts/phase6/backend-tests.txt)。索引合成向量用例用于验证事务/错误门，真实相关性另由72条实际Embedding评测验证；不能互相替代。第四轮独立27项PG94.862s、8项实际Embedding子进程和4项parser检查均有独立原日志，第五轮重新验证实际清空交互与最终源码。

## 真实检索及判断边界

输入只有固定22份simulation/rag资料。正式政策是同源JSON及确定性生成的说明；不把控制器、完整场景、evaluation或业务holdout当知识。未验证图意的阻断块明确排除，本次不证明图意理解。临时夹具核对只为测试，不代表用户资料正式发布批准。

实际使用qwen3.7-text-embedding、北京服务、1024维，文档与查询同profile；每批含固定探针检查模型漂移。生产切分/持久任务/发布/引用与PG精确余弦参与测试，未调用对话模型、Agent、邮箱。协议测试的合成向量只验证事务和错误路径，不计算相关性。

原60条查询及新增12条在运行前冻结字节SHA，见[冻结记录](../../globalmail-agent/knowledge-eval/query-freeze.json)。新查询作者知道资料，属于开发补充集，不能称独立业务留出集或生产精度。

首轮真实评测跑完40条后，旧`historical_eval`模式被SearchCommand拒绝，脚本未记录验证层拒绝而中断；已补用实际HTTP422核验该边界，再按原字节重跑。保留[首轮日志](artifacts/phase6/retrieval-run-initial.txt)与[首轮40条结果](../../globalmail-agent/knowledge-eval/retrieval-progress-initial.json)。这是评测脚本漏处理，不是模型拒答。

旧说明1.0的完整72条运行：原正例29/36、新增正例8/8，多证据3/6查询完整（9/12事实），边界16/16空，缺事实6条全部返回相关资料。原始[结果](../../globalmail-agent/knowledge-eval/retrieval-results-policy-1.0.json)含返回全文，未通过90%目标；不能因命中正确政策文档就算事实齐全。

二轮独立审查确认v1说明实质漏了部分退款明确接受金额/币种，替代SKU也漏客户选择与适配前提。不是全部同义差异。生产生成器升级1.1，在对应章节补齐同源规则条件；旧1.0仍能按原生成器复核，旧bundle/原件/版本不改写，明确拒绝构建并引导创建新版本再核对。旧资料尚无正式发布，不自动创建用户新版本。新版本规则/说明/生成器/摘要一起入清单，新增回归实际验证旧记录未变和新父证据/嵌入输入包含条件。两轮FAIL保留，重审从Stage1开始。

修复中157项全套（264.829s）发现百分比文案没有保留原单位“基点”，已同时显示百分比与基点；同次运行因主Agent中途改生成器，parser指纹门正确拒绝变化。保留[该次原始失败](artifacts/phase6/backend-tests-policy-intermediate.txt)，最终检查冻结代码后整套重跑。

政策修复后的157项全套255.210s通过，见[当时输出](artifacts/phase6/backend-tests-policy-fixed.txt)。随后第三轮独立审查发现后置停止条件遗漏，修复完整原文的资格收集并升切分structure/4。新增后置用例首次把标准化后的id/page写入受控上传输入，被真实接口按422拒绝；已改为合法输入并增加父块/输入/试查非空断言。保留[158项中1个夹具错误的原输出](artifacts/phase6/backend-tests-stop-fixture.txt)，不当最终通过证据；最后对最终代码整套重跑。

缺事实查询返回相关资料不等于能够拒答；本期只测证据检索，未测业务决策、最终回复或模型理解能力。修复后仍用原始冻结查询和原句检查，不引入替代评分规则。

第四轮真实页面检查发现HIGH：通过真实ElSelect清空未发布B，首次整批发布只有A500；请求实际200后丢响应，关闭重开抽屉时B被自动补回，第二请求变成A+B且使用新key，意外发布B。保留[两次实际请求](artifacts/phase6/review-4-unknown-wire.json)与第四轮FAIL，不将40项单测通过当作该交互通过。根因是组件清空值undefined与defaults只识别空字符串不一致；按官方接口显式空值并区分未初始化/已清空，兼容旧内存空值。第五轮从Stage1重读，再次使用真实组件清空/丢响应/关闭重开/严格同body及key/epoch不增长核验；后端检索代码和冻结查询未变，没有重复付费重跑相关性评分。

第五轮该HIGH已由实际组件复验关闭：选较早非默认A500、真实图标清空B，首次服务端POST200后abort响应，再关闭重开抽屉，A500与空B都保留；同按钮重试严格同body/key，两次请求expected_epoch=1、返回epoch=2，均只有A且没有新增发布。见[实际请求与响应](artifacts/phase6/review-5-unknown-wire.json)、[独立对比](artifacts/phase6/review-5-unknown-summary.json)。其余页面流程和Stage 2也已完成，见[第五轮独立审查](PHASE-6-REVIEW-5.md)。

## 实际页面流程

第五轮从空schema/API18187/Web15177创建两份自编simulation/rag Markdown资料，OUTON/H-CTD16-US-BK与OUTONLIFE/F-SJ001-US-BK，不导入准备资料充当页面验收。真实保存、解析、人工核对、后台构建及页面状态均参与。

| 操作 | 实际结果及证据 |
|---|---|
| 较早构建发布与未知响应重试 | A500发布epoch1，A300完成复用1向量；实际清空未发布B后首次提交epoch2，关闭重开同body/key重试仍epoch2/仅A；[对比](artifacts/phase6/review-5-unknown-summary.json) |
| 查询、原件与引用 | 显式B发布epoch3；德语查询A返回精确SKU/完整步骤与停止条件，引用有效、原件实际打开；已发布版本重解析禁用；[检索](artifacts/phase6/review-5-qwen-search-a.png)、[原件](artifacts/phase6/review-5-source-compare.png) |
| 同维模型完整切换 | 只有A的V4构建时缺B提示1份并禁止发布，原epoch3保留；B补齐后epoch4两份整体V4、英语B查询有效；[缺项](artifacts/phase6/review-5-v4-missing-b.png)、[切换](artifacts/phase6/review-5-v4-switch.png)、[试查](artifacts/phase6/review-5-v4-search-b.png) |
| 回滚与新草稿 | 恢复Qwen为新epoch5；A保存v2草稿后v1仍生效且有合格历史构建，不把当前草稿当已发布；[历史候选](artifacts/phase6/review-5-historical-build.png)、[旧版证据](artifacts/phase6/review-5-v2-draft-v1-evidence.png) |
| 下架、旧引用和旧清单 | 另一自有标签页下架A→epoch6仅B；旧ref eligible=false，A查询empty，恢复旧清单实际409且epoch不增；[旧引用](artifacts/phase6/review-5-old-reference-disabled.png)、[拒绝恢复](artifacts/phase6/review-5-old-rollback-rejected.png)、[实际请求](artifacts/phase6/review-5-withdraw-wire.json) |
| 筛选与错误状态 | withdrawn仅A、published仅B、unpublished为空；网络错误保留原问题并清旧证据，恢复重试成功；历史用途明确无合法发布资料；[筛选](artifacts/phase6/review-5-publication-filters.json)、[错误](artifacts/phase6/review-5-search-error.png)、[历史限制](artifacts/phase6/review-5-search-history.png) |

以上证明本期知识维护/发布/检索界面及当前协议，不将两个自编小样本的V4成功推成模型相关性比较或生产业务能力。知识库、工作台、系统状态三页各自明暗×1440/900宽度共12种组合均实际检查，发布/试查/原件抽屉也检查了宽窄与明暗。无横向溢出，组件及视觉继承相邻页面，见[浅色测量](artifacts/phase6/review-5-visual-light.json)、[深色测量](artifacts/phase6/review-5-visual-dark.json)及第五轮像素证据。发布抽屉的首张深色窄屏截图实际为1440，未计入窄屏通过证据；已按真实900宽度重拍并复核。

第五轮另独立跑前端40项（2432.2885ms）、vue-tsc/Vite（27.21s/exit0）、8项真实Embedding子进程协议（1.599s）及4项parser结构测试（0.109s）。第四轮27项真实PG测试（94.862s/0失败/错误/跳过）经[源码版本对比](artifacts/phase6/review-5-source-version.json)确认适用于本轮后端，但没有记作第五轮重跑。66份变更产品源码均不超过300行、TypeScript无any，详见[独立源码检查](artifacts/phase6/review-5-source-scan.json)。

提交前另核对所有变更文件、321个文档本地链接和实际配置秘密值；66份产品源码SHA与第五轮审查时一致，见[最终检查](artifacts/phase6/root-final-check.json)。源码及项目文档的暂存差异检查通过。原始日志/审查执行脚本中的末尾空白原样保留，未为格式检查改写历史证据。

最终policy1.1+structure/4运行完成，72条冻结查询逐条核对原句，独立重算零差异，见[最终结果](../../globalmail-agent/knowledge-eval/retrieval-results.json)与[日志](artifacts/phase6/retrieval-run.txt)：

| 查询分组 | 实测结果 |
|---|---|
| 原开发集单项正例 | 36/36关键依据齐全 |
| 新增单项正例 | 8/8关键依据齐全 |
| 多项问题 | 5/6问题找全，11/12项依据命中 |
| 越界问题 | 16/16无证据；其中旧historical_eval四条由HTTP422拒绝 |
| 缺事实问题 | 6/6返回相关资料；未验证最终拒答 |

单项及多项正例合计49/50问题找全（98%），55/56项关键依据命中（98.21%），达到计划≥90%的开发集目标。KQ-058仍是真漏项：返回了安全SOP，但政策只选到“物流和人工”段，未带回质量问题商家承担退货标签费或30天窗口，不能因为命中政策文档就算齐全。保留单文档只选一个父证据和排序的这一限制，没有扩预算、改标签或将其记作模型拒答。

22份资料全部真实构建并发布到隔离清单，15份解析缓存、27份向量缓存、22个构建。实际返回最多9候选、4父证据、4457代理tokens，满足20/5/4500上限。最终这次构建22次Embedding请求，供应商记录12936 tokens、调用耗时合计65.219s；56条实际查询调用记录4830 tokens，查询耗时中位3.867s、最大6.750s。16条边界没有查询Embedding调用。用量含探针，只统计这次最终运行，不冒充全部历史消费或账单。未测V4相关性优劣。

## 数据隔离、升级与未完成项

首个隔离GUI窗口15174/18181由空库起步，途中出现22份准备资料；审查者暂停写入并保留网络/截图，根Agent核验新资料只在隔离schema，正式43表行摘要、配置与160源文件完全不变，见[当场核对](artifacts/phase6/isolation-check.json)。用户随后明确确认自己点过“导入准备资料”。该窗口不算产品GUI通过；自有服务/schema/对象已清理，改用全新空schema及15176/18186独占重测。没有删除正式导入。真实渲染同时发现共享状态条仍写Phase5，已按实施计划修正为Phase6发布检索、Agent尚未接入，重新跑前端40项和构建。

所有测试使用随机PG schema与私有对象目录，正常结束清理自有进程/schema/对象。正式库尚未安装vector时，隔离schema拥有扩展；PG测试、评测、页面串行执行，避免清理彼此依赖。三个GUI窗口的自有服务/schema/对象均已清理，最后一次见[服务清理](artifacts/phase6/browser-server-review5.txt)；审查浏览器也已关闭，见[浏览器状态](artifacts/phase6/review-5-browser-closed.txt)。正式服务保留给用户查看。

正式本机通过启停脚本升级0004→0005，43总表增至54总表（53业务表加alembic_version）。原42业务表旧列数据、设置以及data/和output/pdf/内160份源文件SHA与迁移前一致；22份资料/22个版本保留，index_builds/knowledge_releases/embedding_cache均为0。正式库没有测试A/B或评测发布记录，见[迁移前基线](artifacts/phase6/formal-before.json)、[迁移后核对](artifacts/phase6/formal-preservation.json)、[启动日志](artifacts/phase6/formal-start.txt)。API18080和页面15173实际HTTP200，runtime为phase6且Agent未接入，见[HTTP检查](artifacts/phase6/formal-http.json)。已有policy1.0资料继续可查看，构建提示需要保存新版本再解析核对；升级没有自动修订或发布用户政策。

可在[正式知识库](http://127.0.0.1:15173/#/knowledge)按“新建或修订 → 解析并核对 → 构建索引 → 确认发布 → 检索试查”查看本期能力。技术验证通过，用户查看状态保留在DEV-PLAN。

Phase5被自动批准策略阻止删除的旧临时目录保留，未改用其他工具绕过。本期测试自动清理自己创建的资源。正式Agent、运行中回复提交竞争留Phase7，彻底删除/联合备份留Phase12；82项产品AC未整体验收。Phase7尚未开始。
