Set WshShell = CreateObject("WScript.Shell")
' The ,0 parameter tells Windows to hide the window completely
WshShell.Run "cmd.exe /c python -m mkdocs serve", 0, false