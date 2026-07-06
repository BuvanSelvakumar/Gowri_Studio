# Gowri Studio - Windows one-click setup & launcher.
# First run: installs Python 3.12 (if needed), creates the environment, installs
# dependencies, then starts the app. Every run after that just launches it.

$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
Set-Location $PSScriptRoot

$venvPy = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

function Find-Python {
    try { & py -3.12 --version *> $null; if ($LASTEXITCODE -eq 0) { return "launcher" } } catch {}
    foreach ($c in @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe"
    )) { if (Test-Path $c) { return $c } }
    return $null
}

if (-not (Test-Path $venvPy)) {
    $py = Find-Python
    if (-not $py) {
        Write-Host "Installing Python 3.12 (one-time)..." -ForegroundColor Yellow
        $url  = "https://www.python.org/ftp/python/3.12.7/python-3.12.7-amd64.exe"
        $inst = Join-Path $env:TEMP "python-3.12.7-amd64.exe"
        Invoke-WebRequest -Uri $url -OutFile $inst -UseBasicParsing
        Write-Host "Running the Python installer silently (this can take a minute)..."
        Start-Process -FilePath $inst -ArgumentList `
            "/quiet","InstallAllUsers=0","PrependPath=1","Include_test=0","Include_launcher=1" -Wait
        $py = Find-Python
    }
    if (-not $py) {
        Write-Host "Could not set up Python automatically." -ForegroundColor Red
        Write-Host "Please install Python 3.12 from https://www.python.org/downloads/ (tick 'Add Python to PATH'), then run this again."
        Read-Host "Press Enter to close"
        exit 1
    }

    Write-Host "Creating the app environment..." -ForegroundColor Yellow
    if ($py -eq "launcher") { & py -3.12 -m venv .venv } else { & $py -m venv .venv }

    Write-Host "Installing dependencies (a few minutes, one-time)..." -ForegroundColor Yellow
    & $venvPy -m pip install --upgrade pip
    & $venvPy -m pip install -r requirements.txt
}

Write-Host "Starting Gowri Studio..." -ForegroundColor Green
& $venvPy run_app.py
