param([switch]$StopDatabase)
. (Join-Path $PSScriptRoot 'local-common.ps1')
if (Test-Path -LiteralPath $stateFile) {
    foreach ($entry in (Get-Content -LiteralPath $stateFile -Raw | ConvertFrom-Json)) {
        Stop-OwnedProcess $entry
    }
    '[]' | Set-Content -LiteralPath $stateFile -Encoding utf8
}
if ($StopDatabase) { Invoke-LocalCompose @('stop','postgres') }
Write-Output '本项目服务已停止；数据库卷、对象及配置均保留。'
