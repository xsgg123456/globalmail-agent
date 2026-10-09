# 新会话交接

文档位置：根目录保留 AGENTS、Product-Spec、变更记录、AGENT-ARCHITECTURE 及已创建的 [DEV-PLAN](../../DEV-PLAN.md)；其余专题由 [文档索引](../README.md) 导航。本文件位于 docs/planning；新任务按 AGENTS 中的目录约定存放产物，不恢复旧根目录副本。

更新：2026-10-09。当前阶段：Phase1原FAIL保留、Phase2–6按各期报告交付，Phase7工程提交09a818f/质量延期；Phase8图片及Phase9内部售后申请与模拟执行工程四步验证、独立两阶段审查均通过，模型质量延期，本地提交以git log为准。下一期Phase10，Phase10–13未开始；82项产品AC未作整体验收。

## 2026-10-09最新用户决定（覆盖下方旧推进门）

用户已确认Phase8工程提交后继续Phase9。Phase8基线6b55d03，另有经用户批准的汇报规则提交3b4fff0。[Phase9实施步骤](PHASE-9-IMPLEMENTATION.md)已交付五类内部售后申请、取消/未知对账、独立模拟执行和工作台。初轮fresh审查的政策发布竞争HIGH与质检误标MEDIUM已修，[原FAIL](../verification/PHASE-9-REVIEW-INITIAL.md)保留；另一fresh实例完整重读后[Stage1/2均PASS](../verification/PHASE-9-REVIEW-FINAL.md)，无HIGH/MEDIUM/LOW。本期工程关闭，不继续付费模型微调。

Phase9冻结后端61模块352项/0fail/error/skip、303.875秒、source_changed=false，236个当前后端文件逐一与测试SHA相同；前端61项/0skip/2662.4437ms、vue-tsc/Vite29.38秒通过，compileall退出0，70个变更文件最大288行。独审另跑70项/0skip/285.5秒（原source_changed=true如实保留：数量标签及忽略的Vite生成声明变化，后端SHA未变）、当前冻结政策六反例/0skip/37.547秒与前端61项/0skip/2441.5846ms、构建26.35秒；三值质检及通过后成功回执均真实UI HTTP200，实际宽窄/人工区/知识页/暗主题已对照。主Agent真实退款、补件、退货和丢回包原键核对已验证，详见[验证记录](../verification/PHASE-9-VALIDATION.md)。正式0005/54表、设置及160原件只读比对不变，测试schema/对象目录已清理，15174/18181已关闭；.idea不纳入编辑或提交。Phase10连续旅程、正式库升级及统一模型质量回归尚未执行。

Phase7已按用户要求本地提交09a818f，原质量FAIL保留；用户明确“现在继续开发Phase8”，本期图片上传/仅图消息/受控预览/图文Understanding/人工字段更正/撤销和工作台已实现。五轮工程审查发现的来源、派生读取、撤销及风险去重缺陷已修；第六轮关闭风险HIGH并新增CMP-002时间线缺缩略图MEDIUM，现已补齐，六份原结论保留。[第七轮fresh](../verification/PHASE-8-REVIEW-7.md)从Stage1完整复核：本期工程Stage1 PASS、Stage2 PASS，无待修HIGH/MEDIUM工程阻塞。最后冻结后端319项/0skip/787.719秒/source_changed=false、前端55项/0skip/2630.1033ms与vue-tsc/Vite35.44秒、compileall通过；独审另跑27项生产路径与1项自写HTTP反例，并干净重跑该自写反例，源码SHA一致。实际缩略图加载/503回退/正常详情及撤销DOM清除/HTTP410已证，详见[验证记录](../verification/PHASE-8-VALIDATION.md)。正式0005/54表、设置及160原件只读比对不变，测试schema/对象目录已清理，15174/18181已关闭。工作目录.idea与本地反馈队列属于用户/环境文件，不纳入Phase8编辑或提交。

用户此前要求“先把Phase7进行一下git提交”已完成；覆盖下方历史“不commit”的推进门，但提交不等于Phase7质量通过。Phase8使用0007隔离schema及临时对象验证，不升级正式0005数据库，不运行付费图片质量回归。原Phase7质量问题仍需统一回归，不因为本期工程审查清零全项目待验项。

用户明确要求停止Phase7反复微调，继续开发，整个项目跑通后再处理模型细节。Phase8/9工程验证已通过，下一期Phase10连续跟进、异步事件、多订单与方案变更；Phase7为工程已实现、业务质量/最终验收延期，原FAIL不改为PASS。保留所有拒发、来源/权限、预算、人审及提交栅栏，不再调用旧控制配置刷结果。Phase1图片质量也保留待统一回归；编译/工程测试/主链路故障继续当期修复。Phase8规划见[实施步骤](PHASE-8-IMPLEMENTATION.md)，不因旧“未开Phase8”或“先全过Phase7”记录停工，不再向用户重复请求已给出的推进许可。

## Phase 7 历史交接（执行次序由最新用户决定覆盖）

- 2026-10-09容量候选本轮已结束，Phase7仍未完成：root92项84.176秒/0skip、最终eval43项0.757秒/当前源稳定、独审18项19.541秒/0skip及compileall0；零HTTP预案074344-66a5c470有75可信SHA、输入15035/15413、38448双控制保守预留。唯一实际negative074740-90d0b3da为1HTTP/6279tokens（3542+2737，含2048推理一次）/49062活动ms/0业务，全文双审FAIL：未来条件遗漏与claim1缺声明商品来源两项有进展，但claim0只引订单号仍认可已查物流、claim2混合事实空证据true，两源引用重写非原文。原机检11true保留，结果另标stopped_on_fulltext_semantic_failure/FAIL gate，实际正例入口0HTTP证实被拦。停止本配置付费；不正例、不接Graph、不新06–09、不全量重复、不Stage2、不正式升级/commit/Phase8/82AC。当前源仍text/5及获准4k/2048/最多60秒，Graph原表示不变；下一步需解决逐事实覆盖与引用产生方式，再完整重冻及独审，不能靠总false或再扩额度刷过。
- 最新正式库只读核验：0005/54表、旧53业务表列/行/SHA与设置/160原件相同，知识22/22、build/release/cache0；formal-before原件不变。正式与隔离15173/18080/15174/18181均未监听，旧隔离浏览器schema/对象不存在；没有正式升级或重启。needs_review且暂存为空。

