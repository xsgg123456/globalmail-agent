. (Join-Path $PSScriptRoot 'observability-common.ps1')
$values = Get-ObservabilityEnvironment
$baseUrl = "http://127.0.0.1:$($values.LANGFUSE_PORT)"
$lockFile = Join-Path $observabilityRepoRoot 'globalmail-agent/infra/observability-images.lock.json'
$imageLock = Get-Content -LiteralPath $lockFile -Raw | ConvertFrom-Json
$containerIds = @(Invoke-ObservabilityCompose @('ps', '-q'))
if ($containerIds.Count -ne 6) { throw '观测容器数量不是预期的六个。' }
foreach ($containerId in $containerIds) {
    $service = & docker inspect --format '{{index .Config.Labels "com.docker.compose.service"}}' $containerId
    $project = & docker inspect --format '{{index .Config.Labels "com.docker.compose.project"}}' $containerId
    $health = & docker inspect --format '{{.State.Health.Status}}' $containerId
    $image = & docker inspect --format '{{.Config.Image}}' $containerId
    $locked = ($imageLock.images | Where-Object { $_.service -eq $service }).image
    if ($project -ne $observabilityProject -or $health -ne 'healthy' -or $image -ne $locked) {
        throw "观测服务 $service 项目隔离、健康或镜像锁验证失败。"
    }
    $ports = & docker port $containerId
    if ($service -eq 'langfuse-web') {
        if ($ports -ne "3000/tcp -> 127.0.0.1:$($values.LANGFUSE_PORT)") { throw '观测入口不是指定本机端口。' }
    } elseif ($ports) { throw "内部服务 $service 暴露了宿主机端口。" }
    $mounts = & docker inspect --format '{{json .Mounts}}' $containerId | ConvertFrom-Json
    foreach ($mount in $mounts) {
        if ($mount.Type -eq 'volume' -and -not $mount.Name.StartsWith("${observabilityProject}_")) {
            throw "服务 $service 使用了其他项目的数据卷。"
        }
    }
    if ($service -in @('langfuse-web', 'langfuse-worker')) {
        & docker exec $containerId node -e "process.exit(process.env.TELEMETRY_ENABLED==='false' && process.env.NEXT_TELEMETRY_DISABLED==='1' && !process.env.NEXT_PUBLIC_LANGFUSE_CLOUD_REGION ? 0 : 1)"
        if ($LASTEXITCODE -ne 0) { throw "服务 $service 遥测或 Cloud 配置验证失败。" }
    }
    Write-Output "$service healthy; image locked; project isolated"
}
$health = Invoke-RestMethod -Uri "$baseUrl/api/public/health" -TimeoutSec 10
if ($health.status -ne 'OK') { throw 'Langfuse HTTP 健康检查失败。' }
$authText = "$($values.LANGFUSE_INIT_PROJECT_PUBLIC_KEY):$($values.LANGFUSE_INIT_PROJECT_SECRET_KEY)"
$auth = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($authText))
$projects = Invoke-RestMethod -Uri "$baseUrl/api/public/projects" -Headers @{ Authorization = "Basic $auth" } -TimeoutSec 10
if (@($projects.data | Where-Object { $_.id -eq $values.LANGFUSE_INIT_PROJECT_ID }).Count -ne 1) {
    throw '初始项目或项目 API 凭据验证失败。'
}
$unauthorized = Invoke-WebRequest -Uri "$baseUrl/api/public/projects" -TimeoutSec 10 -SkipHttpErrorCheck
if ($unauthorized.StatusCode -ne 401) { throw '无凭据请求未被拒绝。' }
$csrf = Invoke-RestMethod -Uri "$baseUrl/api/auth/csrf" -SessionVariable loginSession -TimeoutSec 10
$login = Invoke-RestMethod -Uri "$baseUrl/api/auth/callback/credentials" -Method Post `
    -WebSession $loginSession -ContentType 'application/x-www-form-urlencoded' -TimeoutSec 15 -Body @{
        csrfToken = $csrf.csrfToken; email = $values.LANGFUSE_INIT_USER_EMAIL
        password = $values.LANGFUSE_INIT_USER_PASSWORD; callbackUrl = $baseUrl; json = 'true'
    }
$session = Invoke-RestMethod -Uri "$baseUrl/api/auth/session" -WebSession $loginSession -TimeoutSec 10
if ($session.user.email -ne $values.LANGFUSE_INIT_USER_EMAIL) { throw '本机 UI 账号登录验证失败。' }
Write-Output "HTTP health OK; authenticated project $($values.LANGFUSE_INIT_PROJECT_ID); anonymous rejected (401); UI login OK"
