$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$start = [Environment]::GetFolderPath("StartMenu")
$dir = Join-Path $start "Programs\SS Transcribe-Translate"
New-Item -ItemType Directory -Force -Path $dir | Out-Null

$exe = Join-Path $root "dist\SS-Transcribe-Translate\SS-Transcribe-Translate.exe"
$fallback = Join-Path $root "START-APP.cmd"
if(-not (Test-Path $exe) -and -not (Test-Path $fallback)){
  throw "Neither packaged EXE nor START-APP.cmd was found."
}

$shortcut = Join-Path $dir "SS Transcribe-Translate.lnk"
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($shortcut)
if(Test-Path $exe){
  $sc.TargetPath = $exe
  $sc.Arguments = ""
}else{
  $sc.TargetPath = $fallback
  $sc.Arguments = ""
}
$sc.WorkingDirectory = $root
$sc.Description = "SS Transcribe-Translate - verified local Windows application"
$icon = Join-Path $root "SS-Transcribe-Translate.ico"
if(Test-Path $icon){ $sc.IconLocation = $icon } else { $sc.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,167" }
$sc.Save()

# Replace an old taskbar shortcut when Windows exposes it as an ordinary .lnk.
$taskbarDir = Join-Path $env:APPDATA "Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"
if(Test-Path $taskbarDir){
  $legacy = Get-ChildItem $taskbarDir -Filter "*.lnk" -ErrorAction SilentlyContinue |
    Where-Object {
      $_.BaseName -match "^(Transcription|Transcribe-Translate|SS Transcribe-Translate)$" -or
      ((New-Object -ComObject WScript.Shell).CreateShortcut($_.FullName).TargetPath -match "transcribe-translate\.ps1|start-app\.cmd")
    } | Select-Object -First 1
  if($legacy){
    Copy-Item $shortcut $legacy.FullName -Force
    Write-Host "Replaced legacy taskbar shortcut: $($legacy.Name)"
  }
}

Write-Host "Start Menu shortcut ready: $shortcut"
Write-Host "Target: $($sc.TargetPath)"
Write-Host "The shortcut launches the packaged EXE directly when it exists; it does not run git pull on application launch."
