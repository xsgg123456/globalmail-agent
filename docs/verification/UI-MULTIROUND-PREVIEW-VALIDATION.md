# 多轮会话运行预览验证

日期：2026-10-09。验收来源：[实施规划](../planning/UI-PREVIEW-IMPLEMENTATION.md)的多轮迭代四步；此前首次预览和重设计报告保留历史结论。本轮仍限15175隔离前端，用户要求不Git提交。

## 结果与边界

全局选会话、会话内选轮次、轮内选节点已实现。Emma三封客户来信和一次发货回执形成四轮；第2/3/4轮模型上下文分别冻结邮件seq1–3、1–5、1–6，不包含未来消息。当前会话状态与历史轮结果分开显示，历史输入/输出不随当前业务账本改写。

实验室新来信在内存生成下一轮和演示确认回复；人工接管或结案仅登记来信。查看旧轮/节点时保留选择并提示最新轮。邮件历史入口恢复已看轮，最新入口明确去最新；指定触发邮件可以定位，普通返回保留阅读位置/草稿。关联业务保留run/step回跳。

提示词、思考和回复明确为演示构造，不调用真实AI、发真实邮件或写正式DB。预览API返回404；正式15173/18080继续运行。后端逐次观测、正式解耦和Phase11–13/82项AC不由本轮关闭。

fresh独立审查Stage 1/2均PASS，无待修HIGH/MEDIUM；报告为[本轮独审](UI-MULTIROUND-PREVIEW-REVIEW.md)，明确区分独审实测与主Agent证据复核。

## 工程验证

| 验证 | 实际结果 | 原始证据 |
|---|---|---|
| 前端测试 | 70 pass / 0 fail / 0 skip，2744.7447ms；原64项+新增6项 | `.local-data/runtime/ui-rounds-tests.log` |
| 正常模式编译 | vue-tsc零错误，Vite26.70秒，退出0 | `.local-data/runtime/ui-rounds-normal-build.log` |
| 预览模式编译 | vue-tsc零错误，Vite18.09秒，退出0 | `.local-data/runtime/ui-rounds-preview-build.log` |
| 本轮源码ESLint | 退出0，日志为空 | `.local-data/runtime/ui-rounds-eslint.log` |
| 文件边界 | 16个本轮程序文件，最大260行；diff --check退出0 | `.local-data/runtime/ui-rounds-source-manifest.json` |
| Git限制 | 索引为空，未暂存/提交 | `git diff --cached --name-only` |
| 实际页面日志 | 主Agent测试tab warning/error均为空 | CUA tab.dev.logs |

新增6项验证：初始轮关联、历史快照截点/不可变、会话隔离和新轮保留选择、连续来信/退款节点时序、人工/结案及空输入屏障、退款下一轮/幂等/重置。独审独立重跑6项通过，342.8005ms；区别于主Agent全量70项。

首轮新增测试误将核验节点的候选回复也当成未来邮件，产生68 pass/1 fail；原日志`ui-rounds-tests-initial.log`保留。修正断言为来信理解不含候选回复、所有上下文不含尚未提交的回复ID，仍保留历史邮件截点验证。未修改程序来迎合错误断言。

修复两项本轮发现：独审发现旧业务页排除DEMO-1001导致Emma补发回执漏显示，已按bug-fixer修正列表并实际复验；主Agent检查发现秒数为30的新轮节点会早于启动，改为总秒递增并由新增连续来信/退款测试验证，独审独立复核关闭。首次ESLint文件路径拼错未执行检查，改正确components路径后最终退出0。

## 实际浏览器交互

| 路径或状态 | 实测证据 |
|---|---|
| 默认与切换 | Emma默认第4轮，切第3轮显示等待业务而当前会话仍等待客户；Enter可选轮，aria-current=true及焦点边框可见 |
| 原始输入 | 第3轮完整请求含邮件seq1–5，不含DEMO-SHIP-01；思考分演示构造/未启用，原始JSON可展开 |
| 指定触发邮件 | 第3轮→第5封客户邮件，文章顶部与容器顶部差16.25px；独审另测15.5px |
| 历史保留 | 第2轮stock→实验室追加来信→返回，仍第2轮stock，出现第5轮及更新提示；新轮不抢选择 |
| 最新入口 | 邮件“查看最新运行”明确跳新生成第5轮；“全部N轮”恢复已浏览历史轮 |
| 跨页保存 | 主Agent草稿文字完全保留；独审另外实测阅读scrollTop579→579 |
| 关联业务 | 第2轮stock→业务→原节点；修复后售后页显示DEMO-1001/OP-01/SHIP-01/TRACK-01，第4轮review可往返 |
| 会话抽屉 | 不存在词显示空态；LIAM仅匹配Liam，Enter切换到该会话；状态筛选生效 |
| 人工与重置 | 独审实际接管Liam后只登记来信、不生成run/回复；退款回执不自动跟进；确认重置恢复Emma3封来信/4轮 |

抽屉过渡或长滚动区点击时CUA曾超时；重新观察、等关闭或使用Enter后可达，未把工具点击超时当成应用异常。主Agent曾用hash导航尝试重置，但这只导航不清内存，随后明确reload恢复初始；不影响新轮跨页保留的验收。

## 主题与响应式

| 视口 | 布局及溢出测量 |
|---|---|
| 1440×1000 | documentWidth1440，轮卡272.25px×4，双栏502.672/642.328px；main client1000/scroll1001 |
| 1280×900 | documentWidth1280，轮卡232.25px×4，双栏432.438/552.562px，长JSON client/scroll503/503 |
| 800×900 | documentWidth792，轮卡350px×2，单栏752px，长JSON710/710 |
| 414×896 | documentWidth406，轮卡162px×2，单栏376px，长JSON342/342；卡client/scroll160/160；抽屉width414/scroll414/left0 |

800/414宽度差8px来自既有滚动条，无文档横向溢出；窄屏标题换行，节点详情转单栏。明/暗沿用原Art主题，暗色选中轮卡背景rgb(9,13,25)、边框rgb(46,67,127)、白字可读。独审实开五张截图，并另在自己1280宽页面验证无横向溢出。

截图保存在忽略目录`tmp/ui-preview/`：`multiround-desktop.png`、`multiround-1280.png`、`multiround-800.png`、`multiround-414.png`、`multiround-dark.png`。全部为实际页面截图。

预览地址：`http://127.0.0.1:15175/#/agent-runs?conversation_id=demo-mail-01`。刷新会重置演示内存；无新服务或依赖。
