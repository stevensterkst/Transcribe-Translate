Option Explicit
Dim sh, fso, root, exePath, fallbackPath
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
root = fso.GetParentFolderName(WScript.ScriptFullName)
exePath = fso.BuildPath(root, "dist\SS-Transcribe-Translate\SS-Transcribe-Translate.exe")
fallbackPath = fso.BuildPath(root, "START-APP.cmd")
If Not fso.FileExists(exePath) And Not fso.FileExists(fallbackPath) Then
  MsgBox "SS Transcribe-Translate: neither the packaged EXE nor START-APP.cmd was found." & vbCrLf & root, vbCritical, "SS Transcribe-Translate"
  WScript.Quit 2
End If
sh.CurrentDirectory = root
If fso.FileExists(exePath) Then
  sh.Run """" & exePath & """", 0, False
Else
  sh.Run """" & fallbackPath & """", 0, False
End If
WScript.Quit 0
