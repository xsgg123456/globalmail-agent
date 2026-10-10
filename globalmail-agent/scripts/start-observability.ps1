. (Join-Path $PSScriptRoot 'observability-common.ps1')
& (Join-Path $PSScriptRoot 'init-observability.ps1')
$values = Get-ObservabilityEnvironment
Assert-ObservabilityPort ([int]$values.LANGFUSE_PORT)
Invoke-ObservabilityCompose @('up', '-d', '--wait', '--wait-timeout', '300')
& (Join-Path $PSScriptRoot 'test-observability.ps1')
Write-Output "本机 Langfuse 已启动：http://127.0.0.1:$($values.LANGFUSE_PORT)"
