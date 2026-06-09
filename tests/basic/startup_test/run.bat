@echo off

:: Add the scripts folder directly to PYTHONPATH so bmaya can be resolved immediately on launch
set "PYTHONPATH=%MAYADEV_ROOT%\py\scripts;%PYTHONPATH%"

:: Execute the test class file using the Maya 2026 python interpreter
"C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" "%MAYADEV_ROOT%\tests\basic\startup_test\main.py"

pause