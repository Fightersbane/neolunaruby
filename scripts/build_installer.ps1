# Build the Windows installer.
#   1. stage a clean source snapshot (no venv, models, secrets or git history)
#   2. compile it with Inno Setup into dist\neolunaruby-setup-<version>.exe
#
# Requires Inno Setup 6: winget install JRSoftware.InnoSetup
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$version = (Get-Content (Join-Path $root "VERSION") -Raw).Trim()
$staging = Join-Path $root "staging"

Write-Host "==> Staging source for $version" -ForegroundColor Cyan
if (Test-Path $staging) { Remove-Item $staging -Recurse -Force }
New-Item -ItemType Directory -Path $staging | Out-Null

# Ship code and assets only. Everything else is created or downloaded on the
# user's machine: .venv, models/, .env, config.json, audio/, logs/.
$include = @(
    "app", "engine", "scripts", "installer", "assets",
    "bot.py", "requirements.txt", "VERSION", "CHANGELOG.md",
    "README.md", "LICENSE", ".env.example"
)
foreach ($item in $include) {
    $src = Join-Path $root $item
    if (Test-Path $src) { Copy-Item $src -Destination $staging -Recurse -Force }
}
Copy-Item (Join-Path $root "installer\neolunaruby.cmd") -Destination $staging -Force
Get-ChildItem $staging -Recurse -Directory -Filter "__pycache__" |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

$iscc = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
if (-not $iscc) {
    # winget installs per-user or per-machine depending on the package scope
    $guesses = @(
        "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
        "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
        "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
    )
    $iscc = $guesses | Where-Object { Test-Path $_ } | Select-Object -First 1
    if (-not $iscc) {
        throw "Inno Setup not found. Install it: winget install JRSoftware.InnoSetup"
    }
}

Write-Host "==> Compiling installer" -ForegroundColor Cyan
& $iscc "/DAppVersion=$version" (Join-Path $root "installer\neolunaruby.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed with exit code $LASTEXITCODE" }

Remove-Item $staging -Recurse -Force
$out = Join-Path $root "dist\neolunaruby-setup-$version.exe"
Write-Host "==> Built $out ($([math]::Round((Get-Item $out).Length/1MB,1)) MB)" -ForegroundColor Green
