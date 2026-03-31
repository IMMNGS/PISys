param(
    [ValidateSet('setup', 'development', 'production')]
    [string]$Mode = 'production',
    [switch]$NoAi
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

function Invoke-PythonStdin([string[]]$PythonCmd, [string]$Code) {
    if ($PythonCmd.Count -gt 1) {
        $Code | & $PythonCmd[0] $PythonCmd[1] -
    } else {
        $Code | & $PythonCmd[0] -
    }
}

function Load-EnvFile([string]$Path) {
    if (-not (Test-Path $Path)) { return }
    Write-Info 'Loading .env'
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

function Test-HttpReady([string]$Url, [int]$Attempts = 60, [int]$DelaySeconds = 1) {
    for ($i = 1; $i -le $Attempts; $i++) {
        try {
            Invoke-WebRequest -Uri $Url -TimeoutSec 2 | Out-Null
            return $true
        } catch {
            Start-Sleep -Seconds $DelaySeconds
        }
    }
    return $false
}

function Test-LlamaCppReady {
    $BuildDir = Join-Path $ProjectDir 'data\local_ai\src\llama.cpp\build'
    $ServerCandidates = @(
        (Join-Path $BuildDir 'bin\llama-server'),
        (Join-Path $BuildDir 'bin\server')
    )

    foreach ($candidate in $ServerCandidates) {
        if (Test-Path $candidate) {
            return $true
        }
    }

    return $false
}

function Ensure-LlamaCpp {
    $LocalAiSrcDir = Join-Path $ProjectDir 'data\local_ai\src'
    $LlamaCppDir = Join-Path $LocalAiSrcDir 'llama.cpp'
    $BuildDir = Join-Path $LlamaCppDir 'build'

    Ensure-Directory $LocalAiSrcDir

    $ServerCandidates = @(
        (Join-Path $BuildDir 'bin\llama-server'),
        (Join-Path $BuildDir 'bin\server')
    )
    foreach ($candidate in $ServerCandidates) {
        if (Test-Path $candidate) {
            Write-Ok "llama.cpp already built: $candidate"
            return
        }
    }

    if (-not (Test-Path $LlamaCppDir)) {
        if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
            Fail 'Git is required to clone llama.cpp automatically.'
        }
        Write-Info "Downloading llama.cpp into $LlamaCppDir"
        & git clone --depth 1 https://github.com/ggerganov/llama.cpp.git $LlamaCppDir
    } else {
        Write-Info "Using existing llama.cpp checkout at $LlamaCppDir"
    }

    $ServerCandidates = @(
        (Join-Path $BuildDir 'bin\llama-server'),
        (Join-Path $BuildDir 'bin\server')
    )
    foreach ($candidate in $ServerCandidates) {
        if (Test-Path $candidate) {
            Write-Ok "llama.cpp already built: $candidate"
            return
        }
    }

    if (-not (Get-Command cmake -ErrorAction SilentlyContinue)) {
        Fail 'CMake is required to build llama.cpp automatically.'
    }

    Write-Info 'Configuring llama.cpp build'
    & cmake -S $LlamaCppDir -B $BuildDir -DLLAMA_BUILD_SERVER=ON
    Write-Info 'Building llama.cpp server'
    & cmake --build $BuildDir
    Write-Ok "llama.cpp built under $BuildDir"
}

$PythonCmd = Get-PythonCommand
if (-not $PythonCmd) {
    Fail 'Python 3 was not found on PATH. Install Python 3.9+ and try again.'
}

Load-EnvFile (Join-Path $ProjectDir '.env')

$VenvPy = Join-Path $ProjectDir '.venv\Scripts\python.exe'
$FirstTimeSetup = $Mode -eq 'setup' -or -not (Test-Path (Join-Path $ProjectDir '.venv')) -or -not (Test-Path (Join-Path $ProjectDir 'data\vcf'))

if ($FirstTimeSetup) {
    Write-Info 'Running first-time setup steps...'
    Write-Info 'Checking Python'
    Invoke-PythonCommand $PythonCmd @('--version')

    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Fail 'Node.js is required but was not found on PATH.'
    }
    Write-Info "Node: $(& node --version)"

    if (-not (Test-Path $VenvPy)) {
        Write-Info 'Creating virtual environment'
        Invoke-PythonCommand $PythonCmd @('-m', 'venv', '.venv')
    }

    Write-Info 'Installing Python dependencies'
    & $VenvPy -m pip install --upgrade pip
    & $VenvPy -m pip install -r requirements.txt

    Write-Info 'Creating data directories'
    Ensure-Directory (Join-Path $ProjectDir 'data\vcf')
    Ensure-Directory (Join-Path $ProjectDir 'data\rag\raw')
    Ensure-Directory (Join-Path $ProjectDir 'data\rag\corpus')
    Ensure-Directory (Join-Path $ProjectDir 'data\rag\eval')
    Ensure-Directory (Join-Path $ProjectDir 'data\local_ai\bin')
    Ensure-Directory (Join-Path $ProjectDir 'data\local_ai\models')
    Ensure-Directory (Join-Path $ProjectDir 'data\variant_uploads')

    $DiseaseTerms = Join-Path $ProjectDir 'data\disease_terms.csv'
    if (-not (Test-Path $DiseaseTerms)) {
        @'
term_name,notes
"Combined immunodeficiency","Doctor-defined free-text disease term"
"Auto-inflammatory syndrome","Use when no exact HPO mapping is available"
"Primary antibody deficiency","Can later be mapped to canonical HPO terms"
'@ | Set-Content -Encoding utf8 $DiseaseTerms
        Write-Ok 'Created data/disease_terms.csv template'
    }

    Write-Info 'Building the frontend for setup'
    Push-Location (Join-Path $ProjectDir 'frontend')
    try {
        if (Get-Command npm -ErrorAction SilentlyContinue) {
            npm install
            npm run build
        } else {
            Fail 'npm was not found on PATH.'
        }
    } finally {
        Pop-Location
    }

    Write-Ok 'First-time setup finished'
}

