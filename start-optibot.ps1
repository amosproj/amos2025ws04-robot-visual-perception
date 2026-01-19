# SPDX-FileCopyrightText: 2025 robot-visual-perception
#
# SPDX-License-Identifier: MIT

# OptiBot Auto-Setup & Start Script for Windows
# Requires Administrator privileges
# Usage: PowerShell -ExecutionPolicy Bypass -File .\start-optibot.ps1

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

function Get-PyVersion($Cmd = "python") {
    try {
        $v = & $Cmd --version 2>&1
        if ($v -match "Python (\d+)\.(\d+)") { return @{Major=[int]$matches[1]; Minor=[int]$matches[2]} }
    } catch {}
    return $null
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

$RootDir = $PWD.Path

Write-Color Green "`nOptiBot - Auto-Setup & Start (Windows)`n"

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

# Install Git
if (-not (Test-Cmd "git")) { Install-Package "git" }

# Install Python 3.11
$pythonCmd = "python"
$pyOk = $false
if (Test-Cmd "python311") { $pythonCmd = "python311" }
$pyVer = Get-PyVersion $pythonCmd
if ($pyVer -and $pyVer.Major -eq 3 -and $pyVer.Minor -eq 11) { $pyOk = $true }

if (-not $pyOk) {
    Write-Color Cyan "Installing Python 3.11..."
    Install-Package "python311"
    Start-Sleep 2
    if (Test-Cmd "python311") { $pythonCmd = "python311" }
    $pyVer = Get-PyVersion $pythonCmd
    if (-not ($pyVer -and $pyVer.Major -eq 3 -and $pyVer.Minor -eq 11)) {
        Write-Color Yellow "Python installed. Restart terminal and run script again."
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
    Write-Color Cyan "Installing Node.js..."
    Install-Package "nodejs-lts"
    Start-Sleep 2
    try { $nv = node --version 2>&1; if ($nv -match "v(\d+)") { $nodeVer = [int]$matches[1] } } catch {}
    if (-not $nodeVer -or $nodeVer -lt 20) {
        Write-Color Yellow "Node.js installed. Restart terminal? (Y/N)"
        if ((Read-Host) -match "^[Yy]") {
            Start-Process powershell -Verb RunAs -ArgumentList "-ExecutionPolicy Bypass -File `"$PSCommandPath`""
            exit 0
        }
    }
}

# Install Make
if (-not (Test-Cmd "make")) { Install-Package "make" }

# Install uv
if (-not (Test-Cmd "uv")) {
    Write-Color Cyan "Installing uv..."
    & $pythonCmd -m pip install uv --quiet
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    $scriptsPath = & $pythonCmd -c "import sys, os; print(os.path.join(sys.prefix, 'Scripts'))" 2>$null
    if ($scriptsPath -and $env:Path -notlike "*$scriptsPath*") { $env:Path += ";$scriptsPath" }
}

# Run make dev
if (-not $SkipBuild) {
    Write-Color Cyan "`nRunning 'make dev'..."
    make dev
    if ($LASTEXITCODE -ne 0) { Write-Color Red "ERROR: make dev failed!"; Read-Host "Press Enter"; exit 1 }
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
`$env:VITE_BACKEND_URL='http://localhost:$BackendPort'; $Cmd
Read-Host 'Press Enter to close'
"@
    $encoded = [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($script))
    Start-Process powershell -ArgumentList "-NoExit","-EncodedCommand",$encoded
    Start-Sleep 2
}

Start-Service "Webcam (8000)" "src\backend" "uv run uvicorn streamer.main:app --host 0.0.0.0 --port 8000 --reload" "Green"
Start-Service "Analyzer ($BackendPort)" "src\backend" "uv run uvicorn analyzer.main:app --host 0.0.0.0 --port $BackendPort --reload" "Cyan"
Start-Service "Frontend (3000)" "src\frontend" "npm run dev" "Magenta"

Write-Color Green "`nServices started!"
Write-Color Yellow "Frontend: http://localhost:3000`n"

Start-Sleep 3
Start-Process "http://localhost:3000"

try { while ($true) { Start-Sleep 1 } } finally { Write-Color Yellow "Stopping..." }
