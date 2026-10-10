. (Join-Path $PSScriptRoot 'observability-common.ps1')
if (-not (Test-Path -LiteralPath $observabilityEnvFile)) {
    Write-Output '本机观测配置不存在，没有需要停止的服务。'
    return
}
Invoke-ObservabilityCompose @('stop', '--timeout', '30')
Write-Output '已停止本项目观测服务；容器、卷及私有配置均保留。'