- 2026-10-09用户“好的那你继续”已授权容量方案，不再待授权。Spec v1.14/架构v1.2/DEV-PLAN同步：仅validation总4k（3990+10）、thinking2048、min(60,剩余活动秒)，其他2k/30及总6/12/120秒/16k/80k保持。text/5工程实施中；先真实PG边界/独审/完整零HTTP，再唯一原负全文双审，PASS才原正、表示接Graph和新06–09。质量仍未通过，旧FAIL、Stage1 HIGH/Stage2未开始保持。

- 当前最新text/4工程全量：后端276项548.623秒/0fail/error/skip/source稳定，独审核179原SHA；旧274原字节归档before-thinking-workflow-contract-274。eval42项0.791秒/0skip/source稳定、compileall通过；前端未改，53项/构建证据仍适用。模型语义仍未过，Stage1 HIGH/Stage2未做；needs_review、不commit、不正式升级、不开始8/不勾82AC。
- 230652 schema对齐与231655无损parsed表示各唯一negative完整双审FAIL，原正控制及新06–09仍零HTTP。后者4892tokens/25780活动ms/1HTTP/0业务，原DATA还原与canonical source正文完全相同，却仍错映未来退款，商品译名主要否决理由也错误；表示prototype未接Graph、该假设停止。当前产品仍validation512/1990/30秒，其他节点非thinking/2k/30秒。
- 具体容量新假设已做好零HTTP完整SDK/预算[提案](../verification/artifacts/phase7/validator-capacity-proposal-zero-http.json)：仅validation4000总输出（3990+10）、thinking2048、min(60, cycle剩余活动秒)，其他及总6/12/120秒/16k/80k保持；双完整原对照预留38448。尚未授权/改产品/新HTTP，需用户允许改ASM-006；获准后先源文档同步与stage reserve/unknown/settle/timeout/晚到门工程自检、原负正全文双门、再同一表示接Graph/新06–09/最终当前源及独审Stage1/2/正式保旧升级。不得把预算假设当已证质量改善。

- 最新授权：用户已要求按方案继续调整并尽快结束Phase7，批准仅核验启用有界思考；下方“待授权/产品仍非思考”已过时。理解/决策仍非思考，OutcomeReview使用thinking_budget512、max_completion_tokens1990，推理计入原输出及累计预算。仅thinking的224147负控制仍FAIL，随后text/3改为先核事实来源、再核全部诉求。225009零HTTP预案双审/59可信SHA、材料/schema不变、输入15406/15784；根41项73.542秒、独审4项10.136秒/0skip/source稳定及compileall通过。旧274全量属于这些改动前，稳定后需新全量。
- 当前source-first唯一负控制225432-d2f20860：1HTTP/5032tokens（3577+1455，含512推理）/31358活动ms/0业务出站/source稳定；runner检查通过，阅读全文双审待完成。总理由提缺依据商品译名和漏未来退款，但unit2仍标addressed并编写非正文quote、claim1多引未声明来源、claim2混合事实empty evidence却true。positive及新06–09仍零HTTP，不只据总false宣布语义通过，不得提前升级、clean或commit。

