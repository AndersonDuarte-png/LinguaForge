# Build de release Windows reproduzível (onedir, sem GGUF e sem instalador).
# Fluxo: preflight -> provision llama.cpp -> frontend -> PyInstaller -> validação.
param()

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$manifestPath = Join-Path $PSScriptRoot "llama-manifest.json"
$specPath = Join-Path $PSScriptRoot "linguaforge.spec"
$frontendDir = Join-Path $root "frontend"
$distDir = Join-Path $root "dist\LinguaForge"

function Require-Tool($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        throw "Pré-requisito ausente no PATH: $name"
    }
}

Write-Host "== preflight =="
Require-Tool "node"
Require-Tool "npm.cmd"
Require-Tool "uv"
Write-Host "preflight ok."

Write-Host "== provision llama.cpp b10978 =="
& (Join-Path $PSScriptRoot "provision.ps1") -ManifestPath $manifestPath

Write-Host "== frontend =="
Push-Location $frontendDir
try {
    npm.cmd ci
    if ($LASTEXITCODE -ne 0) { throw "npm ci falhou" }
    npm.cmd run build
    if ($LASTEXITCODE -ne 0) { throw "npm run build falhou" }
} finally {
    Pop-Location
}

Write-Host "== ambiente do projeto (uv) =="
uv sync --group desktop --group packaging --frozen
if ($LASTEXITCODE -ne 0) { throw "uv sync falhou" }

Write-Host "== PyInstaller onedir =="
$distPath = Join-Path $root "dist"
$workPath = Join-Path $root "build"
uv run --no-sync python -m PyInstaller --clean --noconfirm --distpath $distPath --workpath $workPath $specPath
if ($LASTEXITCODE -ne 0) { throw "PyInstaller falhou" }

Write-Host "== validação estrutural de dist =="
$internal = Join-Path $distDir "_internal"
$required = @(
    (Join-Path $distDir "LinguaForge.exe"),
    (Join-Path $internal "frontend\index.html"),
    (Join-Path $internal "backends\llama.cpp\b10978\win-vulkan-x64\llama-server.exe"),
    (Join-Path $internal "backends\llama.cpp\b10978\win-vulkan-x64\llama-server-impl.dll"),
    (Join-Path $internal "backends\llama.cpp\b10978\win-vulkan-x64\ggml-vulkan.dll"),
    (Join-Path $internal "backends\llama.cpp\b10978\win-cpu-x64\llama-server.exe"),
    (Join-Path $internal "backends\llama.cpp\b10978\win-cpu-x64\llama-server-impl.dll")
)
foreach ($path in $required) {
    if (-not (Test-Path $path)) {
        throw "Arquivo ausente em dist: $path"
    }
}
$gguf = Get-ChildItem $distDir -Recurse -Filter "*.gguf" -ErrorAction SilentlyContinue
if ($gguf) {
    throw "GGUF encontrado em dist (não deve ser empacotado): $($gguf.FullName)"
}
Write-Host "validação de dist ok."

Write-Host "== build concluído: $distDir =="
