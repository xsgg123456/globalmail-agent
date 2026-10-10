# 删除、重置与恢复操作

适用本机 Phase12 / 数据库0012_lifecycle。正式服务默认前端15173、API18080。删除范围是本项目管理的副本，外部源包、提供商留存、已外发内容及离线备份另行处置。

## 删除与重试

邮件详情、知识详情及图片查看抽屉分别提供“彻底删除”。先读取影响范围，取消不修改数据。确认后立即停止使用相关内容；只有状态“删除完成”才代表本项目的物理清理与核验通过。页面的“删除记录”可刷新状态和重试失败请求。

共享PDF可能包含其他资料仍引用的内容。此时保持“共享内容阻止删除”，显示关联资料ID，共享原件禁止下载。当前没有自动分离PDF历史版本的功能；仅上传其他资料的新版本不能解除旧版本的依赖，不能以“下架”代替完整删除。

运行中的模型调用、解析或导出尚未退出时，清理可能返回 `writer_inflight`。退出后再重试；追踪服务未确认删除时同样不报告完成。普通下架/图片撤销保留停用历史内容，“彻底删除”才清理正文。无正文的业务发生记录和防重标识保留。

附件或知识删除会同时清空受影响会话的旧草稿、建议及运行内容缓存，同源其他标签页也会失效。清理完成后，剩余会话可重新点击“人工接管”建立空白人审并继续回复；无关会话草稿保留。断线期间漏收通知时，刷新会按服务端删除水位重新核对。

## 模拟分支重置（仅API）

重置沿用同一影响确认与清理链路，只有simulation会话可用。先读取当前版本，确认该会话就是要清空的测试分支，再调用：

```powershell
$conversationId = '<要重置的模拟会话ID>'
$api = 'http://127.0.0.1:18080/api/v1/lifecycle'
$impact = Invoke-RestMethod "$api/conversation/$conversationId/impact"
$command = @{ expected_version=$impact.data.expected_version; action='reset' } | ConvertTo-Json
$request = Invoke-RestMethod "$api/conversation/$conversationId" -Method Post `
  -Headers @{Origin='http://127.0.0.1:15173'} -ContentType 'application/json' -Body $command
Invoke-RestMethod "$api/requests/$($request.data.id)"
```

完成后返回独立的 `new_conversation_id`；旧分支不复用，重试不重复创建。此操作不改源准备包或其他分支，没有页面测试按钮。

## 联合备份

先停止本项目API和前端，保留数据库及观测服务。确认没有运行任务；若上次异常终止留下任务，先正常启动让租约恢复处理完成，再停机备份。

```powershell
pwsh -File globalmail-agent/scripts/stop-local.ps1
pwsh -File globalmail-agent/scripts/backup-local.ps1 -Destination '<新的本地备份目录>'
pwsh -File globalmail-agent/scripts/start-local.ps1 -SkipInstall
```

备份包括数据库归档、注册对象、配置清单/摘要和签名水位。密钥只保存是否配置及摘要，实际凭据须独立保管。未完成目录有 `INCOMPLETE` 标记，不作为可恢复备份。目的目录必须新建，不能覆盖已有备份。

删除日志位于配置的 `lifecycle_journal_root`，默认是对象目录旁的 `<对象目录名>-lifecycle`。它必须独立保留**最新**版本，不能随旧备份一并回滚或删除；日志密钥与水位也要保留。

## 恢复旧备份

```powershell
pwsh -File globalmail-agent/scripts/restore-local.ps1 `
  -Backup '<联合备份目录>' -NewObjectRoot '<全新对象目录>' `
  -LatestJournalRoot '<最新独立日志目录>'
```

恢复只创建全新数据库和全新对象目录，正式配置不自动切换。目标先封闭，重放最新删除/撤销、核验完整回执、合法索引、对象和任务写门后才标记verified。原任务停用，后续需显式重试。已经应用过的普通下架不覆盖备份内后来的合法重新发布。

成功输出新数据库及旁置配置清单路径。该清单不是完整的本机运行设置替代品：切换时保留既有端口及独立凭据配置，并使用返回的新数据库、对象及日志路径。脚本不会自动替用户切换正式实例。当前CLI还使用原数据库回执作为最新日志的第二份水位证明；原数据库完全不可用时会保守拒绝，未提供跳过该证明的灾难恢复流程。

## 删除日志已写、数据库事务未提交时

服务显示 `restore_closed`，不会启动业务worker或开放正文读取。先停本项目服务，再运行：

```powershell
pwsh -File globalmail-agent/scripts/stop-local.ps1
pwsh -File globalmail-agent/scripts/replay-journal-local.ps1
pwsh -File globalmail-agent/scripts/start-local.ps1 -SkipInstall
```

重放要求无其他数据库客户端；未到期的任务/slot租约仍拒绝，需要等租约过期后重试。过期且离线的遗留任务会被停用，然后补齐删除与回执。远端追踪未确认清除、共享内容阻断、对象不完整或日志损坏时保持封闭，不手工删除门控标记来绕过检查。
