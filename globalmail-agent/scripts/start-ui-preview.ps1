$ErrorActionPreference = 'Stop'
$repoDirectory = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$frontendDirectory = Join-Path (Split-Path $PSScriptRoot -Parent) 'frontend'
$previewRuntime = Join-Path $repoDirectory '.local-data/runtime'
New-Item -ItemType Directory -Path $previewRuntime -Force | Out-Null
if (Get-NetTCPConnection -LocalPort 15175 -State Listen -ErrorAction SilentlyContinue) {
    throw '预览端口15175已在使用，请直接打开 http://127.0.0.1:15175/#/workbench'
}
$nodeExecutable = (Get-Command node -ErrorAction Stop).Source
$savedServerEnvironment = @{}
foreach ($entry in Get-ChildItem Env: | Where-Object { $_.Name -match '^(LLM_|GLOBALMAIL_)' }) {
    $savedServerEnvironment[$entry.Name] = $entry.Value
    [Environment]::SetEnvironmentVariable($entry.Name, $null, 'Process')
}
try {
    $previewProcess = Start-Process -FilePath $nodeExecutable -ArgumentList @('node_modules/vite/bin/vite.js', '--mode', 'ui-preview') `
        -WorkingDirectory $frontendDirectory -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $previewRuntime 'ui-preview.out.log') `
        -RedirectStandardError (Join-Path $previewRuntime 'ui-preview.err.log')
    @{ pid = $previewProcess.Id; started_at = $previewProcess.StartTime.ToUniversalTime().ToString('o'); port = 15175 } |
        ConvertTo-Json | Set-Content -LiteralPath (Join-Path $previewRuntime 'ui-preview-process.json') -Encoding utf8
    Write-Output '预览已启动：http://127.0.0.1:15175/#/workbench'
} finally {
    foreach ($name in $savedServerEnvironment.Keys) {
        [Environment]::SetEnvironmentVariable($name, $savedServerEnvironment[$name], 'Process')
    }
}
