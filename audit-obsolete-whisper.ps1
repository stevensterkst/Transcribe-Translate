$ErrorActionPreference = "Stop"
Write-Host "=== READ-ONLY OBSOLETE WHISPER/TORCH AUDIT ===" -ForegroundColor Cyan
Write-Host "NO files or packages will be deleted."

$packages = @("openai-whisper","torch","faster-whisper","ctranslate2","sherpa-onnx")
foreach ($p in $packages) {
  Write-Host ""
  Write-Host "=== PACKAGE: $p ===" -ForegroundColor Yellow

  # pip writes "Package(s) not found" to stderr when an optional package is absent.
  # Under PowerShell ErrorActionPreference=Stop, native stderr can otherwise become
  # a terminating NativeCommandError. That is an audit finding, not an audit failure.
  $oldNativeErrorAction = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  $show = @(& python -m pip show $p 2>$null)
  $pipExit = $LASTEXITCODE
  $ErrorActionPreference = $oldNativeErrorAction

  if ($pipExit -eq 0) {
    $show
  } else {
    Write-Host "NOT INSTALLED" -ForegroundColor DarkYellow
  }
}

$site = python -c "import site; print(site.getusersitepackages())"
Write-Host ""
Write-Host "Python user site: $site"

$targets = @("torch","whisper","openai_whisper","faster_whisper","ctranslate2","sherpa_onnx")
foreach ($t in $targets) {
  $p = Join-Path $site $t
  if (Test-Path $p) {
    $files = @(Get-ChildItem $p -Recurse -File -Force -ErrorAction SilentlyContinue)
    $bytes = ($files | Measure-Object Length -Sum).Sum
    $dir = Get-Item $p
    [pscustomobject]@{
      Path=$p
      MB=[math]::Round($bytes/1MB,1)
      GB=[math]::Round($bytes/1GB,3)
      Files=$files.Count
      CreationTime=$dir.CreationTime
      LastWriteTime=$dir.LastWriteTime
    }
  }
}

Write-Host ""
Write-Host "=== LARGEST OBSOLETE PACKAGE FILES ===" -ForegroundColor Yellow
foreach ($t in @("torch","whisper","openai_whisper")) {
  $p = Join-Path $site $t
  if (Test-Path $p) {
    Get-ChildItem $p -Recurse -File -Force -ErrorAction SilentlyContinue |
      Sort-Object Length -Descending |
      Select-Object -First 20 FullName,@{N="MB";E={[math]::Round($_.Length/1MB,1)}},CreationTime,LastWriteTime
  }
}

Write-Host ""
Write-Host "=== PIP CACHE ===" -ForegroundColor Yellow
python -m pip cache info
$pipCache = Join-Path (Join-Path $env:LOCALAPPDATA "pip") "cache"
if (Test-Path $pipCache) {
  Get-ChildItem $pipCache -Recurse -File -Force -ErrorAction SilentlyContinue |
    Measure-Object Length -Sum
}

Write-Host ""
Write-Host "=== HUGGING FACE CACHE TOP 50 FILES ===" -ForegroundColor Yellow
$hf = Join-Path (Join-Path $env:USERPROFILE ".cache") "huggingface"
if (Test-Path $hf) {
  Get-ChildItem $hf -Recurse -File -Force -ErrorAction SilentlyContinue |
    Sort-Object Length -Descending |
    Select-Object -First 50 FullName,@{N="MB";E={[math]::Round($_.Length/1MB,1)}},CreationTime,LastWriteTime
}

Write-Host ""
Write-Host "=== REPO IMPORT SEARCH ===" -ForegroundColor Yellow
$repo = Split-Path $PSScriptRoot -Parent
$patterns = @("import torch","from torch","import whisper","from whisper","import whisperx","from whisperx","import faster_whisper","from faster_whisper","import ctranslate2","from ctranslate2","import sherpa_onnx","from sherpa_onnx")
Get-ChildItem $repo -Recurse -File -Include *.py,*.ps1,*.bat,*.toml,*.txt -ErrorAction SilentlyContinue |
  Select-String -Pattern $patterns |
  Select-Object Path,LineNumber,Line

Write-Host ""
Write-Host "AUDIT COMPLETE - this script made no changes." -ForegroundColor Green