- 用户要求开发Phase7；文本LangGraph、可信全文上下文、多诉求理解/修订、scoped业务/RAG、持久预算、共事务checkpoint/终局、早到事件/等待及工作台运行详情已实现。原6模型/12工具/120活动秒、16k输入/2k输出/80k总量不变；图片、售后写、实际Langfuse、完整删除留8/9/11/12。规划及历次修复标准见[实施步骤](PHASE-7-IMPLEMENTATION.md)，全实测/原FAIL见[验证记录](../verification/PHASE-7-VALIDATION.md)。
- 第三轮fresh reviewer被thread limit拒绝，用户明确批准“允许本次复用审查实例”。该code-reviewer已从Stage1完整重读源文档/代码；当前Stage1仍有真实模型HIGH缺口、Stage2未执行，不称fresh，不改AGENTS默认。最新审查见[第三轮报告](../verification/PHASE-7-REVIEW-3.md)，旧两轮FAIL保留；不得提前clean、commit或正式升级。
- 连续四封分层证据：缺订单第一封旧真实响应仅作已审核历史；第二封原四生成响应严格审计后新核验/真实提交1出站，非新生成；第三封191114实际4HTTP/3工具/16602tokens/41797ms达HITL0出站，后来0chat严格历史初始化不当新质量；194850新第四封4HTTP/2工具/16438tokens/54280ms/1出站核心PASS。单claim弱no-created备注/核验创建与派发精度/等待无补问列MEDIUM，不声称独立售后账本核查。
- 202431新德语完整5HTTP/3工具/18425tokens/40578ms/1出站全文双审PASS，H10/H11该反例关闭。同批06漏未来条件、无据ceiling译名，5HTTP/16841tokens/31327ms/1出站FAIL，首失败停/cleanuptrue，07–09未调用。203514完整坏稿与显式四操作正例0HTTP双审；204212通用尾规则1HTTP3604tokens5967ms误放，205412 reason-first schema1HTTP3602tokens6282ms仍误放；实际SDK/全文/顺序/SHA正确，全部旧FAIL保留，positive零调用。当前停止付费并重审机制，新的必填request_checks/source_checks已落源：服务无损trigger单位与claim索引齐全、引用精确匹配、逐项与总判断共同AND；原DATA完整与预算不变，text/2、graph/2。出处门不证明语义，须新控制及fresh06双审。
- 新结构前258项518.840秒、before-verdict-schema258项515.871秒及before-request-rules773.268秒均保；88.048秒专项原快照曾被覆写，勿冒充保有。逐项协议修前271项524.878秒与反馈修前272项530.155秒全量稳定通过，分别归档。真courtesy/41单位无截断修后14项5.369秒、独审17项11.416秒/eval38项0.867秒通过。最新反馈typed修复root41项70.487秒、独审22项22.997秒/0skip/SHA稳定，compileall exit0/57包兼容；274项最终后端全量542.232秒/0失败/0错误/0skip/source_changed=false已通过，见验证报告及backend-tests-final快照；backend冻结。初版独审21项2FAIL、root错误addressed空quote前提FAIL均保。worker已结束，root owns评测，执行worker不得复用；旧4字段实际响应不补新审项，旧seed在初始化/Embedding付费前拒绝。前端53项2483.4484ms/0skip、vue-tsc/Vite26.17秒通过；Stage2尚须实际邻居渲染对照。
- 211045旧0HTTP正例来源前提不合法，原样留未付费。212036新51来源预案双审PASS，负稿不改；正稿额外恰三项来源元数据修正，正文/claim.text/全部非draft DATA及错误under保持；输入15,364/15,742。212722恰一次negative1HTTP/4,366tokens/17,702ms/0业务：模型仍把未来退款/not-now映到无关物流补问、认错ceiling类型和混合事实；三条引用非逐字/含未声明出处，binding与最终AND均false，不能称新Graph放行。root/独审全文记录及机械反例证明引用门不等于语义正确。positive/fresh06–09尚0新HTTP，H12/H13仍HIGH。仅修Graph失败反馈：真实binding错误传typed代码，合法绑定下语义负项保reason，原一次repair及全文不变；该工程缺口双审关闭。
- 候选仅语义核验启用有界思考，已向用户请求更改DEV-PLAN:348固定非thinking约定，尚未授权。0HTTP完整SDK候选见[预案](../verification/artifacts/phase7/validator-mode-proposal-zero-http.json)：原messages/schema/SOP/错理解逐字保留、.7/30秒/retry0，thinking_budget512、max_completion_tokens1990包含推理与回答，加官方10token容差≤原2k；输入15,364/15,742/预留35,106，当前产品仍false。不得未答即改产品或付费，也不保证JSON容量/质量改善。获准后另冻当期源及完整actual字段（recording当前未捕获max_completion_tokens须同步），先原坏稿一次，首FAIL停；全文双门后才正例与fresh06–09逐案，不重付05。
- 所有实际模型原请求只保Git忽略tmp/phase7-agent-eval，安全SHA/usage/manifest/失败/cleanup摘要在[real-model.json](../verification/artifacts/phase7/real-model.json)，9输入13原资料SHA从首次付费前冻结，开发作者已知材料，不报生产准确率。已授权每个边界根Agent与独审全文双门，首FAIL停，不因completed判质量；当前无再付费授权执行正在进行。现有CLI以--case单独06/07/08/09顺序复验，不重付05、每案新隔离初始化，不改冻结输入或引入参考答案。
- 本期API18181/Web15174独立schema/manual-agent ScriptedModel工程页面已关闭，随机schema及对象目录已清理；root/独审各自CLI均已关闭，root自有CLI delete-data返回无用户数据。正式15173/API18080当前均未监听，未重启或升级；PG15432数据仍Phase6。最新[只读保旧核对](../verification/artifacts/phase7/formal-current-readonly.json)确认0005/54总表及53旧业务表列/行/SHA、配置与160原件字节一致，资料22/22、build/release/cache0、formal-before字节未变。formal-before已冻结0005/54总表/53旧业务表、22原资料/22版本、build/release/cache0、设置与160原件SHA，绝不能覆写。全部四步及独立Stage1/2通过才stop/start-SkipInstall增量升级0006，verify-preservation after --phase 7，核旧53表/设置/160字节与新Agent表为空；不用正式库导入测试或运行评测。隔离launcher通过tmp/phase7-browser.stop已完成自有清理；Stage1通过后若需Stage2渲染，按phase7_browser_app原隔离入口重建，不连接正式库。未来通过升级门槛后正式服务留用户；82AC未勾选、用户查看前不自动开始Phase8。

## Phase 6 历史交接（当期结果）

- 依据[实施步骤](PHASE-6-IMPLEMENTATION.md)完成0005/53业务表（另有alembic_version，总54表）、1024维真实Embedding隔离子进程、结构切分/完整短文/缓存/任务、完整发布清单/CAS/回滚/同模型空间、检索试查/引用与下架及现成Element界面。正式Agent仍未接入，完整删除留Phase12。
- 独立审查发现并修复不同章节前提遗漏、发布状态筛选、政策说明缺明确同意等条件，以及后置停止条件遗漏。policy生成器1.1保留原1.0渲染核验；旧政策可查看但构建明确要求新版本。chunker修订structure/4收集全文中实际SKU有资格的安全前提/停止条件，保留每块位置。第四轮实际GUI又发现明确清空B后重开自动补回、改变未知发布body/key；现按实际组件清空值修正、恢复选择区分未初始化和已清空。四轮FAIL原文不改，第五轮从Stage1重审并通过。
- 审查线程数量上限阻止fresh实例，用户明确批准本期复用原code-reviewer独立重读；不是fresh，不改变AGENTS默认规则。最终后端158项284.276s/0skip通过；第四轮独立PG27项94.862s/0skip、第五轮8子进程1.599s、4parser0.109s通过。根Agent前端40项2514.5697ms与vue-tsc/Vite28.55s通过，独立重跑40项2432.2885ms/Vite27.21s通过，[第五轮Stage1/2本期PASS](../verification/PHASE-6-REVIEW-5.md)。
- 60条原开发查询+新增12条事前冻结，不改标签。旧policy1.0真实结果原正例29/36、新增8/8、多证据3/6完整、边界16/16空，未达到目标，保留原失败/返回全文。最终policy1.1+structure/4已完成：单项44/44，多项5/6完整（11/12项），边界16/16空，正例合计49/50完整达到≥90%目标；独立重算零差异。KQ-058仍漏相关政策条件，不因为命中政策文档算齐全。缺事实6条返回相关资料不证明拒答/业务决策，未调用对话模型或Agent。
- 首个15174隔离页面途中出现22份资料，用户明确确认自己点了“导入准备资料”；当场只读核验正式43表/设置/160原件未变。旧自有窗口已清理，全新空schema及15176/18186用于独占重测。共享状态条Phase5旧文案修正为Phase6发布检索，前端重新40/40及vue-tsc/Vite26.52s通过。
- 第五轮真实GUI已覆盖严格原body/key重试不误发布B、Qwen/V4完整切换与缺项阻止、实际英德试查、回滚新事件、草稿保旧、下架旧ref/旧回滚拒绝、发布筛选/网络错误及明暗1440/900/邻居对照。全部测试窗口CLI/session/服务/schema/对象已清理，正式服务保留。
- 正式入口http://127.0.0.1:15173/#/knowledge，API18080/PG15432，已升级0004→0005并ready/phase6/agentfalse。迁移前43总表→54总表，原42业务表所有旧列行摘要、设置及160原件SHA一致；旧22资料/22版本保留，新index_builds/releases/cache全0，没有测试A/B或评测发布混入正式库。见[验证报告](../verification/PHASE-6-VALIDATION.md)、[迁移核对](../verification/artifacts/phase6/formal-preservation.json)。已有政策1.0可查看但构建要求保存新版本再解析核对，升级不自动改写或发布用户政策。
- Phase5旧临时目录删除曾被策略拒绝，保留不绕过；本期自有fixture/子进程/schema/对象自动清理。未开始Phase7。

