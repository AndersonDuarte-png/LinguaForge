# Provisiona os backends llama.cpp b10978 para o build Windows (somente ambiente de build).
# Não altera PATH global, não exige admin e não faz download em runtime do aplicativo.
# Idempotente: se os arquivos já estiverem presentes e íntegros, não baixa novamente.
param(
    [string]$ManifestPath = (Join-Path $PSScriptRoot "llama-manifest.json")
)

$ErrorActionPreference = "Stop"

$root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json

function Get-Sha256($path) {
    (Get-FileHash -Path $path -Algorithm SHA256).Hash.ToLowerInvariant()
}

function Test-Provisioned($extractTo, $requiredFiles) {
    $sentinel = Join-Path $extractTo ".provisioned"
    if (-not (Test-Path $sentinel)) { return $false }
    foreach ($file in $requiredFiles) {
        $full = Join-Path $extractTo $file
        if (-not (Test-Path $full)) { return $false }
    }
    # Sentinel guarda hashes dos arquivos-chave para detectar conteúdo corrompido.
    try {
        $recorded = Get-Content $sentinel -Raw | ConvertFrom-Json
    } catch {
        return $false
    }
    foreach ($file in $recorded.PSObject.Properties) {
        $full = Join-Path $extractTo $file.Name
        if ((Get-Sha256 $full) -ne $file.Value) { return $false }
    }
    return $true
}

foreach ($key in @("cpu", "vulkan")) {
    $asset = $manifest.assets.$key
    if ($null -eq $asset -or -not $asset.name -or -not $asset.url -or -not $asset.sha256 -or -not $asset.extract_to) {
        throw "Manifesto inválido: asset '$key' sem campos obrigatórios."
    }
    $extractTo = Join-Path $root $asset.extract_to
    $allowedRoot = (Join-Path $root "data\llama.cpp") + "\"
    if (-not $extractTo.StartsWith($allowedRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Destino de extração fora de data/llama.cpp: $extractTo"
    }
    $required = $asset.required_files

    Write-Host "[provision] $key : $($asset.name)"

    if (Test-Provisioned $extractTo $required) {
        Write-Host "[provision] $key : ja provisionado e integro (ignorando download)."
        continue
    }

    $zip = Join-Path ([System.IO.Path]::GetTempPath()) $asset.name
    Write-Host "[provision] $key : baixando $($asset.url)"
    Invoke-WebRequest -Uri $asset.url -OutFile $zip -UseBasicParsing

    $actual = Get-Sha256 $zip
    $expected = $asset.sha256.ToLowerInvariant()
    if ($actual -ne $expected) {
        Remove-Item $zip -Force -ErrorAction SilentlyContinue
        throw "SHA256 do asset $($asset.name) nao confere: esperado $expected, obtido $actual"
    }
    Write-Host "[provision] $key : SHA256 verificado ($actual)"

    $staging = Join-Path ([System.IO.Path]::GetTempPath()) ("lf-provision-" + [guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Force -Path $staging | Out-Null
    try {
        Expand-Archive -Path $zip -DestinationPath $staging -Force
    } finally {
        Remove-Item $zip -Force -ErrorAction SilentlyContinue
    }

    # Só após download+hash verificados, limpa estado parcial e prepara o destino.
    if (Test-Path $extractTo) {
        Remove-Item $extractTo -Recurse -Force
    }
    New-Item -ItemType Directory -Force -Path $extractTo | Out-Null

    try {
        # Move o conteúdo extraído para o destino (os zips são flat, sem subpasta raiz).
        Get-ChildItem $staging -File | ForEach-Object { Move-Item $_.FullName $extractTo -Force }
    } finally {
        Remove-Item $staging -Recurse -Force -ErrorAction SilentlyContinue
    }

    # Verifica arquivos obrigatórios após a extração.
    foreach ($file in $required) {
        if (-not (Test-Path (Join-Path $extractTo $file))) {
            throw "Arquivo obrigatorio ausente apos extracao: $extractTo\$file"
        }
    }

    # Grava sentinel com hashes dos arquivos-chave para detecção de corrupção futura.
    $hashes = @{}
    foreach ($file in $required) {
        $hashes[$file] = Get-Sha256 (Join-Path $extractTo $file)
    }
    ($hashes | ConvertTo-Json) | Set-Content -Path (Join-Path $extractTo ".provisioned") -Encoding utf8

    Write-Host "[provision] $key : ok (provisionado em $extractTo)"
}

Write-Host "[provision] concluido."
