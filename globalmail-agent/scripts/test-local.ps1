. (Join-Path $PSScriptRoot 'local-common.ps1')
$settings = Get-LocalSettings
$settingsFile = Join-Path $runtimeDir 'settings.json'
$before = (Get-FileHash -LiteralPath $settingsFile).Hash
& (Join-Path $PSScriptRoot 'init-local.ps1') -ApiPort 18081
if ((Get-FileHash -LiteralPath $settingsFile).Hash -ne $before) { throw '重复初始化覆盖了配置。' }
Write-Output 'PASS 重复初始化保留凭据'
$listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
$listener.Start()
try {
    $blocked = $false
    try { Assert-FreePort $listener.LocalEndpoint.Port } catch { $blocked = $_.Exception.Message -like '*已被占用*' }
    if (-not $blocked) { throw '未发现端口冲突。' }
    Write-Output 'PASS 端口冲突明确拒绝'
} finally { $listener.Stop() }

$testRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot ('tmp/local-script-test-' + [guid]::NewGuid().ToString('N'))))
$allowedRoot = [IO.Path]::GetFullPath((Join-Path $repoRoot 'tmp')) + [IO.Path]::DirectorySeparatorChar
if (-not $testRoot.StartsWith($allowedRoot, [StringComparison]::OrdinalIgnoreCase)) { throw '测试路径越界。' }
New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
$runtimeDir = $testRoot
$entry = $null
try {
    $entry = Start-LocalProcess 'test' (Get-Command node).Source @('-e', 'setInterval(() => {}, 1000)') $testRoot
    $fake = @{pid=$entry.pid;name='test';started_at='1900-01-01T00:00:00Z'}
    Stop-OwnedProcess $fake
    if (-not (Get-Process -Id $entry.pid -ErrorAction SilentlyContinue)) { throw '错误创建时间仍杀进程。' }
    $restored = $entry | ConvertTo-Json | ConvertFrom-Json
    Stop-OwnedProcess $restored
    Start-Sleep -Milliseconds 200
    if (Get-Process -Id $entry.pid -ErrorAction SilentlyContinue) { throw '本项目进程未停止。' }
    Write-Output 'PASS 进程创建时间校验、JSON登记往返及停止'
} finally {
    if ($entry) { Stop-OwnedProcess $entry }
    if ([IO.Path]::GetFullPath($testRoot).StartsWith($allowedRoot, [StringComparison]::OrdinalIgnoreCase)) {
        Remove-Item -LiteralPath $testRoot -Recurse -Force
    }
}