## Phase 5 历史交接（当期结果）

- 按dev-builder及[实施步骤](PHASE-5-IMPLEMENTATION.md)交付：原件上传、不可变版本、Markdown修订/PDF替换/受控JSON与JSONL、同源政策编辑、精确SKU/章节/页区间、独立解析、持久任务、原件对照/人工核对、版本差异及操作记录。仅simulation/rag，保存核对到reviewed仍未发布；没有向量、检索、Agent或彻底删除。
- PDF使用独立parser-worker固定MinerU4.0.10/DocVortex0.5.9，115包独立于API25包，15个权重逐SHA核验。模型保留`tmp/knowledge-spike/mineru-home`，独立`.venv`已安装；默认不下载或静默换档。完整17页原件实际274块/26资产，8逻辑范围共用1缓存，最终适配指纹与实际子进程一致。困难样本21/21关键项、16/16行是既有开发样本产物核验，不是生产/未见资料精度，也不是售后判断证据。
- 真实后端123项（PG全部启用、无skip）、前端33项、独立parser4项、3项启停脚本检查及编译/依赖/vue-tsc/Vite通过；最后前端构建26.36秒。实际隔离GUI覆盖新建/核对、响应丢失同key/body重试、政策规则与说明一致、PDF取消/重试/2页换1页、JSON/JSONL只改范围、坏原件详情和恢复重试；独立对照明暗1440/900px邻居页面及PDF详情。见[验证记录](../verification/PHASE-5-VALIDATION.md)、[第三轮fresh审查](../verification/PHASE-5-REVIEW-CLOSED.md)：Stage 1/2本期PASS，无HIGH/MEDIUM阻塞。
- 两轮FAIL原样保留：PDF替换沿用旧页范围、结构化资料改范围被迫填Markdown、原件异常在claim事务内使队首无限回滚。修复后补真实PG→HTTP/runner反例；worker先持久领取租约，再读原件并记录有限重试，坏任务释放槽、健康资料完成。详情原件缺失仍200，下载503，核对提交重新验原件；真实页面attempt4失败，恢复后attempt5完成。缓存不能跳过原件核验，提交途中租约失效会回滚产物。
- 正式入口http://127.0.0.1:15173/#/knowledge，API18080/PG15432。启停脚本升级0003→0004，32旧表行数/行摘要及设置SHA一致，新增10知识表仍无正式资料；API/代理六项HTTP200和非法Host/Origin拒绝通过。正式页面已只读查看空库、34 SKU与Basic/Standard可用，没有导入测试包。本期提交号以`git log -1`为准；正式服务保留给用户。
- 隔离浏览器、15174/18181服务、随机schema及私有临时对象目录已清理；`tmp/phase5-*`辅助文件和`tmp/phase5-parser`解析产物删除被自动审批拒绝（仅返回`blocked by policy`），仍保留，不重试绕过。安全证据保存在`docs/verification/artifacts/phase5`及`output/playwright/phase5-*.png`，安装环境和本地模型保留。下一期Phase6是切分、向量构建、发布/回滚、检索试查与下架，先读Spec/主架构/DEV-PLAN原文；不要把本期局部核对门关闭为82项产品验收。

## Phase 4 当前交接（优先于下方历史记录）

- 用户要求继续Phase 4，按dev-builder完成[实施步骤](PHASE-4-IMPLEMENTATION.md)：白名单资料装载、12表统一业务账本、scoped订单/行/物流/库存查询、只读售后条件、实际客户选择及工作台集成。原v1不改字节；v2同源规则/中文说明保持未发布，原场景仍绑定v1。没有模型调用、真实收发或售后执行。
- 资料只加载72个dev场景的初始来信/状态；每次新命令独立身份/分支，同key复用。没有读取完整故事、未来事件或参考答案；历史逐记录过滤Mock且遵守可见消息截点。现有来源没有可授权真实客户订单快照，手动/历史保持不可用；SCN029是合成历史边界，不能当真实历史评测。
- 多商品逐行核对，相同SKU用第几项区分；包裹/执行/退件严格按订单与行显示。客户选择只取已见消息，独立按持久seq选最新；新拒绝/改方案不会被旧同意覆盖。退件按实际质检数量/份额，库存缺时间或未来快照保持未知；图片观察/客户陈述不会因查询包装变成仓库事实。
- 全套后端88项真实测试（PG启用、无skip）、前端28项、Python编译/依赖、vue-tsc+Vite、既有3脚本检查通过。实际隔离GUI覆盖断网恢复、多行包裹、实际选择、900px明暗抽屉、未知创建同key重试及人审草稿/模拟回复。结果见[验证记录](../verification/PHASE-4-VALIDATION.md)；[最终fresh审查](../verification/PHASE-4-REVIEW-CLOSED.md)Stage 1/2均PASS，独立重跑88/28测试及构建。仅保留非阻塞LOW：收件/质检/签收日期缺口汇总用通用中文标签，详细条件及计算正确。本期提交号以`git log -1`为准。
- 三轮FAIL均保留，已补数据库→查询→正式HTTP反例；第四轮从Stage1重新开始。不将纯函数PASS替代集成正确，不把这期工程验证记成AI理解/七类业务总验收。
- 正式入口http://127.0.0.1:15173/#/workbench，API18080/PG15432；启动脚本升级0002→0003并保留配置/PG卷。正式核心四表升级前后为空，12张业务表也为空，没有测试会话；这不能证明已有真实用户订单迁移。六项HTTP/代理检查及非法Host/Origin拒绝通过，Phase4/72目录真实可读。
- 所有Phase4浏览器、隔离15174/18181服务、随机phase4_browser schema及临时对象目录已清理；正式服务保留给用户查看。继续开发读取本段、根目录Spec/主架构/DEV-PLAN原文；下一期是Phase5知识原件上传、解析对照与人工核对，不能提前开放知识发布/Agent。

