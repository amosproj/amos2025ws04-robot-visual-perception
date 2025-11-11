# start-optibot.ps1 - CLEAN ASCII VERSION
# Automatisches Start-Skript fuer OptiBot auf Windows
# - Erkennt/erstellt venv im Backend
# - Installiert Abhaengigkeiten fuer Backend/Frontend (falls noetig)
# Aufruf:
#   PowerShell -ExecutionPolicy Bypass -File .\start-optibot.ps1

param(
    [int]$CameraIndex = 0,
    [int]$CameraWidth = 1280,
    [int]$CameraHeight = 720,
    [int]$CameraFPS = 30,
    [int]$BackendPort = 8001
)

function Pause-PS {
    Read-Host -Prompt "Press Enter to continue..."
}

# Farbausgabe
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) { Write-Output $args }
    $host.UI.RawUI.ForegroundColor = $fc
}

$RootDir = $PWD.Path

Write-ColorOutput Green "=================================================="
Write-ColorOutput Green "  OptiBot - Windows Starter"
Write-ColorOutput Green "  T-Systems Project - AMOS 2025"
Write-ColorOutput Green "=================================================="
Write-Output ""

# Verzeichnisstruktur pruefen
if (-not (Test-Path "src/backend") -or -not (Test-Path "src/frontend")) {
    Write-ColorOutput Red "ERROR: src/backend oder src/frontend wurde nicht gefunden."
    Write-ColorOutput Yellow "Fuehre das Skript im Projekt-Root aus. Aktuelles Verzeichnis: $PWD"
    Pause-PS
    exit 1
}

# Python pruefen
Write-ColorOutput Cyan "Pruefe Python..."
try {
    $pythonVersion = (python --version 2>&1)
    Write-ColorOutput Green "OK: $pythonVersion"
} catch {
    Write-ColorOutput Red "ERROR: Python nicht gefunden."
    Write-ColorOutput Yellow "Installiere Python 3.11+ von https://www.python.org/downloads/ und aktiviere 'Add to PATH'."
    Pause-PS
    exit 1
}

# Node.js pruefen
Write-ColorOutput Cyan "Pruefe Node.js..."
try {
    $nodeVersion = (node --version 2>&1)
    Write-ColorOutput Green "OK: Node.js $nodeVersion"
} catch {
    Write-ColorOutput Red "ERROR: Node.js nicht gefunden."
    Write-ColorOutput Yellow "Installiere Node.js 18+ von https://nodejs.org/"
    Pause-PS
    exit 1
}

# venv testen
function Test-VirtualEnvironment {
    param([string]$VenvPath)

    if (-not (Test-Path $VenvPath)) { return $false }
    $pythonExe = Join-Path $VenvPath "Scripts\python.exe"
    if (-not (Test-Path $pythonExe)) { return $false }
    try {
        & $pythonExe --version *> $null
        if ($LASTEXITCODE -eq 0) { return $true }
    } catch { return $false }
    return $false
}

# Backend venv pruefen/erstellen
Write-ColorOutput Cyan "Pruefe Backend Virtual Environment..."
$venvPath = "src\backend\venv"

if (Test-Path $venvPath) {
    Write-ColorOutput Yellow "venv gefunden, teste..."
    if (Test-VirtualEnvironment -VenvPath $venvPath) {
        Write-ColorOutput Green "OK: venv ist funktionsfaehig."
    } else {
        Write-ColorOutput Yellow "Hinweis: venv scheint defekt/inkompatibel. Erstelle neu."
        try {
            Remove-Item -Recurse -Force $venvPath -ErrorAction Stop
            Write-ColorOutput Green "Altes venv geloescht."
        } catch {
            Write-ColorOutput Red "ERROR beim Loeschen von $venvPath : $_"
            Pause-PS
            exit 1
        }
        Write-ColorOutput Cyan "Erstelle neues venv..."
        Push-Location src\backend
        try {
            python -m venv venv
            if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
            Write-ColorOutput Green "venv erstellt."
        } catch {
            Write-ColorOutput Red "ERROR beim Erstellen des venv: $_"
            Pop-Location
            Pause-PS
            exit 1
        }
        Pop-Location
    }
} else {
    Write-ColorOutput Yellow "Kein venv gefunden. Erstelle neu..."
    Push-Location src\backend
    try {
        python -m venv venv
        if ($LASTEXITCODE -ne 0) { throw "venv creation failed" }
        Write-ColorOutput Green "venv erstellt."
    } catch {
        Write-ColorOutput Red "ERROR beim Erstellen des venv: $_"
        Pop-Location
        Pause-PS
        exit 1
    }
    Pop-Location
}

# Backend-Dependencies installieren
Write-ColorOutput Cyan "Installiere Backend-Abhaengigkeiten..."
Push-Location src\backend
try {
    & "venv\Scripts\activate"
    Write-ColorOutput Yellow "Upgrade pip..."
    python -m pip install --upgrade pip --quiet
    Write-ColorOutput Yellow "Installiere requirements..."
    python -m pip install -r requirements.txt --quiet
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
    Write-ColorOutput Green "OK: Backend-Abhaengigkeiten installiert."
} catch {
    Write-ColorOutput Red "ERROR bei Backend-Installation: $_"
    Pop-Location
    Pause-PS
    exit 1
} finally {
    Pop-Location
}

