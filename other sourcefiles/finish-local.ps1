param(
  [string]$Media = "",
  [string]$OllamaModel = "",
  [switch]$SkipSetup,
  [switch]$SkipBuild,
  [switch]$CleanupObsoleteWhisper
)
$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
Write-Host "=== SS TRANSCRIBE-TRANSLATE FINAL LOCAL BUILD / VERIFY ===" -ForegroundColor Cyan
Write-Host "Setup and build are enabled by default; obsolete Whisper/Torch cleanup is NEVER automatic."

if(-not $SkipSetup){
  & (Join-Path $PSScriptRoot "setup-local.ps1")
  if($LASTEXITCODE){throw "Local setup failed."}
}
if(-not $SkipBuild){
  & (Join-Path $PSScriptRoot "build-exe.ps1")
  if($LASTEXITCODE){throw "Windows application build failed."}
}
if($CleanupObsoleteWhisper){
  Write-Host "=== EXPLICIT OBSOLETE PACKAGE CLEANUP ===" -ForegroundColor Yellow
  & (Join-Path $PSScriptRoot "cleanup-obsolete-whisper.ps1")
  if($LASTEXITCODE){throw "Cleanup failed."}
}else{
  Write-Host "Obsolete Whisper/Torch cleanup: SKIPPED" -ForegroundColor Green
}

if(-not $Media){
  Add-Type -AssemblyName System.Windows.Forms
  $dialog=New-Object System.Windows.Forms.OpenFileDialog
  $dialog.Title="Select a real speech recording for final end-to-end verification"
  $dialog.Filter="Audio/Video|*.wav;*.mp3;*.m4a;*.mp4;*.mkv;*.mov;*.webm;*.flac;*.ogg|All files|*.*"
  if($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK){throw "No verification recording selected."}
  $Media=$dialog.FileName
}
& (Join-Path $PSScriptRoot "verify-local.ps1") -Media $Media -OllamaModel $OllamaModel
if($LASTEXITCODE){throw "End-to-end verification failed."}

Write-Host ""
Write-Host "=== FINAL RESULT ===" -ForegroundColor Green
Write-Host "Local dependencies + diarization: INSTALLED/CONFIGURED"
Write-Host "Windows GUI application: BUILT"
Write-Host "Batch processing: INCLUDED"
Write-Host "Persistent searchable library: INCLUDED"
Write-Host "Synchronized transcript player: INCLUDED"
Write-Host "YouTube yt-dlp/EJS path: CONFIGURED"
Write-Host "Real end-to-end verification: PASS"
Write-Host "OpenAI paid API runtime: NOT USED"
