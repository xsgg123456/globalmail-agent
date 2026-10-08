# Phase 4 验证记录

日期：2026-10-08。依据：Product-Spec v1.13、AGENT-ARCHITECTURE v1.1、DEV-PLAN Phase4及[实施步骤](../planning/PHASE-4-IMPLEMENTATION.md)。当前状态：四步技术验证及最终独立两阶段审查通过，本机已升级，待用户查看；82项产品AC没有整体验收。

## 交付与边界

- 白名单读取商品、配件、适配、库存、同版政策及72个dev场景的初始来信/状态；每个场景创建独立身份/分支，不读取controller、完整故事、评测答案。既有操作、执行、包裹、退件统一scoped账本，Phase9继续使用该结构。
- 精确查单/行、适配和库存，统一REPEATABLE READ；跨范围拒绝，缺字段保留未知，多商品不默认第一行；历史逐记录排Mock并按真实可见消息截点读取。
- 只读资格预览检查整数金额/数量、受影响份额、既有补偿、最新可见选择、地址版本、证据类型、库存及仓库验收条件。政策未发布，始终`authorized:false`，预览标识不能授权写操作。
- 页面继承现有Art Design Pro卡片、折叠区和抽屉，逐商品行展示账本，以第几项区分相同SKU；实际客户选择显示动作/数量/金额币种/第几封来信/地址版本，与试填候选分开。
- 当前没有获授权真实客户订单快照；手动会话不因输入同名/订单号接上其他身份。SCN029仅是合成历史边界，原clock与消息日期不一致未改写；不能当真实历史业务评测。
- 本期没有模型调用、客户图片理解测试、七类业务自动回复、知识发布、售后执行、库存占用或真实收发。Phase1原失败及人工pending保持原结论；v2为未发布的管理预览，原v1场景固定1.0.1。

## 完整回归与编译

服务端临时读取忽略目录内连接串，仅赋测试变量，不打印。所有数据库测试用随机schema和临时对象，最终清理；浏览器15174/18181为独立测试服务，正式15173/18080未写入测试场景。

| 实际命令 | 本轮输出 |
|---|---|
| `python -X utf8 -m unittest discover -s globalmail-agent/backend/tests -v`，设置绝对PYTHONPATH与GLOBALMAIL_TEST_DATABASE_URL | `Ran 88 tests in 98.897s / OK`，无skip |
| 前端目录 `pnpm exec tsx --test scripts/*.test.ts` | `tests 28 / pass 28 / fail 0 / skipped 0`，666.8995ms |
| 前端目录 `pnpm build` | `vue-tsc --noEmit && vite build`，零类型错误，Vite `built in 26.22s` |
| `python -X utf8 -m compileall -q .../src .../migrations .../tests` | 最终复核零错误 |
| `uv pip check --python globalmail-agent/backend/.venv/Scripts/python.exe` | 最终复核24个包兼容 |
| `python -X utf8 data/knowledge/v2/build_policy.py --check` | 最终复核verified，publication_status=unpublished |
| `pwsh -NoProfile -File globalmail-agent/scripts/test-local.ps1` | 3项PASS：初始化保留凭据、端口冲突拒绝、所有者进程登记/停止 |

88项包含既有34项、政策28项、资料/账本12项、HTTP6项、数据库到正式HTTP反例8项。前端覆盖纯计算、实际composable请求/状态和故障/切会话/晚到结果；它们不替代下方真实GUI验证。

## 审查发现与回归补齐

初审及历次FAIL保留，不把编译绿灯当业务正确：

| 发现 | 修复及实际反例 |
|---|---|
| 质检数量投影丢失，把收2检1算成全验收 | 保留inspected_quantity/inspected_unit_ids；正式HTTP检1无单位needs_input、检1明确份额wait、检2明确两份eligible；均不能执行 |
| 相同SKU行/包裹难辨 | 卡片/选择项第几项，严格按order+line展示；真实SCN008选择第2项仅显示SECOND运单 |
| 合法历史父订单仍混入synthetic行 | 逐行及商品来源过滤；合法时间混合来源真实PG回归无SKU泄露 |
| 实际客户选择未展示 | 受控白名单公开可见选择/地址版本；未来消息选择与地址不公开，私密地址token不返回，多行关联不猜 |
| choices数组反序时旧同意覆盖新拒绝 | 持久消息seq排序且领域独立取最大seq；最新拒绝/改动作/未绑定、同seq歧义阻止eligible |
| 库存缺快照时间仍eligible | 查询可用数保持null，资格要求可信时间<=截点；正式HTTP缺/未来时间needs_input，有效时间正例eligible |
| 查询包装把visual_observation升级成仓库事实 | 仅受控Mock业务事实升为verified_fixture，其余保留kind；正式HTTP图片退件不能满足收件条件 |

