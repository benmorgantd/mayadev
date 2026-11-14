@echo off

:: bmaya.core.asset tests. The model tests need only Python. The Maya handler tests run in mayapy and need
:: RIGMODULES_PLUGIN set to a RigModules.mll (a copy, if a Maya session has the build loaded); without it they skip.
set "MAYA_SKIP_USERSETUP_PY=1"

python -m unittest discover -s "%~dp0." -p "test_asset_*.py"
if errorlevel 1 exit /b 1

"C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" -m unittest discover -s "%~dp0." -p "test_maya_*.py"
