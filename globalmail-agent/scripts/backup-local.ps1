param([Parameter(Mandatory=$true)][string]$Destination)
. (Join-Path $PSScriptRoot 'local-common.ps1')
$settings = Get-LocalSettings
Import-BackendEnvironment $settings
$python = Join-Path $projectDir 'backend/.venv/Scripts/python.exe'
$env:PYTHONPATH = Join-Path $projectDir 'backend/src'
# Stop API/workers beforehand; the service rejects any remaining DB client or running job.
& $python -m globalmail_agent.application.backup_cli backup --path $Destination
if ($LASTEXITCODE -ne 0) { throw '联合备份未完成；停止本项目API和worker后检查错误再重试。' }
