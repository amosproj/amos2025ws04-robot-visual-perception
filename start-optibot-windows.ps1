# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

# OptiBot Auto-Setup & Start Script for Windows (patched)
# Requires Administrator privileges
# Usage: PowerShell -ExecutionPolicy Bypass -File .\start-optibot-windows.ps1

#Requires -RunAsAdministrator

param(
    [int]$CameraIndex = 0,
    [int]$CameraWidth = 1280,
    [int]$CameraHeight = 720,
    [int]$CameraFPS = 30,
    [int]$BackendPort = 8001,
    [switch]$SkipBuild = $false
)

function Write-Color($Color, $Message) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $Color
    Write-Output $Message
    $host.UI.RawUI.ForegroundColor = $fc
}

function Test-Cmd($Command) {
    try { $null = Get-Command $Command -ErrorAction Stop; return $true } catch { return $false }
}

function Install-Choco {
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
    Invoke-Expression ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

function Install-Package($Name) {
    choco install $Name -y --no-progress | Out-Null
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}

function Enable-RefreshEnv {
    try {
        if ($env:ChocolateyInstall -and (Test-Path "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1")) {
            Import-Module "$env:ChocolateyInstall\helpers\chocolateyProfile.psm1" -ErrorAction SilentlyContinue | Out-Null
            if (Get-Command refreshenv -ErrorAction SilentlyContinue) { refreshenv | Out-Null }
        }
    } catch {}
}

function Test-Py311 {
    # Most reliable on Windows: Python Launcher
    try {
        if (-not (Test-Cmd "py")) { return $false }
        $out = & py -3.11 --version 2>&1
        return ($out -match "Python 3\.11")
    } catch { return $false }
}

function Select-PythonCmd {
    # Prefer python311.exe if it exists; otherwise use py -3.11; otherwise fallback python
    if (Test-Cmd "python311") { return "python311" }
    if (Test-Py311) { return "py -3.11" }
    if (Test-Cmd "python") { return "python" }
    return $null
}

$RootDir = $PWD.Path

Write-Color Green "`nOptiBot - Auto-Setup & Start (Windows) [patched]`n"

# Check admin rights
if (-not (New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
    Write-Color Red "ERROR: Run as Administrator!"; Read-Host "Press Enter"; exit 1
}

# Check project structure
if (-not (Test-Path "src/backend") -or -not (Test-Path "src/frontend")) {
    Write-Color Red "ERROR: Run from project root!"; Read-Host "Press Enter"; exit 1
}

# Install Chocolatey
if (-not (Test-Cmd "choco")) {
    Write-Color Cyan "Installing Chocolatey..."
    Install-Choco
    if (-not (Test-Cmd "choco")) { Write-Color Red "ERROR: Chocolatey install failed!"; Read-Host "Press Enter"; exit 1 }
}
Enable-RefreshEnv

# Install Git
if (-not (Test-Cmd "git")) { Install-Package "git" ; Enable-RefreshEnv }

# Ensure Git's Unix tools available (helps Makefiles that call pwd, etc.)
$gitUsrBin = "C:\Program Files\Git\usr\bin"
$gitBin    = "C:\Program Files\Git\bin"
if (Test-Path $gitUsrBin) {
    $machinePath = [System.Environment]::GetEnvironmentVariable("Path","Machine")
    if ($machinePath -notlike "*$gitUsrBin*") {
        [System.Environment]::SetEnvironmentVariable("Path", "$machinePath;$gitBin;$gitUsrBin", "Machine")
    }
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
}
Enable-RefreshEnv

# Install Python 3.11 (and/or ensure py -3.11 works)
$pythonCmd = Select-PythonCmd
$pyOk = $false
if ($pythonCmd) {
    try {
        $v = & $pythonCmd --version 2>&1
        if ($v -match "Python 3\.11") { $pyOk = $true }
    } catch {}
}

if (-not $pyOk) {
    Write-Color Cyan "Installing Python 3.11..."
    Install-Package "python311"
    Enable-RefreshEnv
    Start-Sleep 2

    # Re-check using py -3.11 (preferred)
    if (Test-Py311) {
        $pythonCmd = "py -3.11"
        $pyOk = $true
    } else {
        $pythonCmd = Select-PythonCmd
        try {
            $v = & $pythonCmd --version 2>&1
            if ($v -match "Python 3\.11") { $pyOk = $true }
        } catch {}
    }

    if (-not $pyOk) {
        Write-Color Yellow "Python 3.11 installed but not detected. Close and reopen PowerShell (Admin), then run this script again."
        Read-Host "Press Enter"; exit 0
    }
}

$env:PYTHON_CMD = $pythonCmd

# Install Node.js 20+
$nodeVer = $null
try {
    $nv = node --version 2>&1
    if ($nv -match "v(\d+)") { $nodeVer = [int]$matches[1] }
} catch {}

if (-not $nodeVer -or $nodeVer -lt 20) {
    Write-Color Cyan "Installing Node.js (LTS)..."
    Install-Package "nodejs-lts"
    Enable-RefreshEnv
    Start-Sleep 2
    try { $nv = node --version 2>&1; if ($nv -match "v(\d+)") { $nodeVer = [int]$matches[1] } } catch {}
    if (-not $nodeVer -or $nodeVer -lt 20) {
        Write-Color Yellow "Node.js installed, but may require a new terminal session. Close/reopen PowerShell (Admin) and run again."
        Read-Host "Press Enter"; exit 0
    }
}

# Install Make
if (-not (Test-Cmd "make")) { Install-Package "make" ; Enable-RefreshEnv }

# Install uv (prefer winget; fallback pip for py3.11)
if (-not (Test-Cmd "uv")) {
    if (Test-Cmd "winget") {
        Write-Color Cyan "Installing uv via winget..."
        try {
            winget install --id AstralSoftware.uv -e --accept-source-agreements --accept-package-agreements | Out-Null
            Enable-RefreshEnv
        } catch {}
    }

    if (-not (Test-Cmd "uv")) {
        Write-Color Cyan "Installing uv via pip (Python 3.11)..."
        & $pythonCmd -m pip install --user uv --quiet
        $userScripts = Join-Path $env:APPDATA "Python\Python311\Scripts"
        if (Test-Path $userScripts -and $env:Path -notlike "*$userScripts*") { $env:Path += ";$userScripts" }
    }
}

if (-not (Test-Cmd "uv")) {
    Write-Color Red "ERROR: uv is still not available on PATH. Close/reopen PowerShell (Admin) and try again."
    Read-Host "Press Enter"; exit 1
}

# Avoid OneDrive hardlink issues (os error 396)
$env:UV_LINK_MODE = "copy"

# Run make dev
if (-not $SkipBuild) {
    Write-Color Cyan "`nRunning 'make dev'..."
    make dev
    if ($LASTEXITCODE -ne 0) {
        Write-Color Red "ERROR: make dev failed!"
        Read-Host "Press Enter"; exit 1
    }
}

# Set environment
$env:CAMERA_INDEX = $CameraIndex
$env:CAMERA_WIDTH = $CameraWidth
$env:CAMERA_HEIGHT = $CameraHeight
$env:CAMERA_FPS = $CameraFPS
$env:WEBCAM_OFFER_URL = "http://localhost:8000/offer"
$env:VITE_BACKEND_URL = "http://localhost:$BackendPort"

Write-Color Cyan "`nConfig: Camera=$CameraIndex ${CameraWidth}x${CameraHeight}@${CameraFPS}fps, Backend=$BackendPort`n"

# Start services
function Start-Service($Title, $Dir, $Cmd, $Color) {
    $script = @"
`$Host.UI.RawUI.WindowTitle='$Title'; `$Host.UI.RawUI.ForegroundColor='$Color'; Clear-Host
Write-Host '$Title' -ForegroundColor $Color; Set-Location '$RootDir\$Dir'
`$env:CAMERA_INDEX='$CameraIndex'; `$env:CAMERA_WIDTH='$CameraWidth'; `$env:CAMERA_HEIGHT='$CameraHeight'
`$env:CAMERA_FPS='$CameraFPS'; `$env:WEBCAM_OFFER_URL='http://localhost:8000/offer'
`$env:VITE_BACKEND_URL='http://localhost:$BackendPort'
`$env:PYTHON_CMD='$pythonCmd'
`$env:UV_LINK_MODE='copy'
$Cmd
Read-Host 'Press Enter to close'
"@
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($script))
    Start-Process powershell -ArgumentList "-NoExit","-EncodedCommand",$encoded
    Start-Sleep 2
}

Start-Service "Webcam (8000)"   "src\backend"  "uv run uvicorn webcam.main:app --host 0.0.0.0 --port 8000 --reload"  "Green"
Start-Service "Analyzer ($BackendPort)" "src\backend" "uv run uvicorn analyzer.main:app --host 0.0.0.0 --port $BackendPort --reload" "Cyan"
Start-Service "Frontend (3000)" "src\frontend" "npm run dev" "Magenta"

Write-Color Green "`nServices started!"
Write-Color Yellow "Frontend: http://localhost:3000`n"

Start-Sleep 2
Start-Process "http://localhost:3000"

try { while ($true) { Start-Sleep 1 } } finally { Write-Color Yellow "Stopping..." }