## Phase 3 当前交接（优先于下方历史记录）

- 用户要求继续Phase 3；按dev-builder实施会话/消息/受控JSON/逐封回放、人审/人工回复/结案重开、cycle/run/job/stop/retry、双槽租约/fence、事件日志/SSE和三栏界面。精确实现契约见[Phase3集成契约](PHASE-3-CONTRACT.md)，规划见[实施步骤](PHASE-3-IMPLEMENTATION.md)。
- 本期runner只验证任务协议，不调用模型或生成AI回复，不投递真实邮箱。CaseIssue是稳定correspondence基础事项，事实带来源与可见seq；跨源可信身份复核未开放，历史订单snapshot未接，语义多事项/业务查询/知识/正式Agent均不能声称完成。
- 后端34真实测试（全启用PG，无skip）、前端18测试、Python编译/依赖、vue-tsc+Vite构建、既有3脚本检查通过；真实隔离服务SSE补读/15秒心跳/GET无写、真实文件导入及人审/旧草稿刷新/结案重开/明暗窄屏/网络错误同key重试/阅读滚动均有证据，见[验收记录](../verification/PHASE-3-VALIDATION.md)。[最终fresh审查](../verification/PHASE-3-REVIEW-PASS.md)Stage1/2均PASS，五项旧问题关闭；一项非阻塞LOW：后续对齐任务error_code文案字典，当前状态标签/显式重试提示正确。
- 初审旧草稿输入版本HIGH，第二轮结案接管/知识死锁/GUI Proxy导入，第三轮初挂载阅读位置MEDIUM均已修并保留原FAIL报告；最终从Stage1重新审。别把旧报告改成PASS，也别把工程层测试改写为完整模型/七业务验收。
- 已按用户批准更新AGENTS“全程中文、口语化、说人话、不用文言文”，dev-builder加入AI读材料/业务判断/格式分层记录规则；已处理进化信号，不需要再次询问。没有变更模型或Phase1历史结论。
- 本机正式入口仍是 http://127.0.0.1:15173/#/workbench 与 API18080/PG15432；本轮隔离测试使用15174/18181、随机schema和临时对象，收尾清理。启动脚本运行Alembic升级到0002，保留既有数据。
- 下一步Phase4：受身份/模式/历史截点约束的商品、订单、库存、物流、政策条件查询。用户查看Phase3前进度写“技术验证通过，待用户查看”，不要擅自关闭82项AC。

## Phase 2 当前交接

- 代码在globalmail-agent/backend、frontend、infra、scripts。沿用锁依赖与Art Design Pro副本，未动原模板项目；Phase1和Phase2分开提交，Phase2提交号以git log为准。
- 当前页面 http://127.0.0.1:15173/#/workbench，API http://127.0.0.1:18080/api/v1/health/ready，PG仅127.0.0.1:15432。本项目独立Compose名globalmail-agent、卷globalmail-agent_postgres_data；既有其他项目容器未修改。
- 启动`pwsh -File globalmail-agent/scripts/start-local.ps1`；已装依赖可加-SkipInstall。停止`stop-local.ps1`，加-StopDatabase同时停本项目PG，均保留数据。密码只在忽略的.local-data/runtime；不要把配置/日志公开。后台服务当前保留给用户查看。
- API统一HTTP/envelope成功码200；live/ready/runtime-config无密钥或连接串。ready检查真实PG、迁移表和对象目录。工作台/知识库为真实未开放状态，无模板登录/假token/假业务成功。
- 四张基础表、scope复合外键、UUID对象/摘要/原子落盘与来源依赖已实现；删除journal仅基础。未实现附件上传、删除工作流、会话、业务查单、知识发布、模型运行。
- 已验证12后端测试（6真实PG）、4前端测试、3脚本测试；Python编译、vue-tsc+Vite构建成功。实际容器重启后正文/元数据仍可读；DB停机/API断开时页面显示真实错误并能恢复。独立复审两阶段PASS，详见[Phase2记录](../verification/PHASE-2-VALIDATION.md)及[复审](../verification/PHASE-2-REVIEW-FINAL.md)。
- 初审envelope成功码不一致已修；PowerShell7.5 JSON日期自动转换导致漏停进程已改UTC ticks比较并覆盖登记往返测试。历史报告不改成PASS。
- 下一步按DEV-PLAN进入Phase3（会话/消息/回放/人审/持久任务），先阅读其原文与相关架构，不能提前声称Phase2已有这些能力。不再反复运行Phase1合成图探索。

## 最新用户决定

2026-10-07：用户要求先提交Git，再开始Phase 2。Phase 1本轮探索结束，不再为合成集反复调用付费模型；54次目标字段提取均匹配，业务分流错误不等于OCR/VLM能力失败。原验收失败及人工pending作为历史证据保留，继续Phase 2不需要再次确认。以下Phase 1“未提交/下一步修正”等为当时记录，以本条决定为准。

