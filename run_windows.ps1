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
    if (Get-Command py -ErrorAction SilentlyContinue) { return @('py', '-3') }
    if (Get-Command python3 -ErrorAction SilentlyContinue) { return @('python3') }
    if (Get-Command python -ErrorAction SilentlyContinue) { return @('python') }
    return $null
}

function Invoke-PythonCommand([string[]]$PythonCmd, [string[]]$Args) {
    if ($PythonCmd.Count -gt 1) {
        & $PythonCmd[0] $PythonCmd[1] @Args
    } else {
        & $PythonCmd[0] @Args
    }
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

$PythonCmd = Get-PythonCommand
if (-not $PythonCmd) {
    Fail 'Python 3 was not found on PATH. Install Python 3.9+ and try again.'
}

Load-EnvFile (Join-Path $ProjectDir '.env')

$VenvPy = Join-Path $ProjectDir '.venv\Scripts\python.exe'
$FirstTimeSetup = $Mode -eq 'setup' -or -not (Test-Path (Join-Path $ProjectDir '.venv')) -or -not (Test-Path (Join-Path $ProjectDir 'data\vcf'))

if ($FirstTimeSetup) {
    Write-Info 'Running setup...'
    Invoke-PythonCommand $PythonCmd @('--version')

    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Fail 'Node.js is required but was not found on PATH.'
    }

    if (-not (Test-Path $VenvPy)) {
        Invoke-PythonCommand $PythonCmd @('-m', 'venv', '.venv')
    }

    & $VenvPy -m pip install --upgrade pip
    & $VenvPy -m pip install -r requirements.txt

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

if ($Mode -eq 'production') {
    Write-Info 'Starting in production mode'
    [System.Environment]::SetEnvironmentVariable('FLASK_ENV', 'production', 'Process')

    if (-not $env:SECRET_KEY) {
        $secret = (Invoke-PythonCommand $PythonCmd @('-c', "import secrets; print(secrets.token_hex(32))") | Out-String).Trim()
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
