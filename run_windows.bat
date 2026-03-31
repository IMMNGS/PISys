@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "PS1=%SCRIPT_DIR%run_windows.ps1"

if not exist "%PS1%" (
  echo [HA] Missing launcher script: %PS1%
  exit /b 1
)

set "PS_ARGS="
:parse_args
if "%~1"=="" goto done_args
if /I "%~1"=="setup" (
  set "PS_ARGS=%PS_ARGS% -Mode setup"
) else if /I "%~1"=="development" (
  set "PS_ARGS=%PS_ARGS% -Mode development"
) else if /I "%~1"=="production" (
  set "PS_ARGS=%PS_ARGS% -Mode production"
) else if /I "%~1"=="--no-ai" (
  set "PS_ARGS=%PS_ARGS% -NoAi"
) else if /I "%~1"=="-h" (
  set "PS_ARGS=%PS_ARGS% -?"
) else if /I "%~1"=="--help" (
  set "PS_ARGS=%PS_ARGS% -?"
) else (
  echo [HA] Unknown argument: %~1
  echo [HA] Usage: run_windows.bat [setup^|development^|production] [--no-ai]
  exit /b 2
)
shift
goto parse_args

:done_args
echo [HA] Launching Windows setup/runner...
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %PS_ARGS%
exit /b %ERRORLEVEL%
