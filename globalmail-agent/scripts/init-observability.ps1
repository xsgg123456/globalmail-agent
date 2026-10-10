param([ValidateRange(1024,65535)][int]$Port = 3001)
. (Join-Path $PSScriptRoot 'observability-common.ps1')
New-Item -ItemType Directory -Path $observabilityPrivateDir -Force | Out-Null
Protect-ObservabilityFile $observabilityPrivateDir -Directory
if (-not (Test-Path -LiteralPath $observabilityEnvFile)) {
    $values = [ordered]@{
        LANGFUSE_PORT = $Port
        POSTGRES_PASSWORD = (New-ObservabilitySecret)
        REDIS_AUTH = (New-ObservabilitySecret)
        CLICKHOUSE_PASSWORD = (New-ObservabilitySecret)
        MINIO_ROOT_USER = ('gm' + (New-ObservabilitySecret).Substring(0, 18))
        MINIO_ROOT_PASSWORD = (New-ObservabilitySecret)
        NEXTAUTH_SECRET = (New-ObservabilitySecret)
        SALT = (New-ObservabilitySecret)
        ENCRYPTION_KEY = (New-ObservabilitySecret)
        LANGFUSE_INIT_ORG_ID = 'globalmail-agent-local'
        LANGFUSE_INIT_ORG_NAME = 'Globalmail Local'
        LANGFUSE_INIT_PROJECT_ID = 'globalmail-agent-local'
        LANGFUSE_INIT_PROJECT_NAME = 'Globalmail Agent'
        LANGFUSE_INIT_PROJECT_PUBLIC_KEY = ('pk-lf-' + [guid]::NewGuid().ToString())
        LANGFUSE_INIT_PROJECT_SECRET_KEY = ('sk-lf-' + (New-ObservabilitySecret))
        LANGFUSE_INIT_USER_EMAIL = 'local-admin@globalmail.local'
        LANGFUSE_INIT_USER_NAME = 'Globalmail Local Admin'
        LANGFUSE_INIT_USER_PASSWORD = (New-ObservabilitySecret)
    }
    $lines = foreach ($item in $values.GetEnumerator()) { "$($item.Key)=$($item.Value)" }
    Set-Content -LiteralPath $observabilityEnvFile -Value $lines -Encoding utf8NoBOM
}
Protect-ObservabilityFile $observabilityEnvFile
$values = Get-ObservabilityEnvironment
$backendFile = Join-Path $observabilityPrivateDir 'backend.env'
@(
    'GLOBALMAIL_LANGFUSE_ENABLED=true'
    "GLOBALMAIL_LANGFUSE_BASE_URL=http://127.0.0.1:$($values.LANGFUSE_PORT)"
    "GLOBALMAIL_LANGFUSE_PUBLIC_KEY=$($values.LANGFUSE_INIT_PROJECT_PUBLIC_KEY)"
    "GLOBALMAIL_LANGFUSE_SECRET_KEY=$($values.LANGFUSE_INIT_PROJECT_SECRET_KEY)"
    "GLOBALMAIL_LANGFUSE_PROJECT_ID=$($values.LANGFUSE_INIT_PROJECT_ID)"
) | Set-Content -LiteralPath $backendFile -Encoding utf8NoBOM
Protect-ObservabilityFile $backendFile
Write-Output '观测配置已就绪；已有凭据保持原样。登录凭据位于 .local-data/observability/compose.env。'
Write-Output '后端连接配置位于 .local-data/observability/backend.env；请勿公开文件内容。'
