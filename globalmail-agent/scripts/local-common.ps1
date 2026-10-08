$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtimeDir = Join-Path $repoRoot '.local-data/runtime'
$projectDir = Join-Path $repoRoot 'globalmail-agent'
$composeFile = Join-Path $projectDir 'infra/compose.yaml'
$composeEnv = Join-Path $runtimeDir 'compose.env'
$stateFile = Join-Path $runtimeDir 'processes.json'

function Get-LocalSettings {
    $path = Join-Path $runtimeDir 'settings.json'
    if (-not (Test-Path -LiteralPath $path)) { & (Join-Path $PSScriptRoot 'init-local.ps1') }
    return Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
}

function Assert-FreePort([int]$Port) {
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
    try { $listener.Start() }
    catch { throw "端口 $Port 已被占用。请先停止占用服务；本脚本不会终止其他程序。" }
    finally { $listener.Stop() }
}

function Invoke-LocalCompose([string[]]$ComposeArgs) {
    & docker compose --project-name globalmail-agent --env-file $composeEnv -f $composeFile @ComposeArgs
    if ($LASTEXITCODE -ne 0) { throw '本项目数据库操作失败；未修改其他Compose项目。' }
}

function Import-BackendEnvironment($Settings) {
    $env:GLOBALMAIL_DATABASE_URL = $Settings.database_url
    $env:GLOBALMAIL_OBJECT_ROOT = $Settings.object_root
    $env:GLOBALMAIL_ALLOWED_ORIGINS = $Settings.allowed_origins
    # Only these server-side values may be imported; never dot-source an env file.
    $envFile = Join-Path $repoRoot '.env'
    if (Test-Path -LiteralPath $envFile) {
        foreach ($line in Get-Content -LiteralPath $envFile) {
            if ($line -match '^(LLM_MODEL|LLM_BASE_URL|LLM_API_KEY|GLOBALMAIL_EMBEDDING_API_KEY|GLOBALMAIL_EMBEDDING_BASE_URL)=(.*)$') {
                [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim().Trim('"').Trim("'"), 'Process')
            }
        }
    }
}

function Start-LocalProcess([string]$Name, [string]$Executable, [string[]]$Arguments, [string]$Directory) {
    $quoted = $Arguments | ForEach-Object { '"' + $_.Replace('"', '\"') + '"' }
    $process = Start-Process -FilePath $Executable -ArgumentList $quoted -WorkingDirectory $Directory `
        -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $runtimeDir "$Name.out.log") `
        -RedirectStandardError (Join-Path $runtimeDir "$Name.err.log")
    return @{ name=$Name; pid=$process.Id; started_at=$process.StartTime.ToUniversalTime().ToString('o') }
}

function Stop-OwnedProcess($Entry) {
    $process = Get-Process -Id $Entry.pid -ErrorAction SilentlyContinue
    # PowerShell 7.5 decodes ISO JSON values as DateTime; compare instants, not display strings.
    $recorded = if ($Entry.started_at -is [datetime]) { $Entry.started_at.ToUniversalTime() } else {
        [datetime]::Parse($Entry.started_at, [Globalization.CultureInfo]::InvariantCulture,
            [Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()
    }
    if ($process -and $process.StartTime.ToUniversalTime().Ticks -eq $recorded.Ticks) {
        & taskkill /PID $Entry.pid /T /F | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "停止本项目 $($Entry.name) 进程失败。" }
    }
}
