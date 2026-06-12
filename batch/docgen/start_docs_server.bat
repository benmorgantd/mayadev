@echo off
:: Change directory to where this batch script lives
cd /d "%~dp0"

:: Guard check for environment variable stability across machines
if "%MAYADEV_ROOT%"=="" (
    echo [!] Error: MAYADEV_ROOT environment variable is not set.
    pause
    exit /b 1
)

:: Map output directory path relative to dev root layout
set DOCS_DIR=%MAYADEV_ROOT%\py\scripts\docs

:: Navigate to the directory containing your mkdocs.yml file
cd /d "%DOCS_DIR%\.." 

:: Create a temporary hidden VBScript to launch the server windowless
echo Set WshShell = CreateObject("WScript.Shell") > "%temp%\launch_mkdocs_hidden.vbs" 
echo WshShell.Run "cmd.exe /c mkdocs serve", 0, false >> "%temp%\launch_mkdocs_hidden.vbs" 

:: Execute the invisible script
wscript.exe "%temp%\launch_mkdocs_hidden.vbs" 

:: Erase the temporary script asset from the system cache
del "%temp%\launch_mkdocs_hidden.vbs" 

echo Background MkDocs server has been initialized.
pause