$MysqlUser = $env:MYSQL_USER
if (-not $MysqlUser) { $MysqlUser = 'pisys_user' }
$MysqlPassword = $env:MYSQL_PASSWORD
if (-not $MysqlPassword) { $MysqlPassword = '' }
$MysqlHost = $env:MYSQL_HOST
if (-not $MysqlHost) { $MysqlHost = 'localhost' }
$MysqlPort = $env:MYSQL_PORT
if (-not $MysqlPort) { $MysqlPort = '3308' }
$MysqlDb = $env:MYSQL_DB
if (-not $MysqlDb) { $MysqlDb = 'pisys_db' }

if (Get-Command mysql -ErrorAction SilentlyContinue) {
    Write-Info "Ensuring MySQL database '$MysqlDb' exists (if reachable)"
    $mysqlArgs = @('-u', $MysqlUser, '-h', $MysqlHost, '-P', $MysqlPort)
    if ($MysqlPassword) { $mysqlArgs += "-p$MysqlPassword" }
    try {
        & mysql @mysqlArgs -e "CREATE DATABASE IF NOT EXISTS `$MysqlDb` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" | Out-Null
    } catch {
        Write-Warn 'Could not create the database automatically'
    }
} else {
    Write-Warn 'mysql CLI not found — skipping automatic DB creation'
}

Ensure-Directory (Join-Path $ProjectDir 'data\vcf')
Ensure-Directory (Join-Path $ProjectDir 'data\variant_uploads')
Ensure-Directory (Join-Path $ProjectDir 'data\rag\raw')
Ensure-Directory (Join-Path $ProjectDir 'data\rag\corpus')
Ensure-Directory (Join-Path $ProjectDir 'data\rag\eval')
Ensure-Directory (Join-Path $ProjectDir 'data\local_ai\bin')
Ensure-Directory (Join-Path $ProjectDir 'data\local_ai\models')

$DiseaseTerms = Join-Path $ProjectDir 'data\disease_terms.csv'
if (-not (Test-Path $DiseaseTerms)) {
    @'
term_name,notes
"Combined immunodeficiency","Doctor-defined free-text disease term"
"Auto-inflammatory syndrome","Use when no exact HPO mapping is available"
"Primary antibody deficiency","Can later be mapped to canonical HPO terms"
'@ | Set-Content -Encoding utf8 $DiseaseTerms
}

Write-Info 'Syncing disease terms from data/disease_terms.csv'
Invoke-PythonStdin $PythonCmd @'
import csv
from pathlib import Path

from backend.app import create_app
from backend.models import DiseaseTerm, db


def normalize(text: str) -> str:
    return " ".join((text or "").strip().lower().split())


csv_path = Path("data/disease_terms.csv")
if not csv_path.exists():
    print("No disease_terms.csv found; skipping")
    raise SystemExit(0)

