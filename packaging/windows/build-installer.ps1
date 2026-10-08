# Gera o instalador Windows a partir da dist onedir já validada (rodar build.ps1 antes).
# Não baixa/instala Inno Setup; falha com mensagem clara se ISCC.exe não existir.
param()

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$dist = Join-Path $root "dist\LinguaForge"
$iss = Join-Path $PSScriptRoot "linguaforge.iss"

Write-Host "== valida dist =="
$requiredDist = @(
    (Join-Path $dist "LinguaForge.exe"),
    (Join-Path $dist "_internal\frontend\index.html"),
    (Join-Path $dist "_internal\backends\llama.cpp\b10978\win-vulkan-x64\llama-server.exe"),
    (Join-Path $dist "_internal\backends\llama.cpp\b10978\win-cpu-x64\llama-server.exe")
)
foreach ($path in $requiredDist) {
    if (-not (Test-Path $path)) { throw "dist inválida (rode build.ps1 antes): $path" }
}
Write-Host "dist ok."

Write-Host "== versao (pyproject.toml) =="
$pyproject = Get-Content (Join-Path $root "pyproject.toml") -Raw
$version = [regex]::Match($pyproject, '(?m)^version\s*=\s*"([^"]+)"').Groups[1].Value
if (-not $version) { throw "Versão não encontrada no pyproject.toml." }
Write-Host "versao: $version"

Write-Host "== localiza ISCC.exe =="
$iscc = $null
$candidates = @(
    (Join-Path $env:ProgramFiles "Inno Setup 6\ISCC.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe"),
    (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe")
)
foreach ($candidate in $candidates) {
    if (Test-Path $candidate) { $iscc = $candidate; break }
}
if (-not $iscc) {
    $cmd = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($cmd) { $iscc = $cmd.Source }
}
if (-not $iscc) {
    throw "Inno Setup (ISCC.exe) não encontrado. Instale o Inno Setup 6 e execute novamente."
}
Write-Host "ISCC: $iscc"

Write-Host "== compila instalador =="
& $iscc "/DAppVersion=$version" $iss
if ($LASTEXITCODE -ne 0) { throw "ISCC falhou (exit=$LASTEXITCODE)." }

$output = Join-Path $root "installer\LinguaForge-$version-Setup.exe"
if (-not (Test-Path $output)) { throw "Instalador não foi gerado em $output" }
Write-Host "== instalador gerado: $output =="
