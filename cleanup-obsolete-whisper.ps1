$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== OBSOLETE WHISPER/TORCH CLEANUP ===" -ForegroundColor Cyan
Write-Host "This script removes ONLY openai-whisper and torch after dependency checks."

function Get-PackageInfoText([string]$Name) {
  $oldNativeErrorAction = $ErrorActionPreference
  $ErrorActionPreference = "Continue"
  $result = @(& python -m pip show $Name 2>$null)
  $exitCode = $LASTEXITCODE
  $ErrorActionPreference = $oldNativeErrorAction
  if ($exitCode -eq 0) { return ($result -join [Environment]::NewLine) }
  return ""
}

Write-Host ""
Write-Host "=== BEFORE ===" -ForegroundColor Yellow
$whisperInfo = Get-PackageInfoText "openai-whisper"
$torchInfo = Get-PackageInfoText "torch"
if ($whisperInfo) { $whisperInfo } else { Write-Host "openai-whisper: NOT INSTALLED" }
if ($torchInfo) { $torchInfo } else { Write-Host "torch: NOT INSTALLED" }

$fasterInfo = Get-PackageInfoText "faster-whisper"
$ct2Info = Get-PackageInfoText "ctranslate2"
if (-not $fasterInfo) { throw "faster-whisper is missing. Refusing cleanup because the required transcription engine is not installed." }
if (-not $ct2Info) { throw "ctranslate2 is missing. Refusing cleanup because the required transcription engine is not installed." }

Write-Host ""
Write-Host "=== CHECKING TORCH REVERSE DEPENDENCY ===" -ForegroundColor Yellow
$reverseCheck = @'
import importlib.metadata as md
from packaging.requirements import Requirement
users = []
for dist in md.distributions():
    name = dist.metadata.get("Name") or ""
    if name.lower() in ("torch", "openai-whisper"):
        continue
    for raw in (dist.requires or []):
        try:
            req = Requirement(raw)
        except Exception:
            continue
        if req.name.lower() == "torch":
            users.append(name)
            break
for name in sorted(set(users), key=str.lower):
    print(name)
'@
$remainingTorchUsers = @(& python -c $reverseCheck)
if ($LASTEXITCODE -ne 0) { throw "Could not verify Torch reverse dependencies; refusing cleanup." }
if ($remainingTorchUsers.Count -gt 0) {
  throw ("REFUSING TO REMOVE Torch. Other installed packages declare Torch: " + ($remainingTorchUsers -join ", "))
}
Write-Host "No installed package declares Torch: safe to continue." -ForegroundColor Green
Write-Host ""
if ($whisperInfo) {
  Write-Host "Uninstalling obsolete openai-whisper..."
  python -m pip uninstall -y openai-whisper
  if ($LASTEXITCODE -ne 0) { throw "openai-whisper uninstall failed." }
} else {
  Write-Host "openai-whisper already absent." -ForegroundColor Green
}

if ($torchInfo) {
  Write-Host "Uninstalling obsolete torch..."
  python -m pip uninstall -y torch
  if ($LASTEXITCODE -ne 0) { throw "torch uninstall failed." }
} else {
  Write-Host "torch already absent." -ForegroundColor Green
}

Write-Host ""
Write-Host "=== REMOVING ONLY OBSOLETE PIP CACHE ENTRIES ===" -ForegroundColor Yellow
$oldNativeErrorAction = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& python -m pip cache remove torch 2>$null
& python -m pip cache remove openai-whisper 2>$null
$ErrorActionPreference = $oldNativeErrorAction

Write-Host ""
Write-Host "=== AFTER ===" -ForegroundColor Yellow
if (Get-PackageInfoText "openai-whisper") { throw "openai-whisper is still installed after cleanup." }
if (Get-PackageInfoText "torch") { throw "torch is still installed after cleanup." }
if (-not (Get-PackageInfoText "faster-whisper")) { throw "faster-whisper disappeared during cleanup." }
if (-not (Get-PackageInfoText "ctranslate2")) { throw "ctranslate2 disappeared during cleanup." }

Write-Host "openai-whisper: REMOVED" -ForegroundColor Green
Write-Host "torch: REMOVED" -ForegroundColor Green
Write-Host "faster-whisper: PRESENT" -ForegroundColor Green
Write-Host "ctranslate2: PRESENT" -ForegroundColor Green
Write-Host ""
Write-Host "FFmpeg, standalone yt-dlp, Python, Hugging Face cache and SS project files were not targeted." -ForegroundColor Green