app = create_app()
added = 0
updated = 0

with app.app_context():
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            term_name = (row.get("term_name") or "").strip()
            notes = (row.get("notes") or "").strip() or None
            if not term_name:
                continue

            normalized = normalize(term_name)
            existing = DiseaseTerm.query.filter_by(normalized_name=normalized).first()
            if existing is None:
                db.session.add(DiseaseTerm(
                    term_name=term_name,
                    normalized_name=normalized,
                    notes=notes,
                ))
                added += 1
            else:
                changed = False
                if existing.term_name != term_name:
                    existing.term_name = term_name
                    changed = True
                if notes and existing.notes != notes:
                    existing.notes = notes
                    changed = True
                if changed:
                    updated += 1

    db.session.commit()

print(f"Disease terms sync complete. Added {added}, updated {updated}.")
'@
Write-Ok 'Disease terms sync completed'

if ($Mode -eq 'production') {
    Write-Info 'Starting in production mode'
    [System.Environment]::SetEnvironmentVariable('FLASK_ENV', 'production', 'Process')

    if (-not $env:SECRET_KEY) {
        $secret = (Invoke-PythonCommand $PythonCmd @('-c', "import secrets; print(secrets.token_hex(32))") | Out-String).Trim()
        [System.Environment]::SetEnvironmentVariable('SECRET_KEY', $secret, 'Process')
        Write-Warn "SECRET_KEY was not set. Generated a random one for this session: $secret"
        Write-Warn 'Set SECRET_KEY in your environment or .env for persistent sessions.'
    }

    Write-Info 'Building frontend for production'
    Push-Location (Join-Path $ProjectDir 'frontend')
    try {
        if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
            Fail 'npm was not found on PATH.'
        }
        npm ci
        npm run build
    } finally {
        Pop-Location
    }
    Write-Ok 'Frontend built → frontend/dist/'

    Write-Info 'Ensuring Python dependencies installed'
    & $VenvPy -m pip install -r requirements.txt
    Write-Ok 'Python dependencies OK'

    Write-Info 'Checking HPO terms'
    Invoke-PythonStdin $PythonCmd @'
from backend.app import create_app
from backend.models import db, HPOTerm
from pyhpo import Ontology

app = create_app()

with app.app_context():
    hpo_count = HPOTerm.query.count()
    if hpo_count > 0:
        print(f'HPO terms already present ({hpo_count}) — skipping load')
        raise SystemExit(0)

    print('No HPO terms found — loading (one-time)')
    ont = Ontology()
    added = 0
    for term in ont:
        if not HPOTerm.query.filter_by(hpo_id=term.id).first():
            db.session.add(HPOTerm(hpo_id=term.id, term_name=term.name, definition=term.definition or None, synonyms=', '.join(term.synonym) if term.synonym else None))
            added += 1
    db.session.commit()
    print(f'Loaded {added} HPO terms')
'@
    Write-Ok 'HPO terms check completed'

    if (-not $NoAi) {
        if (Test-LlamaCppReady) {
            Write-Ok 'Existing llama.cpp build found; skipping automatic setup'
        } elseif ((Get-Command git -ErrorAction SilentlyContinue) -and (Get-Command cmake -ErrorAction SilentlyContinue)) {
            Ensure-LlamaCpp
        } else {
            Write-Warn 'Git or CMake is not available; skipping automatic llama.cpp setup and falling back to the mock/local fallback server if needed'
        }
        Write-Info 'Starting local LLM server'
        Start-Process -FilePath $VenvPy -ArgumentList @('scripts/start_local_llm.py', '--mode', 'auto', '--host', '127.0.0.1', '--port', '8080') -PassThru | Out-Null
        if (-not (Test-HttpReady 'http://127.0.0.1:8080/health')) {
            Fail 'Local LLM server did not become ready at http://127.0.0.1:8080/health'
        }
        Write-Ok 'Local LLM server ready'
    } else {
        Write-Warn 'NoAi was set — skipping local LLM startup'
    }

    Write-Info 'Launching production server'
    if (Get-Command waitress-serve -ErrorAction SilentlyContinue) {
        & waitress-serve --listen=0.0.0.0:8000 run:app
    } else {
        Write-Warn 'waitress-serve was not found; falling back to the Flask development server'
        & $VenvPy run.py
    }
} else {
    Write-Info 'Starting in development mode'
    Write-Info 'Run the frontend dev server separately with: cd frontend; npm run dev'
    & $VenvPy run.py
}