## Phase 1 当前交接（优先于下方历史记录）

- 已读规则/需求/架构/计划并用dev-builder实施。`data/visual/v1`冻结35个AI合成案例及VIS-001–018分支；标签与模型输入隔离，人审pending。不是生产客户数据，也未证明照片真实SKU身份。
- `globalmail-agent/vision-spike`包括制作、预处理、真实请求、校验、离线评分、中文报告和证据归档；锁定tech-spike环境，模型/预算未更换。最终final-v5共108次：104结构成功、4拒绝、300,520已知tokens；规则初筛88次通过不代表业务通过。
- 独立语义审阅发现9次关键失败：不合资格仍申请3、政策缺证据仍申请3、额外插电指导1、无SOP紧固维修1、虚构订单核验并混用型号1。保留原始输出，不以Schema失败遮掩越权。详情见[专项报告](../verification/VISUAL-VALIDATION.md)。
- 用户明确反馈此前“标签核对”表述看不懂，已解释为看图判断参考处理答案是否符合业务，并制作[中文逐例页](../../data/visual/v1/review.html)。用户没有确认标签，不要自动标已验收或重复要求看JSON。bent和补角度案例有标签争议，需先人工核对，再新版本重测，不能改旧答案刷分。
- 28项离线测试通过；编译、freeze校验及真实CLI已跑。初审/复审历史报告保留；最终代码审查见模块review-close.md，语义审阅另有v4/v5 JSON与Markdown。实验代码可用与Phase业务验收是两项结论。
- 下一步修资格/证据、SOP边界和图商品核验后在原模型预算复测；不能关闭Phase 8/13。DEV-PLAN允许独立Phase 2工程准备，本轮没有开始。不要继续反复付费仅为追求全绿；先处理已定位问题和参考答案争议。
- 真实回复、manifest/labels/freeze快照留在本地忽略目录`tmp/vision-spike`，模块内已保存摘要/哈希用于追溯。审查尚未通过，本轮未写clean、未提交Git。full-v2中断时在途消费未知、final-v4有1次usage未知，不能把已知tokens说成完整账单。

## Git 提交前检查与新窗口入口

- 2026-10-07：本次提交整理需求、主架构、专题文档、DEV-PLAN 及两组实验源码/结果；正式应用开发仍未开始。根目录只保留五个 Markdown 入口，具体提交号以 `git log -1` 为准。
- 提交前离线复核：21 份文档、112 个本地链接及 82 项 AC 映射通过；20 个 Python 文件内存编译通过；技术实验 4 项测试通过，知识实验 19 项通过、5 项数据库测试按设计跳过。两套环境的 75/115 个依赖均兼容；本轮未重跑数据库、付费模型或正式应用验收。
- 实验源码和结果原有 36 条 SHA-256 记录逐项核对；审查报告仅随目录迁移改了引用路径，已保留原摘要并记录本次摘要更新原因，反向替换与原摘要一致。`.gitattributes` 保留两组实验目录的原始字节，避免检出转换换行造成摘要失效。
- 新窗口先读根目录 AGENTS.md、Product-Spec.md、AGENT-ARCHITECTURE.md、DEV-PLAN.md 和本交接，再使用 dev-builder 从 **Phase 1：客户图片样本与真实图文风险实验** 开始；沿用既定计划，按阶段验收。组件实验通过不代表正式功能完成。

## 本轮一致性检查与开发计划

- 统一已定技术选择、已制作业务数据、实验索引与正式索引、短文切分、金额表示、危险直接分流图及当前进度表述；未发现需重新决策的业务范围冲突，具体记录见 [一致性检查](../verification/DOCUMENT-CONSISTENCY-REVIEW.md)。
- DEV-PLAN覆盖14项REQ、20项P0 SCOPE、82项AC及全部SCN/JRN/VIS/DEMO/FT范围，按13个可独立验收阶段列出文件、依赖、数据库和完成门槛；不把组件实验或设计PASS记为产品完成。
- 本轮只修改说明文档并制定计划，未运行客户图片模型、未改业务源码/数据fixture、未创建正式数据库/服务。以下各专题保留此前阶段的产出与边界；其中历史版本号和“该阶段未创建”不是当前进度。

## 客户图片三项能力增量

- 用户确认先同步需求/架构/验收：图片文字提取、可见产品异常理解、有依据的售后分流。Spec新增REQ-014、AC-065至AC-082，总计82项AC均未执行；OUT-004不再排除客户静态图，客户PDF/视频/音频仍不支持。
- 支持JPEG/PNG/静态WebP附件及有受控字节的CID图、纯图片来信；真实邮箱接入仍另定。Qwen3.7-Plus在Understanding节点联合读图，无独立视觉Agent或默认OCR服务，不将客户图片放进共享向量库或MinerU知识发布链。
- 字段候选、视觉观察、原因推测、客户陈述、业务核验分开；订单/SKU精确查证，SOP/政策及客户选择决定动作。照片未见异常不否定客户功能故障，照片未拍到不证明缺件，危险迹象人审不等订单；图片不自动确定根因/责任/真伪/交易资格或成功。
- 图片按原6模型/12工具/120秒及token预算处理，初值每封4图、每张10MiB/20百万像素、合计20MiB、每轮6视图；这些是待实测应用限额，不能声称模型必定一次处理成功。
- 增量独立复核发现危险分流优先级缺口，已补设计：有效risk_flags与HumanReview同事务落库、确定性handoff，不等待额外决策模型，技术失败/预算不足不能漏掉已识别人审；旧运行仍服从处理权/版本/删除栅栏，未识别风险不伪造危险。
- 架构第4.4节补接收/视图/字段与观察schema、逐图状态、客户/历史隔离、人工更正、缓存、删除与晚到栅栏；提交锁序补附件/证据修订锁，checkpoint与trace纳入清理。
- VIS-001至VIS-018为待制作图片专项，原72个已制作输入不增加；单页产品资料读图不证明客户缺陷识别准确率。本轮只同步文档，未生成图片/调用模型或修改业务源码。
- 旧AGENT-ARCHITECTURE-REVIEW仅覆盖v1.0；本次 [AGENT-VISUAL-REVIEW.md](../verification/AGENT-VISUAL-REVIEW.md) 增量设计审查PASS，1项MEDIUM（危险分流优先级）和1项LOW（DEMO旧计数）均已修订并复核关闭。11份文档的链接/围栏、82项AC唯一映射及18项VIS对应已离线检查；真实图片质量/延迟和工程契约仍须后续执行。

