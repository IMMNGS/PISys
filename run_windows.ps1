param(
    [ValidateSet('setup', 'development', 'production')]
    [string]$Mode = 'production'
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ProjectDir

function Write-Info($Message) { Write-Host "[HA] $Message" -ForegroundColor Cyan }
function Write-Ok($Message)   { Write-Host "[HA] $Message" -ForegroundColor Green }
function Write-Warn($Message) { Write-Host "[HA] $Message" -ForegroundColor Yellow }
function Fail($Message) {
    Write-Host "[HA] $Message" -ForegroundColor Red
    exit 1
}

function Get-PythonCommand {
    if (Get-Command py -ErrorAction SilentlyContinue) { return @{ Exe = 'py'; BaseArgs = @('-3') } }
    if (Get-Command python3 -ErrorAction SilentlyContinue) { return @{ Exe = 'python3'; BaseArgs = @() } }
    if (Get-Command python -ErrorAction SilentlyContinue) { return @{ Exe = 'python'; BaseArgs = @() } }
    return $null
}

function Invoke-PythonCommand([string[]]$PythonArgs) {
    if (-not $PythonArgs -or $PythonArgs.Count -eq 0) {
        Fail 'Internal error: Python command invoked without arguments.'
    }

    & $script:PythonExe @script:PythonBaseArgs @PythonArgs
}

function Load-EnvFile([string]$Path) {
    if (-not (Test-Path $Path)) { return }
    Get-Content $Path | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith('#')) { return }
        $idx = $line.IndexOf('=')
        if ($idx -lt 1) { return }
        $name = $line.Substring(0, $idx).Trim()
        $value = $line.Substring($idx + 1)
        [System.Environment]::SetEnvironmentVariable($name, $value, 'Process')
    }
}

function Ensure-Directory([string]$Path) {
    New-Item -ItemType Directory -Force -Path $Path | Out-Null
}

function Add-PostgresBinToPath {
    $pgRoot = 'C:\Program Files\PostgreSQL'
    if (-not (Test-Path $pgRoot)) { return }

    $binDirs = Get-ChildItem -Path $pgRoot -Directory -ErrorAction SilentlyContinue |
        Sort-Object Name -Descending |
        ForEach-Object { Join-Path $_.FullName 'bin' } |
        Where-Object { Test-Path $_ }

    foreach ($binDir in $binDirs) {
        if ($env:Path -notlike "*$binDir*") {
            $env:Path = "$binDir;$env:Path"
        }
    }
}

function Ensure-PostgresInstalled {
    if (Get-Command psql -ErrorAction SilentlyContinue) {
        Write-Ok 'PostgreSQL client detected.'
        return
    }

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Fail 'PostgreSQL is not installed and winget is unavailable. Install PostgreSQL manually, then rerun setup.'
    }

    Write-Info 'PostgreSQL not found. Installing via winget (this may prompt for elevation)...'
    & winget install --id PostgreSQL.PostgreSQL --exact --silent --accept-package-agreements --accept-source-agreements --disable-interactivity

    Add-PostgresBinToPath

    if (-not (Get-Command psql -ErrorAction SilentlyContinue)) {
        Fail 'PostgreSQL installation did not complete successfully. Install PostgreSQL manually, then rerun setup.'
    }

    Write-Ok 'PostgreSQL installation complete.'
}

function Ensure-PostgresServiceRunning {
    # Only attempt local service checks when using localhost/loopback.
    $isLocalHost = $env:POSTGRES_HOST -in @('localhost', '127.0.0.1', '::1')
    if (-not $isLocalHost) { return }

    $services = Get-Service -Name 'postgresql*' -ErrorAction SilentlyContinue
    if (-not $services) {
        Write-Warn 'No PostgreSQL Windows service found. Verify your PostgreSQL installation.'
        return
    }

    foreach ($svc in $services) {
        if ($svc.Status -ne 'Running') {
            try {
                Write-Info "Starting service $($svc.Name)..."
                Start-Service -Name $svc.Name -ErrorAction Stop
            } catch {
                Write-Warn "Could not start service $($svc.Name). Try running setup as Administrator."
            }
        }
    }
}

$PythonCommand = Get-PythonCommand
if (-not $PythonCommand) {
    Fail 'Python 3 was not found on PATH. Install Python 3.9+ and try again.'
}

$script:PythonExe = [string]$PythonCommand.Exe
$script:PythonBaseArgs = @($PythonCommand.BaseArgs)

Load-EnvFile (Join-Path $ProjectDir '.env')

