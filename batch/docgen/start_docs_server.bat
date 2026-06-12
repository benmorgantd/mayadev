@echo off
setlocal enabledelayedexpansion

:: 1. Fallback definition if executed outside of an active Maya session environment context
if "%MAYADEV_ROOT%"=="" (
    set "MAYADEV_ROOT=C:\Users\bmorgan\Documents\dev\maya\mayadev"
)

:: Verify the path is valid before continuing
if not exist "%MAYADEV_ROOT%" (
    echo [!] Error: Target repository root path does not exist: %MAYADEV_ROOT%
    pause
    exit /b 1
)

:: 2. Map structural directory rules cleanly
set "WORKING_DIR=%MAYADEV_ROOT%\py\scripts"
set "VBS_PATH=%temp%\launch_mkdocs_hidden.vbs"

if not exist "%WORKING_DIR%\mkdocs.yml" (
    echo [!] Error: Could not locate mkdocs.yml inside %WORKING_DIR%
    pause
    exit /b 1
)

echo [@] Generating background workspace server instructions...

:: 3. Write out a VBScript that explicitly sets its own working directory internally
echo Set WshShell = CreateObject("WScript.Shell") > "%VBS_PATH%"
echo WshShell.CurrentDirectory = "%WORKING_DIR%" >> "%VBS_PATH%"
echo WshShell.Run "cmd.exe /c python -m mkdocs serve", 0, false >> "%VBS_PATH%"

echo [@] Executing windowless background documentation hosting service...
wscript.exe "%VBS_PATH%"

:: Defer cleanup file destruction metrics briefly to let the OS register the script allocation
timeout /t 1 /nobreak >nul
if exist "%VBS_PATH%" del "%VBS_PATH%"

echo [+][Success] Background MkDocs server initialized via Python module fallback.
echo Preview available locally at: http://127.0.0.1:8000
pause