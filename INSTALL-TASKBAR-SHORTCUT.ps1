$ErrorActionPreference = "Stop"
$root = (Resolve-Path -LiteralPath $PSScriptRoot).Path
$icon = Join-Path $root "SS-Transcribe-Translate.ico"
$exe = Join-Path $root "SS-Transcribe-Translate.exe"
if (-not (Test-Path -LiteralPath $exe)) {
    $exe = Join-Path $root "dist\SS-Transcribe-Translate\SS-Transcribe-Translate.exe"
}
if (-not (Test-Path -LiteralPath $exe)) {
    throw "Packaged EXE not found. Extract the complete Windows bundle first. Checked: $root and dist\SS-Transcribe-Translate."
}
$exe = (Resolve-Path -LiteralPath $exe).Path
$working = Split-Path -Parent $exe
$wsh = New-Object -ComObject WScript.Shell
$startMenu = Join-Path ([Environment]::GetFolderPath("StartMenu")) "Programs\SS Transcribe-Translate"
$desktop = [Environment]::GetFolderPath("Desktop")
New-Item -ItemType Directory -Force -Path $startMenu | Out-Null

function Set-SSShortcut([string]$Path) {
    $sc = $wsh.CreateShortcut($Path)
    $sc.TargetPath = $exe
    $sc.Arguments = ""
    $sc.WorkingDirectory = $working
    $sc.Description = "SS Transcribe-Translate — verified Windows GUI"
    if (Test-Path -LiteralPath $icon) { $sc.IconLocation = "$icon,0" }
    else { $sc.IconLocation = "$exe,0" }
    $sc.Save()
    $check = $wsh.CreateShortcut($Path)
    if ($check.TargetPath -ne $exe -or $check.Arguments -ne "" -or $check.WorkingDirectory -ne $working) {
        throw "Shortcut verification failed: $Path"
    }
}

$startShortcut = Join-Path $startMenu "SS Transcribe-Translate.lnk"
$desktopShortcut = Join-Path $desktop "SS Transcribe-Translate.lnk"
Set-SSShortcut $startShortcut
Set-SSShortcut $desktopShortcut

# Windows controls pinning. We can repair existing shortcut files, but do not
# claim a taskbar pin succeeded merely because a file was copied.
$taskbarDir = Join-Path $env:APPDATA "Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar"
$taskbarUpdated = $false
if (Test-Path -LiteralPath $taskbarDir) {
    foreach ($old in (Get-ChildItem -LiteralPath $taskbarDir -Filter "*.lnk" -File -ErrorAction SilentlyContinue)) {
        $oldSc = $wsh.CreateShortcut($old.FullName)
        $isOurs = $old.BaseName -match "(?i)^(Transcription|Transcribe-Translate|SS Transcribe-Translate)$" -or
            $oldSc.TargetPath -match "(?i)transcribe-translate|START-APP\.(cmd|vbs)"
        if ($isOurs) {
            Set-SSShortcut $old.FullName
            $taskbarUpdated = $true
        }
    }
}
Write-Host "PASS: Start Menu shortcut verified: $startShortcut"
Write-Host "PASS: Desktop shortcut verified: $desktopShortcut"
Write-Host "PASS: direct target = $exe"
if ($taskbarUpdated) {
    Write-Host "PASS: existing matching taskbar shortcut file updated."
    Write-Host "If Windows still displays stale cached metadata, unpin the old icon and pin the Start Menu entry."
} else {
    Write-Host "INFO: no matching pinned taskbar shortcut found. Pin 'SS Transcribe-Translate' from Start Menu."
}
Write-Host "Working directory: $working"
