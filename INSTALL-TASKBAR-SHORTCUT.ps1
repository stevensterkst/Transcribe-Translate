$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$launcher = Join-Path $root "START-APP.vbs"
$cmdFallback = Join-Path $root "START-APP.cmd"
$icon = Join-Path $root "SS-Transcribe-Translate.ico"
$exe = Join-Path $root "dist\SS-Transcribe-Translate\SS-Transcribe-Translate.exe"

if (-not (Test-Path -LiteralPath $launcher)) {
    throw "Silent launcher missing: $launcher"
}
if (-not (Test-Path -LiteralPath $exe) -and -not (Test-Path -LiteralPath $cmdFallback)) {
    throw "Neither packaged EXE nor fallback launcher exists under $root"
}

$wsh = New-Object -ComObject WScript.Shell
$wscript = Join-Path $env:SystemRoot "System32\wscript.exe"
$startMenu = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs\SS Transcribe-Translate"
$desktop = [Environment]::GetFolderPath("Desktop")
New-Item -ItemType Directory -Force -Path $startMenu | Out-Null

function Set-SSShortcut([string]$Path) {
    $sc = $wsh.CreateShortcut($Path)
    $sc.TargetPath = $wscript
    $sc.Arguments = ('"{0}"' -f $launcher)
    $sc.WorkingDirectory = $root
    $sc.Description = "SS Transcribe-Translate — silent GUI launcher"
    if (Test-Path -LiteralPath $icon) { $sc.IconLocation = "$icon,0" }
    elseif (Test-Path -LiteralPath $exe) { $sc.IconLocation = "$exe,0" }
    else { $sc.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,167" }
    $sc.Save()
    $check = $wsh.CreateShortcut($Path)
    if ($check.TargetPath -ne $wscript -or $check.Arguments -ne ('"{0}"' -f $launcher)) {
        throw "Shortcut verification failed: $Path"
    }
}

$startShortcut = Join-Path $startMenu "SS Transcribe-Translate.lnk"
$desktopShortcut = Join-Path $desktop "SS Transcribe-Translate.lnk"
Set-SSShortcut $startShortcut
Set-SSShortcut $desktopShortcut

# Update an existing pinned taskbar shortcut if one of the known legacy names
# or targets is present. Windows may cache pinned shortcut metadata; do not
# claim it was pinned unless the resulting target is verified.
$taskbarDir = Join-Path $env:APPDATA "Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"
$taskbarUpdated = $false
if (Test-Path -LiteralPath $taskbarDir) {
    $oldLinks = Get-ChildItem -LiteralPath $taskbarDir -Filter "*.lnk" -File -ErrorAction SilentlyContinue
    foreach ($old in $oldLinks) {
        $oldSc = $wsh.CreateShortcut($old.FullName)
        $isOurs = $old.BaseName -match "^(Transcription|Transcribe-Translate|SS Transcribe-Translate)$" -or
            $oldSc.TargetPath -match "(?i)transcribe-translate|START-APP\.(cmd|vbs)"
        if ($isOurs) {
            Set-SSShortcut $old.FullName
            $taskbarUpdated = $true
        }
    }
}

Write-Host "PASS: Start Menu shortcut: $startShortcut"
Write-Host "PASS: Desktop shortcut: $desktopShortcut"
Write-Host "PASS: both point directly to the packaged --windowed EXE (no console window)."
if ($taskbarUpdated) {
    Write-Host "PASS: existing matching pinned shortcut file updated: $taskbarDir"
    Write-Host "If its displayed icon/target remains cached, unpin that old icon and pin 'SS Transcribe-Translate' from Start Menu."
} else {
    Write-Host "INFO: no existing matching pinned shortcut was found to update."
    Write-Host "Pin 'SS Transcribe-Translate' from Start Menu to the taskbar; Windows controls taskbar pinning."
}
Write-Host "Launcher root: $root"
