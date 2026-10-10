param(
    [Parameter(Mandatory=$true)][string]$Backup,
    [Parameter(Mandatory=$true)][string]$NewObjectRoot,
    [Parameter(Mandatory=$true)][string]$LatestJournalRoot
)
. (Join-Path $PSScriptRoot 'local-common.ps1')
$settings = Get-LocalSettings
Import-BackendEnvironment $settings
$python = Join-Path $projectDir 'backend/.venv/Scripts/python.exe'
$env:PYTHONPATH = Join-Path $projectDir 'backend/src'
& $python -m globalmail_agent.application.backup_cli restore --path $Backup --object-root $NewObjectRoot --journal-root $LatestJournalRoot
if ($LASTEXITCODE -ne 0) { throw '恢复未通过验收，隔离目标保持封闭；正式配置未切换。' }
