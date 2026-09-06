Option Explicit

Dim shell, fso, appDir, exePath
Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
appDir = fso.GetParentFolderName(WScript.ScriptFullName)
exePath = fso.BuildPath(appDir, "DesktopMemo.exe")
shell.Run """" & exePath & """ --widget-only", 0, False
Set fso = Nothing
Set shell = Nothing
