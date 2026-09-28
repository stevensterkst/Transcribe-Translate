Option Explicit

Dim sh, fso, root, startDir, desktopDir, exePath, fallbackPath
Dim ws, shortcutPath, desktopShortcutPath, sc, dsc
Dim shellApp, startFolder, startItem, verbs, verb, verbText
Dim oldConsole, pinAttempted, pinned

Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
Set ws = CreateObject("WScript.Shell")
Set shellApp = CreateObject("Shell.Application")

root = fso.GetParentFolderName(WScript.ScriptFullName)
exePath = fso.BuildPath(root, "dist\SS-Transcribe-Translate\SS-Transcribe-Translate.exe")
fallbackPath = fso.BuildPath(root, "START-APP.cmd")

If Not fso.FileExists(exePath) Then
  MsgBox "SS Transcribe-Translate: the packaged EXE was not found." & vbCrLf & _
         "Run the verified Windows build first." & vbCrLf & vbCrLf & root, vbCritical, "SS Transcribe-Translate"
  WScript.Quit 2
End If

startDir = fso.BuildPath(sh.SpecialFolders("StartMenu"), "Programs\SS Transcribe-Translate")
If Not fso.FolderExists(startDir) Then fso.CreateFolder(startDir)

shortcutPath = fso.BuildPath(startDir, "SS Transcribe-Translate.lnk")
Set sc = ws.CreateShortcut(shortcutPath)
sc.TargetPath = exePath
sc.Arguments = ""
sc.WorkingDirectory = root
sc.Description = "SS Transcribe-Translate"
If fso.FileExists(fso.BuildPath(root, "SS-Transcribe-Translate.ico")) Then
  sc.IconLocation = fso.BuildPath(root, "SS-Transcribe-Translate.ico")
Else
  sc.IconLocation = exePath & ",0"
End If
sc.Save()

desktopDir = sh.SpecialFolders("Desktop")
desktopShortcutPath = fso.BuildPath(desktopDir, "SS Transcribe-Translate.lnk")
Set dsc = ws.CreateShortcut(desktopShortcutPath)
dsc.TargetPath = exePath
dsc.Arguments = ""
dsc.WorkingDirectory = root
dsc.Description = "SS Transcribe-Translate"
If fso.FileExists(fso.BuildPath(root, "SS-Transcribe-Translate.ico")) Then
  dsc.IconLocation = fso.BuildPath(root, "SS-Transcribe-Translate.ico")
Else
  dsc.IconLocation = exePath & ",0"
End If
dsc.Save()

oldConsole = fso.BuildPath(startDir, "SS Transcribe-Translate - Console.lnk")
If fso.FileExists(oldConsole) Then fso.DeleteFile oldConsole, True

' Ask Windows to pin the real Start Menu shortcut.
' Windows 11 may suppress this shell verb; in that case the Start Menu shortcut remains available.
On Error Resume Next
Set startFolder = shellApp.Namespace(startDir)
If Not startFolder Is Nothing Then
  Set startItem = startFolder.ParseName(fso.GetFileName(shortcutPath))
  If Not startItem Is Nothing Then
    Set verbs = startItem.Verbs
    For Each verb In verbs
      verbText = LCase(Trim(Replace(verb.Name, "&", "")))
      If InStr(verbText, "pin to taskbar") > 0 Or _
         InStr(verbText, "pin to taskbar") > 0 Or _
         InStr(verbText, "anclar a la barra") > 0 Or _
         InStr(verbText, "barra de tareas") > 0 Then
        verb.DoIt
        pinAttempted = True
        pinned = True
        Exit For
      End If
    Next
  End If
End If
On Error GoTo 0

' Launch the packaged Windows GUI application, never the console launcher.
sh.CurrentDirectory = root
sh.Run """" & exePath & """", 0, False
WScript.Quit 0
