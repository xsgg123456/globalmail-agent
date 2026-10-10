# Phase 12 隔离 GUI 验收

2026-10-10。结论：本报告所列真实 API/浏览器生命周期路径通过；不代表本期全部工程验收或模型语义验收。使用 dev-builder 与 playwright skill，独立 Chromium `phase12` 会话；没有启动模型 worker、没有付费模型调用。

## 环境与版本边界

实际启动命令（仓库根目录）：

```powershell
pwsh -File globalmail-agent/scripts/start-workbench-test.ps1 -Phase 12 -ManualAgent -ApiPort 18189 -WebPort 15179
npx --yes --package @playwright/cli playwright-cli -s=phase12 open http://127.0.0.1:15179/#/workbench --headed
```

首轮 schema `phase12_browser_e5c743efc42e4bdd80809948da00e1ba`，完成预览/取消/共享原件场景后，通过 `tmp/phase12-browser.stop` 交原 launcher 清理，退出0并输出 `Isolated processes/schema/object directory cleaned.`。在主线程告知后端冻结后，全新启动最终 schema `phase12_browser_ca1031205ca740bc9046e3b824b16c42`；session 为 `tmp/globalmail_phase12_browser_r0kfaxmr/session.json`，对象和独立生命周期日志都在该临时目录。API 18189、前端15179，没有操作正式18080/15173、观测3001或旧预览15175。

**版本限制：最终服务加载后，主线程又修复了 `lifecycle_inventory.py` 的共享知识来源持有者边界和 `lifecycle_replay.py` 的已处理 withdraw 重放边界。该服务加载的是这两处修复前版本，本 GUI 不声称覆盖修复后的后台行为。主线程负责相应后台回归及最终独审；UI源码未变。**

验收模式 `create_app(..., start_worker=False)`，因此确认后正常进入 revoked，本报告显式调用本隔离实例的 `POST /api/v1/lifecycle/requests/{id}/retry` 推进真实清理；没有以轮询假装后台 worker 工作。模型只显示已配置，不调用。

## 实测结果

| 场景 | 真实行为与证据 |
|---|---|
| 会话预览与取消 | 显示2文件、1运行、1会话。最终取消前后80张表逐行SHA完全相同，`cancel_database_unchanged=True`；[前SHA](artifacts/phase12/cancel-before-db-hashes.json)、[后SHA](artifacts/phase12/cancel-after-db-hashes.json)、[结果](artifacts/phase12/cancel-db-result.txt)。首轮[预览截图](artifacts/phase12/conversation-preview.png)。 |
| 会话确认、草稿和旧页面 | 确认后列表目标、正文、草稿输入立即消失，DOM及localStorage哨兵全部false；[撤销DOM](artifacts/phase12/final-revoked-dom.txt)。真实清理返回completed，[API结果](artifacts/phase12/final-conversation-completed.json)、[截图](artifacts/phase12/final-conversation-completed.png)。再次打开旧会话URL后仍无哨兵，[旧页DOM](artifacts/phase12/final-old-page-dom.txt)、[快照](artifacts/phase12/final-old-page-snapshot.txt)。 |
| 知识删除 | 草稿资料底部危险入口，预览与取消不关资料正文；确认后详情清空、列表移除，API retry真实completed。最终[结果](artifacts/phase12/knowledge-completed.json)、[页面](artifacts/phase12/knowledge-completed.png)、[快照](artifacts/phase12/knowledge-completed-snapshot.txt)。首轮[预览](artifacts/phase12/knowledge-preview.png)。 |
| 图片删除 | 上传400×300纯合成PNG并绑定合成来信，Drawer内独立危险入口。预览取消后原图仍可见，确认后原图/缩略图清除、显示已移除；会话仍保留。最终[结果](artifacts/phase12/image-completed.json)、[页面](artifacts/phase12/image-completed.png)、[快照](artifacts/phase12/image-completed-snapshot.txt)。 |
| 共享PDF阻断 | 两份资料通过正常API引用同一真实PDF上传对象；预览列关联资料ID，确认后实际清理返回blocked_dependencies。最终从History点击重试仍blocked，未误报完成；[状态](artifacts/phase12/final-shared-blocked.json)、[History截图](artifacts/phase12/history-blocked-retry.png)、[快照](artifacts/phase12/history-blocked-retry-snapshot.txt)。 |
| 清理失败后History重试成功 | 新合成会话确认删除后，用生产writer_barrier在隔离schema持有共享锁，再调真实retry，返回cleanup_failed / writer_inflight；[真实故障](artifacts/phase12/cleanup-failed-real-lock.json)。释放锁后在History实际点击重试，返回completed；[失败页](artifacts/phase12/history-cleanup-failed.png)、[成功页](artifacts/phase12/history-retry-completed.png)、[真实GET](artifacts/phase12/history-retry-completed.json)。没有改数据库状态来伪造失败。 |
| 读取错误 | Playwright仅拦截生命周期记录GET返回503，History显示明确错误及刷新按钮，旧记录仍保留；[720截图](artifacts/phase12/history-get-error-720.png)、[快照](artifacts/phase12/history-get-error-snapshot.txt)。已unroute恢复。这是读取错误UI注入，不作为真实数据库故障证明。 |
| 失效资源读回 | 删除会话、资料和资料原件404；删除图片和共享原件410；保留图片所属会话200；列表与历史200。[实际API读回](artifacts/phase12/final-api-readback.json)。 |
| 布局 | 实际查看1440、720宽截图，危险操作与主操作分离，确认按钮/关联ID/错误说明未溢出；1440时document.scrollWidth=1440，History Drawer为x900/w540/h1000。720时[History截图](artifacts/phase12/history-720.png)文字换行、按钮可见。 |

网络证据：[请求记录](artifacts/phase12/final-browser-requests.txt)、[console错误](artifacts/phase12/browser-errors.txt)。本轮4条错误为主动注入的GET503与旧会话/建议404；未观察到Vue渲染异常。

## 命令与限制

取消DB哈希、合成样本、故障持锁、API读回脚本仅位于本轮tmp：`phase12-gui-db-hashes.py before/after`、`phase12-gui-seed.py`、`phase12-shared-seed.py`、`phase12-gui-cleanup-fault.py`、`phase12-final-readback.py`。使用 `globalmail-agent/backend/.venv/Scripts/python.exe` 执行，结果如上；只读私有连接配置，没有输出连接串或凭据。

QA入口只增加Phase12参数和明确临时journal路径/环境恢复；没有修改产品实现。实际运行 `python -m py_compile globalmail-agent/scripts/phase3-test-server.py globalmail-agent/scripts/phase7_browser_app.py` 退出0；`git diff --check -- globalmail-agent/scripts/phase3-test-server.py globalmail-agent/scripts/start-workbench-test.ps1` 退出0，仅CRLF提示。

未覆盖：真实模型输出与图像语义、远端Langfuse实际删除、后台自动调度、联合备份恢复、跨进程完整并发、两处后续后台修复；这些由主线程专项验证和独审记录承担。本轮仅用合成内容，没有已外发副本或正式业务资料。

## 清理状态

首轮隔离进程/schema/对象已清理。最终实例按主线程要求保留给fresh reviewer，尚未清理；收尾由主线程通知后通过既有stop文件完成。本报告不提前声明最终服务清理完成。

私有API按PID重启脚本写入曾被自动审批拒绝，返回 `blocked by policy`；未执行该脚本。随后使用已有launcher的stop文件完成更安全的全新实例重启，未阻塞本次验收。
