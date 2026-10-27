# Windows x64 only. Repository-local official runtime; no PATH or registry changes.
$ErrorActionPreference = 'Stop'
$phase1Root = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../../..'))
$phase1Runtime = Join-Path $phase1Root '.tools/p117-python31216'
$phase1Python = Join-Path $phase1Runtime 'python/python.exe'
if (-not (Test-Path -LiteralPath $phase1Python)) {
    if (Test-Path -LiteralPath $phase1Runtime) { throw 'Incomplete runtime exists; inspect it before retrying.' }
    $phase1Asset = 'cpython-3.12.16+20261026-x86_64-pc-windows-msvc-install_only_stripped.tar.gz'
    $phase1Url = 'https://github.com/astral-sh/python-build-standalone/releases/download/20261026/'
    $phase1Artifacts = Join-Path $phase1Root '.artifacts/p1-17-python-bootstrap'
    New-Item -ItemType Directory -Force -Path $phase1Artifacts | Out-Null
    $phase1Archive = Join-Path $phase1Artifacts $phase1Asset
    Invoke-WebRequest -Uri ($phase1Url + $phase1Asset) -OutFile $phase1Archive -TimeoutSec 90
    $phase1Hash = (Get-FileHash -LiteralPath $phase1Archive -Algorithm SHA256).Hash
    # Frozen against the official release SHA256SUMS during P1-17 acceptance.
    if ($phase1Hash -ne '1f2ab53880fc67ea323398c6388e05af28addc99a8e389209f08a51fdff4b149') {
        throw 'Python archive SHA256 mismatch; no extraction performed.'
    }
    New-Item -ItemType Directory -Path $phase1Runtime | Out-Null
    tar -xzf $phase1Archive -C $phase1Runtime
    if ($LASTEXITCODE -ne 0) { throw 'Python archive extraction failed.' }
}
$phase1Version = & $phase1Python --version
if ($LASTEXITCODE -ne 0 -or $phase1Version -ne 'Python 3.12.16') { throw 'Unexpected Python runtime.' }
Write-Output $phase1Python
