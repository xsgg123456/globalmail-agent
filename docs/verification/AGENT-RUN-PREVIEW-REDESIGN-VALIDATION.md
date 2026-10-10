# Agent运行台预览重设计验证

日期：2026-10-09。范围：用户反馈运行台不好看后的第二版视觉迭代，仅15175隔离预览；验收来源为[实施规划](../planning/UI-PREVIEW-IMPLEMENTATION.md)。首次[预览验证](UI-PREVIEW-VALIDATION.md)与[独审](UI-PREVIEW-REVIEW.md)保留原结论。

## 结果与边界

顶部概览、两栏时间线/节点详情、运行历史抽屉、角色提示词、可读字段和完整原始JSON已实现。保留Art外壳、Element主题和既有预览内存数据。未暂存或Git提交，未调用模型、发真实邮件、写正式业务数据。生产15173/18080继续运行；正式逐次模型采集和业务解耦仍属于后续实施。

fresh独立审查Stage 1/2均PASS，无未关闭HIGH/MEDIUM；见[本轮报告](AGENT-RUN-PREVIEW-REDESIGN-REVIEW.md)。独审另实测草稿、人工屏障、正常事件生成run04及原15173邻居明暗渲染，区分自己的实测和主Agent响应式/编译证据。

## 工程验证

| 验证 | 实际结果 | 原始证据 |
|---|---|---|
| 前端现有测试 | 64 pass / 0 fail / 0 skip，2852.9602ms | `.local-data/runtime/agent-redesign-tests.log` |
| 正常模式编译 | vue-tsc无错误，Vite 26.22秒，退出0 | `.local-data/runtime/agent-redesign-normal-build.log` |
| 预览模式编译 | vue-tsc无错误，Vite 17.85秒，退出0 | `.local-data/runtime/agent-redesign-preview-build.log` |
| 最后文案入产物 | 构建JS包含“正式接入时读取供应商”；不是旧文案产物 | `rg -l`只读取构建产物的匹配文件名 |
| 本轮运行台浏览器 | warning/error日志为空 | CUA独立tab实际记录 |
| 本轮7个程序文件 | ESLint退出0；最大157行；diff --check退出0 | 只检查本次展示层文件，无全仓改写 |
| Git限制 | `git diff --cached --name-only`为空，未执行commit | 当前索引只读检查 |

64项是既有前端回归，不将它们称为新增组件单测；本轮新增交互由真实浏览器和独立审查验证。

## 浏览器交互

| 路径或状态 | 实测证据 |
|---|---|
| 默认模型输入 | 系统提示词与用户上下文分段，model/enable_thinking/temperature可读；工具Schema和完整请求可展开 |
| 完整请求 | 原JSON保留model、参数、system/user消息和工具schema，未用摘要替换原请求；Schema展开后用键盘Enter展开末项 |
| 记录思考 | run01/review显示“演示思考·构造内容”和完整预览段落；正式采集说明使用未来接入表述 |
| 未启用思考 | run02首节点显示enable_thinking=false，无虚构该次思考 |
| 工具节点 | query_order输入/输出字段及完整原输出JSON可查看；search_knowledge参数和文档/版本/章节/依据可查看 |
| 键盘选择 | query_order时间线按钮Enter选中，aria-current=step，与详情同步 |
| 业务往返 | run01/order→业务DEMO-1001→返回关联运行节点，保留run_id=demo-run-01、step_id=order |
| 历史空结果 | 搜索不存在客户显示“没有符合筛选的运行” |
| 状态筛选与切换 | 等待业务仅出现Liam，点击后概览/节点更新为run02；恢复全部状态，Enter切回Emma/run01 |
| 邮件草稿 | 返回demo-mail-01，输入草稿→本轮运行→返回邮件，文本完全保留；验后清空测试草稿 |

CUA曾在抽屉收起过渡和滚动区末端点击时出现选择超时；重新观察、等抽屉隐藏或直接键盘Enter后可操作。没有据自动化超时推断应用错误；实际页面无错误日志。

## 宽窄与主题

| 视口 | 布局和溢出测量 |
|---|---|
| 1440×900 | 两栏；main clientHeight/scrollHeight=900/900，documentWidth=1440；面板内各自滚动 |
| 1280×900 | 两栏435.938/557.062px，documentWidth=1280，main900/900；长JSON宽/scrollWidth=507/507 |
| 800×900 | 单栏752px，documentWidth=792；长JSON宽/scrollWidth=710/710 |
| 414×896 | 单栏376px，documentWidth=406；长JSON宽/scrollWidth=342/342；历史抽屉宽414、left0、scrollWidth414 |

800/414的documentWidth比viewport少8px来自原页面滚动条；原Art侧栏折叠过渡完成后复查，无横向内容溢出。明/暗沿现有主题切换；暗色卡片背景rgb(22,22,24)、边框rgba(255,255,255,0.08)，字段和角色块仍可读。

截图位于被忽略的临时目录：

- `tmp/ui-preview/agent-redesign-desktop.png`：1440桌面、默认输入。
- `tmp/ui-preview/agent-redesign-dark-tools.png`：暗色工具参数与结果。
- `tmp/ui-preview/agent-redesign-1280.png`、`agent-redesign-800.png`、`agent-redesign-414.png`：响应式。

本轮不改变Phase11–13、模型业务质量或82项AC的完成状态。预览地址：`http://127.0.0.1:15175/#/agent-runs?run_id=demo-run-01`。