# Frontend-Dependencies installieren
Write-ColorOutput Cyan "Pruefe Frontend-Abhaengigkeiten..."
if (-not (Test-Path "src\frontend\node_modules")) {
    Write-ColorOutput Yellow "Installiere Frontend-Abhaengigkeiten..."
    Push-Location src\frontend
    try {
        npm install --silent
        if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
        Write-ColorOutput Green "OK: Frontend-Abhaengigkeiten installiert."
    } catch {
        Write-ColorOutput Red "ERROR bei Frontend-Installation: $_"
        Pop-Location
        Pause-PS
        exit 1
    } finally {
        Pop-Location
    }
} else {
    Write-ColorOutput Green "OK: Frontend-Abhaengigkeiten bereits vorhanden."
}

Write-Output ""
Write-ColorOutput Green "=================================================="
Write-ColorOutput Green "  Starte Services"
Write-ColorOutput Green "=================================================="
Write-Output ""

# Environment-Variablen
$env:CAMERA_INDEX   = $CameraIndex
$env:CAMERA_WIDTH   = $CameraWidth
$env:CAMERA_HEIGHT  = $CameraHeight
$env:CAMERA_FPS     = $CameraFPS
$env:WEBCAM_OFFER_URL = "http://localhost:8000/offer"
$env:VITE_BACKEND_URL = "http://localhost:$BackendPort"

Write-ColorOutput Cyan "Konfiguration:"
Write-Output "  Kamera-Index:  $CameraIndex"
Write-Output "  Aufloesung:    ${CameraWidth}x${CameraHeight}"
Write-Output "  FPS:           $CameraFPS"
Write-Output "  Backend-Port:  $BackendPort"
Write-Output ""

# Fensterstarter
function Start-ServiceWindow {
    param(
        [string]$Title,
        [string]$WorkingDir,
        [string]$Command,
        [string]$Color
    )

    Write-ColorOutput $Color ("Starte " + $Title + " ...")

    $scriptBlock = @"
`$Host.UI.RawUI.WindowTitle = '$Title'
`$Host.UI.RawUI.BackgroundColor = 'Black'
`$Host.UI.RawUI.ForegroundColor = '$Color'
Clear-Host
Write-Host '==================================================' -ForegroundColor $Color
Write-Host '  $Title' -ForegroundColor $Color
Write-Host '==================================================' -ForegroundColor $Color
Write-Host ''
Set-Location '$RootDir'
Set-Location '$WorkingDir'
`$env:CAMERA_INDEX     = '$CameraIndex'
`$env:CAMERA_WIDTH     = '$CameraWidth'
`$env:CAMERA_HEIGHT    = '$CameraHeight'
`$env:CAMERA_FPS       = '$CameraFPS'
`$env:WEBCAM_OFFER_URL = 'http://localhost:8000/offer'
`$env:VITE_BACKEND_URL = 'http://localhost:$BackendPort'
$Command
Write-Host ''
Write-Host 'Press any key to close this window...' -ForegroundColor Yellow
`$null = `$Host.UI.RawUI.ReadKey('NoEcho,IncludeKeyDown')
"@

    $encodedCommand = [Convert]::ToBase64String([System.Text.Encoding]::Unicode.GetBytes($scriptBlock))
    Start-Process powershell -ArgumentList "-NoExit", "-EncodedCommand", $encodedCommand | Out-Null
    Start-Sleep -Seconds 2
}

# Services starten
Start-ServiceWindow `
    -Title "OptiBot - Webcam Service (Port 8000)" `
    -WorkingDir "src\backend" `
    -Command "& venv\Scripts\activate; python -m uvicorn server:app --host 0.0.0.0 --port 8000" `
    -Color "Green"

Start-ServiceWindow `
    -Title "OptiBot - Analyzer Service (Port $BackendPort)" `
    -WorkingDir "src\backend" `
    -Command "& venv\Scripts\activate; python -m uvicorn analyzer:app --host 0.0.0.0 --port $BackendPort" `
    -Color "Cyan"

Start-ServiceWindow `
    -Title "OptiBot - Frontend (Port 3000)" `
    -WorkingDir "src\frontend" `
    -Command "npm run dev" `
    -Color "Magenta"

Write-Output ""
Write-ColorOutput Green "Services gestartet."
Write-Output ""
Write-ColorOutput Yellow "Endpoints:"
Write-Output "  Webcam:   http://localhost:8000/health"
Write-Output "  Analyzer: http://localhost:$BackendPort/health"
Write-Output "  Frontend: http://localhost:3000"
Write-Output ""

Write-ColorOutput Yellow "Oeffne Frontend im Browser..."
Start-Process "http://localhost:3000"

Write-Output ""
Write-ColorOutput Green "Alles bereit."
Write-Output "Strg+C beendet dieses Fenster."
Write-Output ""

# Skript laufen lassen (Hauptfenster)
try {
    while ($true) { Start-Sleep -Seconds 1 }
} finally {
    Write-ColorOutput Yellow "Beende Services..."
}
