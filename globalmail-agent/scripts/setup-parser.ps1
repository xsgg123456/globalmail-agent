param([switch]$DownloadModels, [switch]$Standard)
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$parserDir = Join-Path $repoRoot 'globalmail-agent/parser-worker'
Get-Command uv -ErrorAction Stop | Out-Null
Push-Location $parserDir
try {
    & uv sync --frozen
    if ($LASTEXITCODE -ne 0) { throw '独立解析环境安装失败。' }
    $parserPython = Join-Path $parserDir '.venv/Scripts/python.exe'
    if ($DownloadModels) {
        $previousHome = $env:MINERU_HOME
        try {
            if ($env:GLOBALMAIL_PARSER_HOME) { $env:MINERU_HOME = $env:GLOBALMAIL_PARSER_HOME }
            elseif (Test-Path -LiteralPath (Join-Path $repoRoot 'tmp/knowledge-spike/mineru-home')) {
                $env:MINERU_HOME = Join-Path $repoRoot 'tmp/knowledge-spike/mineru-home'
            } else { $env:MINERU_HOME = Join-Path $repoRoot '.local-data/parser-models' }
            $tier = if ($Standard) { 'standard' } else { 'basic' }
            $arguments = @('models','download','--tier',$tier,'--small-backend','onnx','--source','modelscope')
            if ($Standard) { $arguments += @('--vlm-engine','llama-cpp') }
            & (Join-Path $parserDir '.venv/Scripts/mineru-kit.exe') @arguments
            if ($LASTEXITCODE -ne 0) { throw '解析模型下载失败。' }
        } finally { $env:MINERU_HOME = $previousHome }
    }
    & $parserPython check_models.py --profile $(if ($Standard) { 'mineru_standard' } else { 'mineru_basic' })
    if ($LASTEXITCODE -ne 0) { throw '模型缺失或摘要不匹配。首次安装请加 -DownloadModels；已有模型请核对 parser-worker/model-assets.json。' }
    & uv pip check --python $parserPython
    if ($LASTEXITCODE -ne 0) { throw '解析依赖兼容检查失败。' }
} finally { Pop-Location }
