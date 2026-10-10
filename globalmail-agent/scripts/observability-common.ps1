$ErrorActionPreference = 'Stop'
$observabilityRepoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$observabilityPrivateDir = Join-Path $observabilityRepoRoot '.local-data/observability'
$observabilityComposeFile = Join-Path $observabilityRepoRoot 'globalmail-agent/infra/compose.observability.yaml'
$observabilityEnvFile = Join-Path $observabilityPrivateDir 'compose.env'
$observabilityProject = 'globalmail-agent-observability'

function New-ObservabilitySecret {
    $bytes = [byte[]]::new(32)
    [Security.Cryptography.RandomNumberGenerator]::Fill($bytes)
    return [Convert]::ToHexString($bytes).ToLowerInvariant()
}

function Protect-ObservabilityFile([string]$Path, [switch]$Directory) {
    # Build only the discretionary ACL; preserve owner/SACL without requesting SeSecurityPrivilege.
    $acl = if ($Directory) { [Security.AccessControl.DirectorySecurity]::new() }
        else { [Security.AccessControl.FileSecurity]::new() }
    $acl.SetAccessRuleProtection($true, $false)
    $owner = [Security.Principal.WindowsIdentity]::GetCurrent().User
    foreach ($sid in @($owner, [Security.Principal.SecurityIdentifier]::new('S-1-5-18'),
            [Security.Principal.SecurityIdentifier]::new('S-1-5-32-544'))) {
        $rule = if ($Directory) {
            [Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl',
                'ContainerInherit, ObjectInherit', 'None', 'Allow')
        } else { [Security.AccessControl.FileSystemAccessRule]::new($sid, 'FullControl', 'Allow') }
        $acl.AddAccessRule($rule)
    }
    if ($Directory) { [IO.FileSystemAclExtensions]::SetAccessControl([IO.DirectoryInfo]::new($Path), $acl) }
    else { [IO.FileSystemAclExtensions]::SetAccessControl([IO.FileInfo]::new($Path), $acl) }
}

function Get-ObservabilityEnvironment {
    if (-not (Test-Path -LiteralPath $observabilityEnvFile)) {
        throw '观测私有配置不存在；先运行 init-observability.ps1。'
    }
    $values = @{}
    foreach ($line in Get-Content -LiteralPath $observabilityEnvFile) {
        if ($line -match '^([A-Z][A-Z0-9_]*)=([^\r\n]*)$') { $values[$Matches[1]] = $Matches[2] }
        elseif ($line.Trim() -and -not $line.StartsWith('#')) { throw '观测私有配置格式不合法。' }
    }
    foreach ($key in @('LANGFUSE_PORT', 'POSTGRES_PASSWORD', 'REDIS_AUTH', 'CLICKHOUSE_PASSWORD',
            'MINIO_ROOT_USER', 'MINIO_ROOT_PASSWORD', 'NEXTAUTH_SECRET', 'SALT', 'ENCRYPTION_KEY',
            'LANGFUSE_INIT_PROJECT_ID', 'LANGFUSE_INIT_PROJECT_PUBLIC_KEY',
            'LANGFUSE_INIT_PROJECT_SECRET_KEY', 'LANGFUSE_INIT_USER_EMAIL', 'LANGFUSE_INIT_USER_PASSWORD')) {
        if (-not $values[$key]) { throw "观测配置缺少 $key；不会自动替换已有凭据。" }
    }
    return $values
}

function Invoke-ObservabilityCompose([string[]]$ComposeArgs) {
    & docker compose --project-name $observabilityProject --env-file $observabilityEnvFile `
        -f $observabilityComposeFile @ComposeArgs
    if ($LASTEXITCODE -ne 0) { throw '本项目观测 Compose 操作失败。' }
}

function Assert-ObservabilityPort([int]$Port) {
    $owned = Invoke-ObservabilityCompose @('ps', '--status', 'running', '-q', 'langfuse-web')
    if ($owned) {
        $binding = & docker port $owned 3000/tcp
        if ($LASTEXITCODE -eq 0 -and $binding -eq "127.0.0.1:$Port") { return }
    }
    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, $Port)
    try { $listener.Start() }
    catch { throw "本机端口 $Port 已被占用；不会停止其他程序。" }
    finally { $listener.Stop() }
}
