param([string]$LatestJournalRoot)
. (Join-Path $PSScriptRoot 'local-common.ps1')
$settings = Get-LocalSettings
Import-BackendEnvironment $settings
$python = Join-Path $projectDir 'backend/.venv/Scripts/python.exe'
$env:PYTHONPATH = Join-Path $projectDir 'backend/src'
$replayArgs = @('-m', 'globalmail_agent.application.replay_journal')
if ($LatestJournalRoot) { $replayArgs += @('--journal-root', $LatestJournalRoot) }
# Run only after stopping API/workers; active connections or leases are refused.
& $python @replayArgs
if ($LASTEXITCODE -ne 0) { throw '日志重放失败；停止API和worker，核查最新日志和删除状态后重试。恢复门已关闭时保持封闭。' }
