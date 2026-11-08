@echo off

:: RigModules menu tests. The layout tests need only Python. The script tests run in mayapy and need
:: RIGMODULES_PLUGIN set to a RigModules.mll (a copy, if a Maya session has the build loaded); without it they skip.
set "MAYA_SKIP_USERSETUP_PY=1"

"C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" -m unittest discover -s "%~dp0." -p "test_*.py" -v