原审查：[初审FAIL](PHASE-4-REVIEW.md)、[第二轮FAIL](PHASE-4-REVIEW-FINAL.md)、[第三轮FAIL](PHASE-4-REVIEW-PASS.md)（该文件名含PASS但正文实际FAIL）。[第四轮fresh报告](PHASE-4-REVIEW-CLOSED.md)正式签署Stage 1/2均PASS，HIGH 0、MEDIUM 0、LOW 1；独立重跑后端88/88（99.503s）、前端28/28及构建，并逐项列出82项AC的归属和未完成限制。

非阻塞LOW：仓库收件、质检、签收日期三个条件在缺口汇总中使用通用中文标签；逐条件中文详情和资格计算正确。保留为后续文案改进，不将本期范围扩大到未完成的知识/模型或售后执行。

## 实际浏览器

真实API+Vite+PG，Playwright独立session。已核验：

| 流程 | 实际结果与截图 |
|---|---|
| SCN025订单/既有补发/资格/库存 | 订单USD35.99；候选USD3.50因既有补偿与缺同意须人工核对；现有5/占用0但可用数未知，明确缺库存时间/地区/硬件；[订单](../../output/playwright/phase4-business-desktop.png)、[条件](../../output/playwright/phase4-conditions-desktop.png) |
| 真实断网与恢复 | route.abort造成GET失败，保留ORDER-NETWORK-CHECK；撤销故障、清空精确号重查恢复；[错误](../../output/playwright/phase4-network-error.png) |
| SCN008同订单同SKU两行 | 未选时需澄清；两项序号不同；选第2项只显示SIM-TRACK-SCN-008-SECOND，没有第1项运单；1600px无横向溢出；[逐行物流](../../output/playwright/phase4-multiline.png) |
| BASE-OUTON-04实际选择 | 退款已同意、USD54.99、数量1、对应第1封来信与第1项；地址版本1、此次选择未明确地址版本如实显示；[选择](../../output/playwright/phase4-choices.png) |
| SCN029历史不可用 | 显示合成历史边界及真实截点，订单/政策/Mock SKU均不补造；[历史](../../output/playwright/phase4-historical.png) |
| 900px明暗抽屉 | 实际主题切换、重新选择并打开处理详情，折叠/表单可用；两主题document scrollWidth=clientWidth=900；[深色](../../output/playwright/phase4-narrow-dark.png)、[浅色](../../output/playwright/phase4-narrow-light.png) |
| 创建结果未知后重试 | 真实route.fetch先完成提交再abort响应，同场景重试202；sameId/sameCommand=true，列表匹配会话仅1条；[未知结果](../../output/playwright/phase4-create-unknown.png) |
| SCN028人审回归 | 初始接管表单可用，保存草稿保持接管；完成模拟回复后等待新来信，时间线新增模拟人工第2封，无AI回复；[人审](../../output/playwright/phase4-human.png) |

故障注入产生的网络控制台错误按测试预期记录，不声称全程没有控制台错误。手机精细适配仍属P1，没有拿900px测试替代全尺寸验收。

## 正式本机入口升级

- `stop-local.ps1`后运行`start-local.ps1 -SkipInstall`，PG卷与配置保留，Alembic从`0002_conversations_jobs`升级到`0003_business_catalog`；12张业务表已建立。
- 本轮升级前正式库的conversations/messages/objects/content_dependencies均为空；升级后ID列表逐项相等，12张业务表也为空。没有用空库升级宣称已验证实际用户订单迁移，也没有把浏览器测试场景搬进正式库。
- `python -X utf8 globalmail-agent/scripts/check-runtime.py`输出`status:passed`：API及前端代理六项HTTP检查均200，非法Host/Origin拒绝；本轮未再次重启PG验证持久化。
- 只读核验运行配置`phase:4`，business_queries/conversations开启，knowledge/agent关闭；场景目录72条。正式页面显示Phase 4、依赖就绪和“初始业务场景”入口，下拉项实测72条并[截图](../../output/playwright/phase4-local.png)；现有模型配置只显示“已配置，未验证连接”，没有调用模型。
- 正式入口的额外自动化在打开下拉后点击取消，被覆盖在按钮上的选项拦住而超时；已关闭该QA浏览器，没有创建会话。不将这次部分只读核验记成完整创建流程通过；完整创建/未知结果重试已在隔离服务验证。
- 保留用户入口`http://127.0.0.1:15173/#/workbench`及API18080/PG15432。隔离服务输出`Isolated processes/schema/object directory cleaned.`，随后只读复查`phase4_browser_*` schema与对应临时对象目录均为0；各QA浏览器已关闭。
