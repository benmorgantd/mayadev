@echo off

:: Add the scripts folder directly to PYTHONPATH so bmaya can be resolved immediately on launch
:: RigModules' python folder holds mayalaunch, which the batch framework starts Maya through
set "PYTHONPATH=%MAYADEV_ROOT%\py\scripts;%RIGMODULES_ROOT%\python;%PYTHONPATH%"

:: Execute the test class file using the Maya 2026 python interpreter
"C:\Program Files\Autodesk\Maya2026\bin\mayapy.exe" %~dp0main.py

pause