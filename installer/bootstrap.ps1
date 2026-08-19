# First-launch bootstrap: make sure Python 3.13 and the virtual environment
# exist, then start the app. Safe to run repeatedly - it skips finished steps.
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }

# --- Python 3.13 ---------------------------------------------------------
$py = $null
try { if (& py -3.13 --version 2>$null) { $py = "py -3.13" } } catch {}
if (-not $py) {
    Write-Step "Installing Python 3.13 (one time)"
    winget install --id Python.Python.3.13 -e --accept-source-agreements --accept-package-agreements
    $env:Path = [Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [Environment]::GetEnvironmentVariable("Path", "User")
    $py = "py -3.13"
}

# --- FFmpeg --------------------------------------------------------------
if (-not (Get-Command ffmpeg -ErrorAction SilentlyContinue)) {
    Write-Step "Installing FFmpeg (one time)"
    winget install --id Gyan.FFmpeg -e --accept-source-agreements --accept-package-agreements
}

# --- virtual environment -------------------------------------------------
$venvPy = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
    Write-Step "Creating the Python environment"
    Invoke-Expression "$py -m venv `"$root\.venv`""
}

$marker = Join-Path $root ".venv\.deps-installed"
$reqHash = (Get-FileHash (Join-Path $root "requirements.txt") -Algorithm SHA256).Hash
if (-not (Test-Path $marker) -or (Get-Content $marker -Raw).Trim() -ne $reqHash) {
    Write-Step "Installing dependencies - this takes a few minutes and about 5 GB"
    & $venvPy -m pip install --upgrade pip
    & $venvPy -m pip install -r (Join-Path $root "requirements.txt") `
        --extra-index-url https://download.pytorch.org/whl/cu128
    # kokoro-onnx pulls plain onnxruntime, which shadows the GPU build
    & $venvPy -m pip uninstall -y onnxruntime
    & $venvPy -m pip install --force-reinstall --no-deps onnxruntime-gpu==1.23.2
    Set-Content $marker $reqHash -Encoding utf8
}

Write-Step "Starting neolunaruby"
& $venvPy -m app.main