## Agent 架构细化

- 新增 AGENT-ARCHITECTURE.md：单主 Agent、理解节点/动态工具循环、可信RunContext、会话/运行/内部申请/执行单状态、工具契约、事务/租约/幂等、知识管线、API/SSE、清理及部署边界。
- input_revision（外部上下文）、authority_epoch（执行权限）与case_revision（本轮记忆）分开。HITL结束本轮，人工回复后只由下一封新客户来信启新run；停止或进程中断需要显式retry，后台事件不能绕过门禁。
- 补偿按订单行/受影响数量跨run校验；内部申请与模拟ERP执行分开。未知结果先查原操作。最终回复/写入同事务核对处理权、引用资格和发布head，不能在guard后另开无保护事务写入。
- 业务结果早于wait注册也保留wake_pending并补查，不漏唤醒；同一run固定知识release/profile，变更只经一次预算内统一上下文重建。CheckpointRepository覆盖put/pending-writes持久写栅栏，删除需等待在途写入停止并清理已暴露给模型的正文依赖。
- 原架构v1.0逐项映射64 AC、30 SCN、21 JRN和12类故障时序；当前验收映射已增加上述图片范围，仍是未来验证设计，未运行正式业务测试。
- AGENT-ARCHITECTURE-REVIEW.md独立设计审查PASS：1项HIGH（结果先于wait导致漏唤醒）及1项MEDIUM（同run知识快照混版）均已修订复核关闭；检查点删除加固也已复核，未执行应用验收。
- 轻量纠正Spec旧句：Agent只提交内部申请、控制台模拟执行；SDK追踪已实测，但正式Langfuse服务尚未部署。模型预算仍为6次请求/12次工具/120秒、16k/2k/累计80k、网络30秒。

## 知识管线实测进展

- KNOWLEDGE-VALIDATION.md 汇总本轮结果；globalmail-agent/knowledge-spike 保留脚本、依赖锁、冻结查询、原始/修订结果，临时产物与模型在 tmp/knowledge-spike。
- MinerU 4.0.10 Basic/Standard 在两份 4 页困难样本上均完成 21/21关键项及16/16表行，Basic 更快，推荐默认复杂PDF解析；原17页34SKU8图片存在性检查通过，不代表图像操作事实已核准。
- 60条开发查询对照 v4 和 qwen3.7-text-embedding 1024维，新模型整篇正例top1为29/36、v4为18/36。细切后同文档占满top5是问题；按父文档去重补全后两者36正例+6多证据+12边界全覆盖。候选少且用开发集调参，不叫100%生产精度；300/500实际块内容相同，未得长文最优参数。
- 固定18条真实Qwen证据检查初版13/18，补可信simulation模式/结果不确定性定义后18/18（6无答案全拒猜）；不是完整回复验收。旧结果保留。
- 隔离PG生命周期7组检查+8契约测试通过；真实双模型向量、两连接快照、下架/晚到任务/删除栅栏已验证，修复共享政策SKU与brand成对过滤。删除只覆盖实验数据库，未完成正式对象/隐私清理、政策捆绑、worker或备份恢复。容器及凭据已清理。
- 首审三项问题（父正文复核、失败后旧缓存误用、并发实验措辞）已修复，fresh 独立复核 PASS；14 文件编译、115 依赖兼容，普通测试 19 通过/5 DB 跳过，另有实际 DB 8 项全过。报告及验证摘要在实验目录。后端总览第7节已对齐知识选择，旧探针不改写，模拟资料用途不变。

## 长期知识维护方案

- 用户关心现有模拟资料后续增删改查、Embedding 与切分，并要求评估 MinerU；职责推荐为业务负责人维护内容、技术人员维护入库系统，初期可单人兼任。
- KNOWLEDGE-DESIGN.md 规定最小知识管理页面、原件/版本/索引分层、发布与回滚、增量向量化、下架与彻底删除、迟到任务和缓存撤销；Product-Spec v1.10 已消除旧的仅导入/移除范围冲突，新增 AC-057 至 AC-064，均未验收。
- MinerU 4.0.10 已在独立环境安装，Basic/Standard 模型已下载并完成上述比较；本机 RTX 5060 Ti、8151 MiB 显存。推荐 Basic 处理复杂 PDF，正式部署仍需核对该版本许可附加条款及实际负载。
- text-embedding-v4 1024 维保留为实测基线；qwen3.7-text-embedding 经 60 条开发查询对照后推荐为下一阶段主候选。短资料完整保留、长文结构切块并补父文档；长文参数和独立评测仍待验证。
- 该阶段的TECH-SELECTION v1.2、BACKEND-ARCHITECTURE v1.4和详细架构已对齐知识方案；当时未创建DEV-PLAN或业务代码，simulation资料不直接改标签用于生产。当前版本见本文件顶部。

## 本轮技术选型进展

- 已有 TECH-SELECTION.md 与 `globalmail-agent/tech-spike/`；Python 依赖锁、3 个探针及结果文件已保存。
- 实测通过：百炼原生 JSON Schema、流式工具往返/usage、PDF 17 页文本与嵌图读取及单页读图、text-embedding-v4 1024 维、24 条开发查询的 pgvector SKU 过滤、PG 检查点重连/幂等示例、Langfuse SDK 回调/异步关联/测试属性过滤。
- PG 从推荐初值 16 更新为新项目采用的 18.6，vector 0.8.6；固定镜像 digest 见技术选型文件。临时验证容器已移除。
- 当前只做组件验证；正式知识索引、业务 Agent、任务 worker、售后状态机、完整 Langfuse 服务和前端适配仍未实现。
- 按用户“按顺序来”的要求，先完成选型，再细化状态、工具契约、持久化和部署设计，最后才生成 DEV-PLAN。

