param(
    [ValidateRange(1024,65535)][int]$ApiPort = 18080,
    [ValidateRange(1024,65535)][int]$FrontendPort = 15173,
    [ValidateRange(1024,65535)][int]$PostgresPort = 15432
)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$runtimeDir = Join-Path $repoRoot '.local-data/runtime'
$settingsFile = Join-Path $runtimeDir 'settings.json'
if (Test-Path -LiteralPath $settingsFile) {
    Write-Output '本机配置已存在，保留原密码及端口。'
    return
}
if (@($ApiPort,$FrontendPort,$PostgresPort | Sort-Object -Unique).Count -ne 3) {
    throw 'API、前端、数据库端口不能重复。'
}
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
$randomBytes = [byte[]]::new(32)
[Security.Cryptography.RandomNumberGenerator]::Fill($randomBytes)
$databasePassword = [Convert]::ToHexString($randomBytes).ToLowerInvariant()
$settings = @{
    api_port = $ApiPort; frontend_port = $FrontendPort; postgres_port = $PostgresPort
    database_url = "postgresql+psycopg://globalmail:${databasePassword}@127.0.0.1:${PostgresPort}/globalmail"
    object_root = (Join-Path $repoRoot '.local-data/objects')
    allowed_origins = "http://127.0.0.1:$FrontendPort,http://localhost:$FrontendPort"
}
$settings | ConvertTo-Json | Set-Content -LiteralPath $settingsFile -Encoding utf8
@("GLOBALMAIL_POSTGRES_PASSWORD=$databasePassword", "GLOBALMAIL_POSTGRES_PORT=$PostgresPort") |
    Set-Content -LiteralPath (Join-Path $runtimeDir 'compose.env') -Encoding utf8
Write-Output '已生成本项目本机配置；密码仅保存在忽略目录 .local-data/runtime。'
