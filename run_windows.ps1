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

function Ensure-NonAdminAppRole {
    if (-not $env:POSTGRES_USER) { return }
    if ($env:POSTGRES_USER.Trim().ToLowerInvariant() -eq 'postgres') {
        Fail "POSTGRES_USER must be a dedicated app role (e.g. pisysdb), not 'postgres'."
    }
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
        $value = $line.Substring($idx + 1).Trim()

        # Support dotenv-style quoted values and inline comments.
        if ($value.Length -ge 2) {
            if (($value.StartsWith('"') -and $value.EndsWith('"')) -or ($value.StartsWith("'") -and $value.EndsWith("'"))) {
                $value = $value.Substring(1, $value.Length - 2)
            } else {
                $commentIdx = $value.IndexOf(' #')
                if ($commentIdx -ge 0) {
                    $value = $value.Substring(0, $commentIdx).TrimEnd()
                }
            }
        }

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

function Test-PostgresInstalled {
    Add-PostgresBinToPath

    if (Get-Command psql -ErrorAction SilentlyContinue) {
        return $true
    }

    $pgRoot = 'C:\Program Files\PostgreSQL'
    if (Test-Path $pgRoot) {
        $psqlExe = Get-ChildItem -Path $pgRoot -Filter psql.exe -Recurse -ErrorAction SilentlyContinue |
            Select-Object -First 1
        if ($psqlExe) {
            return $true
        }
    }

    $services = Get-Service -Name 'postgresql*' -ErrorAction SilentlyContinue
    if ($services) {
        return $true
    }

    if (Get-Command winget -ErrorAction SilentlyContinue) {
        $wingetIds = @(
            'PostgreSQL.PostgreSQL.18',
            'PostgreSQL.PostgreSQL',
            'PostgreSQL.PostgreSQL.17',
            'PostgreSQL.PostgreSQL.16',
            'PostgreSQL.PostgreSQL.15',
            'EnterpriseDB.PostgreSQL'
        )

        foreach ($pkg in $wingetIds) {
            $listOutput = (& winget list --id=$pkg -e --source winget 2>&1 | Out-String)
            if ($LASTEXITCODE -eq 0 -and $listOutput -notmatch 'No installed package found') {
                return $true
            }
        }
    }

    return $false
}

function Ensure-PostgresInstalled {
    if (Test-PostgresInstalled) {
        Write-Ok 'PostgreSQL installation detected.'
        return
    }

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Fail 'PostgreSQL is not installed and winget is unavailable. Install PostgreSQL manually, then rerun setup.'
    }

    Write-Info 'PostgreSQL not found. Updating winget sources...'
    & winget source update | Out-Null

    $packageIds = @(
        'PostgreSQL.PostgreSQL.18',
        'PostgreSQL.PostgreSQL',
        'PostgreSQL.PostgreSQL.17',
        'PostgreSQL.PostgreSQL.16',
        'PostgreSQL.PostgreSQL.15',
        'EnterpriseDB.PostgreSQL'
    )

    $installed = $false
    foreach ($pkg in $packageIds) {
        Write-Info "Trying winget package id: $pkg"
        Write-Info 'If installer prompts appear, complete them and return to this setup window.'
        & winget install --id=$pkg -e --source winget --accept-package-agreements --accept-source-agreements
        Add-PostgresBinToPath
        if ($LASTEXITCODE -eq 0 -and (Test-PostgresInstalled)) {
            $installed = $true
            break
        }
    }

    if (-not $installed) {
        Write-Warn 'No known PostgreSQL package id could be installed automatically.'
        Write-Info 'Available winget PostgreSQL entries:'
        & winget search PostgreSQL --source winget
        Fail 'PostgreSQL installation failed. Install one of the listed PostgreSQL packages manually, then rerun setup.'
    }

    if (-not (Test-PostgresInstalled)) {
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

function Read-SecretValue([string]$Prompt) {
    $secure = Read-Host -Prompt $Prompt -AsSecureString
    $ptr = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [System.Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    } finally {
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)
    }
}

function Read-RequiredSecretValue([string]$Prompt) {
    while ($true) {
        $value = Read-SecretValue -Prompt $Prompt
        if (-not [string]::IsNullOrWhiteSpace($value)) {
            return $value
        }
        Write-Warn 'A non-empty password is required for setup.'
    }
}

function Escape-SqlLiteral([string]$Value) {
    return $Value.Replace("'", "''")
}

function Escape-SqlIdentifier([string]$Value) {
    return $Value.Replace('"', '""')
}

function Resolve-PsqlExe {
    Add-PostgresBinToPath

    $cmd = Get-Command psql -ErrorAction SilentlyContinue
    if ($cmd) {
        return $cmd.Source
    }

    $pgRoot = 'C:\Program Files\PostgreSQL'
    if (Test-Path $pgRoot) {
        $psqlExe = Get-ChildItem -Path $pgRoot -Filter psql.exe -Recurse -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($psqlExe) {
            return $psqlExe.FullName
        }
    }

    return $null
}

function Invoke-PsqlCommand([string]$Password, [string[]]$Args) {
    if (-not $script:PsqlExe) {
        $script:PsqlExe = Resolve-PsqlExe
    }
    if (-not $script:PsqlExe) {
        Fail 'psql command not found after PostgreSQL installation. Cannot reset postgres password automatically.'
    }

    $oldPgPassword = $env:PGPASSWORD
    [System.Environment]::SetEnvironmentVariable('PGPASSWORD', $Password, 'Process')
    try {
        & $script:PsqlExe @Args
    } finally {
        if ($null -eq $oldPgPassword) {
            [System.Environment]::SetEnvironmentVariable('PGPASSWORD', $null, 'Process')
        } else {
            [System.Environment]::SetEnvironmentVariable('PGPASSWORD', $oldPgPassword, 'Process')
        }
    }
}

function Test-PsqlLogin([string]$User, [string]$Password) {
    $args = @('-h', $env:POSTGRES_HOST, '-p', $env:POSTGRES_PORT, '-U', $User, '-d', 'postgres', '-tAc', 'SELECT 1;')
    Invoke-PsqlCommand -Password $Password -Args $args | Out-Null
    return ($LASTEXITCODE -eq 0)
}

function Ensure-PostgresRoleForSetup {
    Ensure-NonAdminAppRole

    $script:PsqlExe = Resolve-PsqlExe
    if (-not $script:PsqlExe) {
        Fail 'psql command not found after PostgreSQL installation. Cannot reset postgres password automatically.'
    }

    if ($env:POSTGRES_HOST -notin @('localhost', '127.0.0.1', '::1')) {
        Write-Warn "Skipping PostgreSQL role bootstrap for non-local host '$($env:POSTGRES_HOST)'."
        return
    }

    $targetUser = $env:POSTGRES_USER
    $targetPassword = $env:POSTGRES_PASSWORD
    if ([string]::IsNullOrWhiteSpace($targetPassword)) {
        $targetPassword = Read-RequiredSecretValue -Prompt "Enter NEW PostgreSQL password for user '$targetUser'"
    }

    if (Test-PsqlLogin -User $targetUser -Password $targetPassword) {
        [System.Environment]::SetEnvironmentVariable('POSTGRES_PASSWORD', $targetPassword, 'Process')
        Write-Ok "PostgreSQL credentials for '$targetUser' are valid."
        return
    }

    Write-Warn "Could not authenticate as '$targetUser'. Attempting role bootstrap with an admin account."
    $adminUser = if ($env:POSTGRES_ADMIN_USER) { $env:POSTGRES_ADMIN_USER } else { 'postgres' }
    $adminPassword = if ($env:POSTGRES_ADMIN_PASSWORD) { $env:POSTGRES_ADMIN_PASSWORD } else { '' }

    $adminReady = $false
    if (-not [string]::IsNullOrWhiteSpace($adminPassword) -and (Test-PsqlLogin -User $adminUser -Password $adminPassword)) {
        $adminReady = $true
    }

    if (-not $adminReady) {
        for ($attempt = 1; $attempt -le 3; $attempt++) {
            $adminPassword = Read-RequiredSecretValue -Prompt "Enter CURRENT PostgreSQL password for admin user '$adminUser'"
            if (Test-PsqlLogin -User $adminUser -Password $adminPassword) {
                $adminReady = $true
                break
            }
            Write-Warn "Admin authentication failed (attempt $attempt/3)."
        }
    }

    if (-not $adminReady) {
        Fail "Unable to authenticate as PostgreSQL admin '$adminUser'. Set POSTGRES_ADMIN_USER/POSTGRES_ADMIN_PASSWORD and rerun setup."
    }

    $escapedUser = Escape-SqlIdentifier -Value $targetUser
    $escapedPassword = Escape-SqlLiteral -Value $targetPassword
    $roleSql = @"
DO
\$\$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$targetUser') THEN
        EXECUTE 'CREATE ROLE ""$escapedUser"" LOGIN PASSWORD ''$escapedPassword''';
    ELSE
        EXECUTE 'ALTER ROLE ""$escapedUser"" WITH LOGIN PASSWORD ''$escapedPassword''';
    END IF;
END
\$\$;
"@
    $roleArgs = @('-h', $env:POSTGRES_HOST, '-p', $env:POSTGRES_PORT, '-U', $adminUser, '-d', 'postgres', '-v', 'ON_ERROR_STOP=1', '-c', $roleSql)
    Invoke-PsqlCommand -Password $adminPassword -Args $roleArgs | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Fail "Failed to create or update PostgreSQL role '$targetUser'."
    }

    if (-not (Test-PsqlLogin -User $targetUser -Password $targetPassword)) {
        Fail "Role bootstrap finished, but login still fails for '$targetUser'."
    }

    [System.Environment]::SetEnvironmentVariable('POSTGRES_PASSWORD', $targetPassword, 'Process')
    Write-Ok "PostgreSQL role '$targetUser' is ready for setup."
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
    else { [System.Environment]::SetEnvironmentVariable('POSTGRES_USER', 'pisysdb', 'Process') }
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

Ensure-NonAdminAppRole

$VenvPy = Join-Path $ProjectDir '.venv\Scripts\python.exe'

function Run-Setup {
    Write-Info 'Running setup...'
    Invoke-PythonCommand -PythonArgs @('--version')

    if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
        Fail 'Node.js is required but was not found on PATH.'
    }

    Ensure-PostgresInstalled
    Ensure-PostgresServiceRunning
    Ensure-PostgresRoleForSetup

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