## 当前目标与已确认范围

- 构建准生产智能邮件售后 Agent；先在隔离环境跑通业务，真实收发、财务和履约接入另定。不要重新降格为单场景 Demo。
- 三品牌：OUTON、OUTONLIFE 灯具；BELEEV 滑板车。首批 8 个产品系列、34 个 SKU。
- 七类业务：产品咨询、故障排查、物流查询、退款、退货、换货、补寄配件，全部属于首版。
- 同一发信人保留同一会话，内部按订单及售后事项分别跟踪。订单号用于查询准确 SKU，已有信息须复用。
- Agent 自主查资料、调用工具、补问、生成内部待办和自动模拟发送。人工负责具体业务履约，控制台推进模拟执行记录，Agent 查询并跟进。
- 无可靠依据或出现安全问题等情形触发人工接管；期间只记录新信息。人工回复后，下一封客户来信才自动恢复 Agent。最终结案由客服确认。
- PostgreSQL + pgvector 路线已定；主 Agent、LangGraph、确定性业务服务、持久化任务、Langfuse 为推荐架构。不要重新发起 Neo4j 选型讨论。
- 主模型使用 qwen3.7-plus，模型适配和 Embedding 已完成组件小测；真实 Key 只在被 Git 忽略的本地 .env 中。结果范围见 TECH-SELECTION。
- 前端基于用户指定的 D:/Work_Project/art-design-pro 副本，位于 globalmail-agent/frontend/；沿用现成组件与工程，不能回到旧邮件工作台风格。
- Git 提交标题和正文使用中文。作者：张帅，823585487@qq.com。

## 已交付的数据

入口：data/knowledge/v1/README.md。

- 22 个逻辑知识文档：8 份产品资料（合在 17 页 PDF 中）、8 篇排障说明、5 篇真实往来案例、1 份政策说明。
- 8 张真实商品照片，34 个 SKU，53 个模拟配件及适配关系，87 条库存；政策 JSON 与中文说明同源，当前政策补丁版本 1.0.1。
- 原 51 个环节样例、48 行控制事件、24 条检索问题保留。
- 新增 21 条完整流程（每类 1 主流程 + 2 分支），287 个后续步骤，88 封客户来信，50 段仅供评测的参考回复，11 份本地寄回资料。总共 72 个场景输入。
- 连续流程目录：data/knowledge/v1/scenarios/journeys/README.md；人工可读案例在 readable/，初始输入和未来事件分开，评测答案在 evaluation/。
- 退款失败对账、客户拒绝方案、退货验收争议、附件重发、缺货、地址变化、误投、补件仍无效、改退款、人工接管恢复和结案已有连续数据。

## 数据的重要边界

- 用户允许虚构，但必须贴近日常跨境售后。业务正文用自然语言，内部测试字段与客户往来分开。
- 商品身份、商品图和价格原型来自生产只读资料；新增往来、地址、政策、库存和执行记录为编写内容，不冒充真实履约。
- 44 个真实来源会话、285 封邮件保存在被忽略的 .local-data/knowledge-v1/；仅 5 个审读案例进入知识资料。未经复核的正文和独立评测组不进入 RAG。
- 45 条 YouTube 链接只是目录，未观看、未建立已验证 SKU 适用关系。未知参数和维修步骤继续保留未知。
- 只有知识正文计划做 Embedding。商品映射、订单、库存、执行记录与政策资格通过数据库/业务工具读取；完整演练故事、参考回复和未来事件不能入 RAG 或提前给 Agent 看。
- 寄回 HTML 是可审阅的虚构资料，不是承运商可实际扫描使用的标签。

## 验证与未实现部分

- 原资料 40 项检查、新增连续资料 33 项检查、8 项正反例测试通过。
- 独立审查通过，文件哈希及结论见 data/knowledge/v1/sources/journey-review.json。
- 新增资料离线重建结果一致；PDF 未在连续流程补齐时更改。
- DEV-PLAN.md已制定；尚未实现正式业务后端、知识入库器、应用检索服务、Agent业务执行或前端业务适配。独立技术探针已验证Embedding与临时pgvector检索，不改变这里的应用完成状态。
- 静态检查通过不代表模型、业务状态机或真实系统通过。后续必须执行真实模型调用和逐轮业务测试。

## 新会话推荐顺序

1. 读取 Product-Spec.md v1.13、AGENT-ARCHITECTURE.md v1.1、AGENT-ACCEPTANCE.md、BACKEND-ARCHITECTURE.md及对应版本架构审查记录，再读TECH-SELECTION、KNOWLEDGE-DESIGN和专项实测。
2. 读取资料 README、DATA-CONTRACT.md 和连续流程目录；无需重做业务访谈或重新造同一批数据。
3. 读取DEV-PLAN v1.0及本轮一致性检查；进入开发时用dev-builder从Phase 1冻结VIS图片样本及Qwen真实视觉实验开始，不重新生成计划、不把待制作样本或未执行阶段描述为完成。
4. 沿用技术探针已验证的依赖组合，在正式应用中补齐迁移、服务部署、进程恢复和业务验收。不要将作者脚本里的参考回复作为 Agent 的真实输出。

单独重建新增数据可依次运行：

```powershell
python -X utf8 data/knowledge/v1/tools/complete_step_fixtures.py
python -X utf8 data/knowledge/v1/tools/build_journeys.py
python -X utf8 data/knowledge/v1/tools/validate_journeys.py
python -X utf8 data/knowledge/v1/tools/test_journey_integrity.py
```

完整资料重建入口是 tools/build_all.py，需本机受控来源目录及 PDF 依赖。该入口不会连接生产；extract_sources.py / fetch_product_photos.py 则是显式生产/来源刷新入口，不要混用。