# PostgreSQL defaults match backend/config.py and run.sh.
if (-not $env:POSTGRES_USER) {
    if ($env:MYSQL_USER) { [System.Environment]::SetEnvironmentVariable('POSTGRES_USER', $env:MYSQL_USER, 'Process') }
    else { [System.Environment]::SetEnvironmentVariable('POSTGRES_USER', 'postgres', 'Process') }
}
if (-not $env:POSTGRES_PASSWORD) {
    if ($env:MYSQL_PASSWORD) { [System.Environment]::SetEnvironmentVariable('POSTGRES_PASSWORD', $env:MYSQL_PASSWORD, 'Process') }
    else { [System.Environment]::SetEnvironmentVariable('POSTGRES_PASSWORD', '', 'Process') }
}
if (-not $env:POSTGRES_HOST) {
    if ($env:MYSQL_HOST) { [System.Environment]::SetEnvironmentVariable('POSTGRES_HOST', $env:MYSQL_HOST, 'Process') }
    else { [System.Environment]::SetEnvironmentVariable('POSTGRES_HOST', 'localhost', 'Process') }
}
if (-not $env:POSTGRES_PORT) {
    if ($env:MYSQL_PORT) { [System.Environment]::SetEnvironmentVariable('POSTGRES_PORT', $env:MYSQL_PORT, 'Process') }
    else { [System.Environment]::SetEnvironmentVariable('POSTGRES_PORT', '5432', 'Process') }
}
if (-not $env:POSTGRES_DB) {
    if ($env:MYSQL_DB) { [System.Environment]::SetEnvironmentVariable('POSTGRES_DB', $env:MYSQL_DB, 'Process') }
    else { [System.Environment]::SetEnvironmentVariable('POSTGRES_DB', 'pisys_db', 'Process') }
}

$VenvPy = Join-Path $ProjectDir '.venv\Scripts\python.exe'

function Run-Setup {
    Write-Info 'Running setup...'
    Invoke-PythonCommand -PythonArgs @('--version')

    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Fail 'Node.js is required but was not found on PATH.'
    }

    Ensure-PostgresInstalled
    Ensure-PostgresServiceRunning

    if (-not (Test-Path $VenvPy)) {
        Invoke-PythonCommand -PythonArgs @('-m', 'venv', '.venv')
    }

    & $VenvPy -m pip install --upgrade pip
    & $VenvPy -m pip install -r requirements.txt

    Write-Info 'Ensuring PostgreSQL database exists'
    $ensureDbCode = @'
from backend.app import _ensure_databases
from backend.config import DevelopmentConfig

_ensure_databases(DevelopmentConfig)
'@

    try {
        & $VenvPy -c $ensureDbCode
    } catch {
        Write-Warn 'Could not auto-create PostgreSQL database. Verify POSTGRES_HOST/POSTGRES_PORT and credentials, then create DB manually if needed.'
    }

    Ensure-Directory (Join-Path $ProjectDir 'data\vcf')
    Ensure-Directory (Join-Path $ProjectDir 'data\variant_uploads')

    $DiseaseTerms = Join-Path $ProjectDir 'data\disease_terms.csv'
    if (-not (Test-Path $DiseaseTerms)) {
@'
term_name,notes
"Combined immunodeficiency","Doctor-defined free-text disease term"
"Auto-inflammatory syndrome","Use when no exact HPO mapping is available"
"Primary antibody deficiency","Can later be mapped to canonical HPO terms"
'@ | Set-Content -Encoding utf8 $DiseaseTerms
    }

    Push-Location (Join-Path $ProjectDir 'frontend')
    try {
        npm install
        npm run build
    } finally {
        Pop-Location
    }

    Write-Ok 'Setup finished'
}

if ($Mode -eq 'setup') {
    Run-Setup
    Write-Info 'Setup-only mode complete.'
    exit 0
}

$NeedBootstrapSetup = -not (Test-Path (Join-Path $ProjectDir '.venv')) -or -not (Test-Path (Join-Path $ProjectDir 'data\vcf'))
if ($NeedBootstrapSetup) {
    Run-Setup
}

if ($Mode -eq 'production') {
    Write-Info 'Starting in production mode'
    [System.Environment]::SetEnvironmentVariable('FLASK_ENV', 'production', 'Process')

    if (-not $env:SECRET_KEY) {
        $secret = (Invoke-PythonCommand -PythonArgs @('-c', "import secrets; print(secrets.token_hex(32))") | Out-String).Trim()
        [System.Environment]::SetEnvironmentVariable('SECRET_KEY', $secret, 'Process')
        Write-Warn 'SECRET_KEY was not set. Generated one for this session.'
    }

    Push-Location (Join-Path $ProjectDir 'frontend')
    try {
        npm ci
        npm run build
    } finally {
        Pop-Location
    }

    & $VenvPy -m pip install -r requirements.txt

    if (Get-Command waitress-serve -ErrorAction SilentlyContinue) {
        & waitress-serve --listen=0.0.0.0:8000 run:app
    } else {
        & $VenvPy run.py
    }
} else {
    Write-Info 'Starting in development mode'
    & $VenvPy run.py
}
