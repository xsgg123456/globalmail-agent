param([int]$ApiPort = 18186, [int]$WebPort = 15177, [switch]$ManualAgent,
    [ValidateSet(11,16)][int]$Phase = 16)
. (Join-Path $PSScriptRoot 'local-common.ps1')
$settings = Get-LocalSettings
$savedEnv = @{}
$envNames = @('GLOBALMAIL_TEST_DATABASE_URL','GLOBALMAIL_DATABASE_URL','GLOBALMAIL_OBJECT_ROOT',
    'GLOBALMAIL_ALLOWED_ORIGINS','LLM_API_KEY','LLM_MODEL','LLM_BASE_URL',
    'GLOBALMAIL_EMBEDDING_API_KEY','GLOBALMAIL_EMBEDDING_BASE_URL',
    'GLOBALMAIL_LANGFUSE_ENABLED','GLOBALMAIL_LANGFUSE_BASE_URL','GLOBALMAIL_LANGFUSE_PUBLIC_KEY',
    'GLOBALMAIL_LANGFUSE_SECRET_KEY','GLOBALMAIL_LANGFUSE_PROJECT_ID')
foreach ($name in $envNames) { $savedEnv[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
try {
    Import-BackendEnvironment $settings
    $env:GLOBALMAIL_TEST_DATABASE_URL = $env:GLOBALMAIL_DATABASE_URL
    $testArgs = @((Join-Path $PSScriptRoot 'phase3-test-server.py'), '--phase', "$Phase",
        '--api-port', "$ApiPort", '--web-port', "$WebPort")
    if ($ManualAgent) { $testArgs += '--manual-agent' }
    & (Join-Path $projectDir 'backend/.venv/Scripts/python.exe') @testArgs
    if ($LASTEXITCODE -ne 0) { throw '隔离测试服务启动或清理失败。' }
} finally {
    foreach ($name in $envNames) { [Environment]::SetEnvironmentVariable($name, $savedEnv[$name], 'Process') }
}
