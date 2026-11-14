@echo off

:: bmaya.core tool registry tests. The registry tests are plain Python. The editor and build_menus tests run in
:: mayapy, offscreen, and need no plugin.
set "MAYA_SKIP_USERSETUP_PY=1"
set "QT_QPA_PLATFORM=offscreen"

python -m unittest discover -s "%~dp0." -p "test_core_*.py"
if errorlevel 1 exit /b 1

"C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" -m unittest discover -s "%~dp0." -p "test_maya_*.py"
