. (Join-Path $PSScriptRoot 'observability-common.ps1')
$values = Get-ObservabilityEnvironment
$baseUrl = "http://127.0.0.1:$($values.LANGFUSE_PORT)"
$authText = "$($values.LANGFUSE_INIT_PROJECT_PUBLIC_KEY):$($values.LANGFUSE_INIT_PROJECT_SECRET_KEY)"
$auth = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($authText))
$headers = @{ Authorization = "Basic $auth" }
$traceId = [guid]::NewGuid().ToString('N')
$fromTime = [Uri]::EscapeDataString((Get-Date).ToUniversalTime().AddMinutes(-5).ToString('o'))
$toTime = [Uri]::EscapeDataString((Get-Date).ToUniversalTime().AddMinutes(5).ToString('o'))
$python = Join-Path $observabilityRepoRoot 'globalmail-agent/backend/.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $python)) { throw '停启追踪测试需要已安装 Langfuse SDK4 的后端虚拟环境。' }
& $python (Join-Path $PSScriptRoot 'observability-smoke.py') $observabilityEnvFile $traceId
if ($LASTEXITCODE -ne 0) { throw 'SDK4 合成追踪写入失败。' }

function Wait-ObservabilitySmokeTrace {
    for ($attempt = 0; $attempt -lt 25; $attempt++) {
        $response = Invoke-WebRequest -Uri "$baseUrl/api/public/v2/observations?traceId=$traceId&fromStartTime=$fromTime&toStartTime=$toTime&fields=core,basic&limit=10" `
            -Headers $headers -TimeoutSec 10 -SkipHttpErrorCheck
        if ($response.StatusCode -eq 200) {
            $observations = $response.Content | ConvertFrom-Json
            if (@($observations.data | Where-Object { $_.traceId -eq $traceId -and
                    $_.name -eq 'observability-retention-smoke' }).Count -gt 0) { return }
        } elseif ($response.StatusCode -ne 404) {
            throw "观测读回请求失败，HTTP $($response.StatusCode)。"
        }
        Start-Sleep -Seconds 2
    }
    throw '合成追踪在规定时间内未可读。'
}

Wait-ObservabilitySmokeTrace
$beforeConfig = (Get-FileHash -LiteralPath $observabilityEnvFile).Hash
$backendFile = Join-Path $observabilityPrivateDir 'backend.env'
$beforeBackend = (Get-FileHash -LiteralPath $backendFile).Hash
$beforeVolumes = @(& docker volume ls --filter "label=com.docker.compose.project=$observabilityProject" --format '{{.Name}}' | Sort-Object)
$businessBefore = & docker inspect --format '{{.Id}} {{.State.StartedAt}}' globalmail-agent-postgres-1
if ($LASTEXITCODE -ne 0) { throw '业务 PostgreSQL 基准容器不存在，无法验证未被重启。' }
& (Join-Path $PSScriptRoot 'init-observability.ps1')
if ($beforeConfig -ne (Get-FileHash -LiteralPath $observabilityEnvFile).Hash -or
        $beforeBackend -ne (Get-FileHash -LiteralPath $backendFile).Hash) { throw '重复初始化改变了配置。' }
try {
    & (Join-Path $PSScriptRoot 'stop-observability.ps1')
    & (Join-Path $PSScriptRoot 'start-observability.ps1')
    Wait-ObservabilitySmokeTrace
} finally {
    # A failed test must still leave the user's service running with retained volumes.
    Invoke-ObservabilityCompose @('up', '-d')
}
$afterVolumes = @(& docker volume ls --filter "label=com.docker.compose.project=$observabilityProject" --format '{{.Name}}' | Sort-Object)
$businessAfter = & docker inspect --format '{{.Id}} {{.State.StartedAt}}' globalmail-agent-postgres-1
if ($LASTEXITCODE -ne 0) { throw '业务 PostgreSQL 基准容器在验证后不可读。' }
if (($beforeVolumes -join '|') -ne ($afterVolumes -join '|') -or $beforeVolumes.Count -ne 5) {
    throw '停启后观测卷不一致。'
}
if ($businessBefore -ne $businessAfter) { throw '业务 PostgreSQL 在观测停启测试中变化。' }
Write-Output "PASS: credentials unchanged; 5 volumes retained; trace $traceId readable after restart; business PostgreSQL unchanged"
