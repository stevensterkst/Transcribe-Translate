param(
  [Parameter(Mandatory=$true)][string]$InputFolder,
  [string]$OllamaModel = ""
)
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path $InputFolder -PathType Container)) { throw "Input folder not found: $InputFolder" }
$exts = @(".mp4",".mkv",".mov",".avi",".webm",".m4v",".mp3",".m4a",".wav",".flac",".ogg")
$files = Get-ChildItem $InputFolder -File | Where-Object { $exts -contains $_.Extension.ToLowerInvariant() }
if (-not $files) { throw "No supported media files found in $InputFolder" }

Write-Host "=== SS Transcribe-Translate LOCAL BATCH ===" -ForegroundColor Cyan
Write-Host "Files: $($files.Count)"

foreach ($file in $files) {
  Write-Host ""
  Write-Host "--- $($file.Name) ---" -ForegroundColor Yellow
  if ($OllamaModel) {
    .\verify-local.ps1 -Media $file.FullName -OllamaModel $OllamaModel
  } else {
    throw "Specify -OllamaModel explicitly so batch processing never silently chooses a model."
  }
}
