param([switch]$SkipInstall)
. (Join-Path $PSScriptRoot 'local-common.ps1')
$settings = Get-LocalSettings
$backendDir = Join-Path $projectDir 'backend'
$frontendDir = Join-Path $projectDir 'frontend'
$owned = @()
$savedEnv = @{}
$envNames = @('GLOBALMAIL_DATABASE_URL','GLOBALMAIL_OBJECT_ROOT','GLOBALMAIL_ALLOWED_ORIGINS',
    'LLM_API_KEY','LLM_MODEL','LLM_BASE_URL','GLOBALMAIL_EMBEDDING_API_KEY',
    'GLOBALMAIL_EMBEDDING_BASE_URL','VITE_PORT','VITE_API_PROXY_URL',
    'GLOBALMAIL_LANGFUSE_ENABLED','GLOBALMAIL_LANGFUSE_BASE_URL','GLOBALMAIL_LANGFUSE_PUBLIC_KEY',
    'GLOBALMAIL_LANGFUSE_SECRET_KEY','GLOBALMAIL_LANGFUSE_PROJECT_ID')
foreach ($name in $envNames) { $savedEnv[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
try {
    foreach ($tool in @('docker','uv','node','pnpm')) { Get-Command $tool -ErrorAction Stop | Out-Null }
    Assert-FreePort $settings.api_port
    Assert-FreePort $settings.frontend_port
    $runningDb = & docker compose --project-name globalmail-agent --env-file $composeEnv -f $composeFile ps --status running -q postgres
    if ($LASTEXITCODE -ne 0) { throw '无法连接Docker，请启动Docker Desktop。' }
    if (-not $runningDb) { Assert-FreePort $settings.postgres_port }
    Invoke-LocalCompose @('up','-d','--wait')
    if (-not $SkipInstall) {
        Push-Location $backendDir
        try { & uv sync --frozen; if ($LASTEXITCODE -ne 0) { throw '后端锁文件安装失败。' } }
        finally { Pop-Location }
        Push-Location (Join-Path $projectDir 'parser-worker')
        try { & uv sync --frozen; if ($LASTEXITCODE -ne 0) { throw '独立解析锁文件安装失败。' } }
        finally { Pop-Location }
        Push-Location $frontendDir
        try { & pnpm install --frozen-lockfile --ignore-scripts; if ($LASTEXITCODE -ne 0) { throw '前端锁文件安装失败。' } }
        finally { Pop-Location }
    }
    Import-BackendEnvironment $settings
    $python = Join-Path $backendDir '.venv/Scripts/python.exe'
    if (-not (Test-Path -LiteralPath $python)) { throw '缺少后端环境，请去掉-SkipInstall重试。' }
    Push-Location $backendDir
    try { & $python -m alembic upgrade head; if ($LASTEXITCODE -ne 0) { throw '数据库迁移失败。' } }
    finally { Pop-Location }
    $owned += Start-LocalProcess 'api' $python @('-m','uvicorn','--app-dir','src','globalmail_agent.main:app',
        '--host','127.0.0.1','--port',"$($settings.api_port)",'--no-access-log') $backendDir
    # The frontend child must not inherit backend/model credentials.
    foreach ($name in @('GLOBALMAIL_DATABASE_URL','LLM_API_KEY','LLM_MODEL','LLM_BASE_URL',
        'GLOBALMAIL_EMBEDDING_API_KEY','GLOBALMAIL_EMBEDDING_BASE_URL',
        'GLOBALMAIL_LANGFUSE_ENABLED','GLOBALMAIL_LANGFUSE_BASE_URL','GLOBALMAIL_LANGFUSE_PUBLIC_KEY',
        'GLOBALMAIL_LANGFUSE_SECRET_KEY','GLOBALMAIL_LANGFUSE_PROJECT_ID')) {
        [Environment]::SetEnvironmentVariable($name, $null, 'Process')
    }
    $env:VITE_PORT = "$($settings.frontend_port)"
    $env:VITE_API_PROXY_URL = "http://127.0.0.1:$($settings.api_port)"
    $vite = Join-Path $frontendDir 'node_modules/vite/bin/vite.js'
    if (-not (Test-Path -LiteralPath $vite)) { throw '缺少前端依赖，请去掉-SkipInstall重试。' }
    $owned += Start-LocalProcess 'frontend' (Get-Command node).Source @($vite,'--host','127.0.0.1',
        '--port',"$($settings.frontend_port)",'--strictPort') $frontendDir
    $owned | ConvertTo-Json -AsArray | Set-Content -LiteralPath $stateFile -Encoding utf8
    $ready = $false
    for ($attempt = 0; $attempt -lt 45; $attempt++) {
        try {
            $api = Invoke-RestMethod "http://127.0.0.1:$($settings.api_port)/api/v1/health/ready" -TimeoutSec 2
            $web = Invoke-WebRequest "http://127.0.0.1:$($settings.frontend_port)" -TimeoutSec 2
            if ($api.data.status -eq 'ready' -and $web.StatusCode -eq 200) { $ready = $true; break }
        } catch { }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw '服务未就绪；检查 .local-data/runtime/*.err.log（不要公开凭据）。' }
    Write-Output "页面：http://127.0.0.1:$($settings.frontend_port)"
    Write-Output "API：http://127.0.0.1:$($settings.api_port)/api/v1/health/ready"
    Write-Output '停止：pwsh -File globalmail-agent/scripts/stop-local.ps1（保留数据）'
} catch {
    foreach ($entry in $owned) { Stop-OwnedProcess $entry }
    throw
} finally {
    foreach ($name in $envNames) { [Environment]::SetEnvironmentVariable($name, $savedEnv[$name], 'Process') }
}
