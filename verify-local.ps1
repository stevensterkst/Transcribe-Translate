param(
  [Parameter(Mandatory=$true)]
  [string]$Media,
  [string]$OllamaModel = ""
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "=== SS TRANSCRIBE-TRANSLATE REAL LOCAL VERIFICATION ===" -ForegroundColor Cyan
Write-Host "Application directory: $PSScriptRoot"

Write-Host "This verifier requires an explicit user-selected recording; it will not select browser caches or arbitrary newest files." -ForegroundColor Yellow

$mediaPath = (Resolve-Path -LiteralPath $Media -ErrorAction Stop).Path
Write-Host "Media: $mediaPath"

$pkgCheck = @"
import faster_whisper
import ctranslate2
import requests
print("Python packages: OK")
print("faster-whisper:", getattr(faster_whisper, "__version__", "installed"))
print("ctranslate2:", getattr(ctranslate2, "__version__", "installed"))
try:
 import sherpa_onnx; print("sherpa-onnx:", getattr(sherpa_onnx, "__version__", "installed"))
except ImportError: print("sherpa-onnx: NOT INSTALLED")
"@
$pkgCheck | python -
if ($LASTEXITCODE -ne 0) { throw "Required Python package import test failed." }

$ff = Get-Command ffmpeg -ErrorAction SilentlyContinue
if (-not $ff) {
  $ffCandidates = @(Get-ChildItem "C:/Program Files" -Directory -Filter "FFmpeg*" -ErrorAction SilentlyContinue |
    ForEach-Object { Join-Path $_.FullName "bin/ffmpeg.exe" } |
    Where-Object { Test-Path $_ })
  if ($ffCandidates.Count -gt 0) {
    $ffPath = $ffCandidates[0]
    $env:Path = (Split-Path $ffPath -Parent) + ";" + $env:Path
    $ff = Get-Command ffmpeg -ErrorAction SilentlyContinue
  }
}
if (-not $ff) { throw "FFmpeg was not found on PATH or in C:/Program Files/FFmpeg*/bin." }
Write-Host "FFmpeg: $($ff.Source)" -ForegroundColor Green

try { $ollama = Invoke-RestMethod "http://127.0.0.1:11434/api/tags" -TimeoutSec 10 }
catch { throw "Ollama is not reachable at http://127.0.0.1:11434" }
$models = @($ollama.models | ForEach-Object { $_.name }) | Where-Object { $_ }
if ($models.Count -eq 0) { throw "Ollama is reachable but reports no installed models." }
Write-Host "Ollama models: $($models -join ', ')" -ForegroundColor Green

if (-not $OllamaModel) {
  if ($models -contains "phi4-mini:3.8b") { $OllamaModel = "phi4-mini:3.8b" }
  elseif ($models -contains "qwen3:1.7b") { $OllamaModel = "qwen3:1.7b" }
  else { $OllamaModel = $models[0] }
  Write-Host "No verification model supplied; using $OllamaModel for the real job." -ForegroundColor Yellow
}
if ($models -notcontains $OllamaModel) { throw "Requested Ollama model is not installed: $OllamaModel" }

Write-Host ""
Write-Host "=== OLLAMA MODEL SMOKE TESTS ===" -ForegroundColor Yellow
foreach ($m in $models) {
  $body = @{model=$m; messages=@(@{role="user"; content="Reply with exactly OK."}); stream=$false; options=@{temperature=0}} | ConvertTo-Json -Depth 5
  try {
    $reply = Invoke-RestMethod "http://127.0.0.1:11434/api/chat" -Method Post -ContentType "application/json" -Body $body -TimeoutSec 300
    $content = [string]$reply.message.content
    if (-not $content.Trim()) { throw "empty response" }
    Write-Host "PASS $m -> $($content.Trim())" -ForegroundColor Green
  } catch { throw "Ollama model smoke test failed for $m : $($_.Exception.Message)" }
}

$requiredFiles = @("core/asr.py","core/config.py","core/text.py","core/pipeline.py","core/outputs.py","core/media.py","core/search.py","core/diarization.py","app.py")
foreach($name in $requiredFiles) { if (-not (Test-Path $name)) { throw "Missing application file: $name" } }

$source = Get-Content "core/pipeline.py" -Raw
$asr = Get-Content "core/asr.py" -Raw
$gui = Get-Content "app.py" -Raw
$text = Get-Content "core/text.py" -Raw
$allPython = (Get-ChildItem app.py,core -Recurse -File -Filter *.py | Get-Content -Raw) -join "`n"
$diar = Get-Content "core/diarization.py" -Raw
$batch = Get-Content "core/batch.py" -Raw
$library = Get-Content "core/library.py" -Raw
$player = Get-Content "core/player.py" -Raw
python -m unittest discover -s tests -p "test_*.py" -v
if($LASTEXITCODE -ne 0){ throw "Python unit tests failed." }

$checks = @(
  @($source, "source_summary", "Source-summary stage"),
  @($source, "translate_summary_to_english", "English-summary translation stage"),

  @($asr, "word_timestamps", "Word timestamps"),
  @($asr, "hotwords", "Hotwords"),
  @($gui, "Vocabulary / names", "Vocabulary GUI"),
  @($gui, "Search transcript", "Search GUI"),
  @($gui, "Transcript-grounded Q&A", "Q&A GUI"),
  @($gui, "Enable speaker diarization", "Diarization GUI"),
  @($text, "ask_transcript", "Q&A backend"),
  @($text, "chunk_text", "Long-form chunking"),
  @($diar, "OfflineSpeakerDiarization", "Offline diarization backend"),
  @($batch, "run_batch", "Batch processing backend"),
  @($library, "search_jobs", "Persistent searchable library"),
  @($player, "write_player", "Synchronized transcript player"),
  @($asr, "zero speech segments", "Empty-transcript safety")
)
foreach($check in $checks) {
  if ($check[0] -notmatch [regex]::Escape($check[1])) { throw "Architecture check failed: $($check[2])" }
}
$forbiddenOpenAI = @("import openai","from openai","api.openai.com","client.responses","client.chat.completions")
foreach($needle in $forbiddenOpenAI) {
  if($allPython -match [regex]::Escape($needle)) { throw "Architecture check failed: forbidden OpenAI runtime reference: $needle" }
}
Write-Host "Architecture checks: PASS (local/Ollama runtime; no OpenAI runtime dependency)" -ForegroundColor Green

$env:SS_VERIFY_MEDIA = $mediaPath
$env:SS_VERIFY_OLLAMA_MODEL = $OllamaModel
$out = Join-Path $HOME "Downloads\Transcribe-Translate\_verification"
if (-not (Test-Path $out)) { New-Item -ItemType Directory -Path $out | Out-Null }

Write-Host ""
Write-Host "=== REAL END-TO-END LOCAL JOB ===" -ForegroundColor Cyan
$runCode = @"
import os, sys
from pathlib import Path
sys.path.insert(0, ".")
from core.config import load_config
from core.pipeline import run_job
cfg = load_config()
cfg.ollama_model = os.environ["SS_VERIFY_OLLAMA_MODEL"]
cfg.analysis = True
cfg.word_timestamps = True
cfg.search_query = ""
cfg.qa_question = ""
job = run_job(os.environ["SS_VERIFY_MEDIA"], cfg, Path(os.environ["SS_VERIFY_OUTPUT"]) if os.environ.get("SS_VERIFY_OUTPUT") else Path("output"), print)
print("JOB_OUTPUT=" + str(job))
"@
$env:SS_VERIFY_OUTPUT = (Resolve-Path $out).Path
$runCode | python -
if ($LASTEXITCODE -ne 0) { throw "The real local pipeline failed." }

$latest = Get-ChildItem $out -Directory | Where-Object { $_.Name -notlike "_*" } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $latest) { throw "No output directory was created." }

$expected = @("original.txt","original.json","original.srt","original.vtt","transcript.md","segments.csv","source_summary.md","english_summary.md","search_report.json","job.json","output_manifest.json","analysis.md")
foreach($name in $expected) {
  $p = Join-Path $latest.FullName $name
  if (-not (Test-Path $p)) { throw "Missing expected output: $name" }
  $size = (Get-Item $p).Length
  if ($size -le 0) { throw "Empty expected output: $name" }
  Write-Host "OK  $name ($size bytes)" -ForegroundColor Green
}

$json = Get-Content (Join-Path $latest.FullName "original.json") -Raw | ConvertFrom-Json
if (-not $json.text -or -not $json.text.Trim()) { throw "Original JSON transcript text is empty." }
if (-not $json.segments -or @($json.segments).Count -eq 0) { throw "Original JSON contains no transcript segments." }

$job = Get-Content (Join-Path $latest.FullName "job.json") -Raw | ConvertFrom-Json
if ($job.api_cost -notlike "*no OpenAI API*") { throw "Zero-API assertion missing." }
if ($job.source_summary -ne "generated from original-language transcript") { throw "Source-summary provenance is wrong." }
if ($job.english_summary -ne "translation of source-language summary") { throw "English-summary provenance is wrong." }
if ($job.text_model -ne $OllamaModel) { throw "Recorded Ollama model does not match selected model." }

$original = Get-Content (Join-Path $latest.FullName "original.txt") -Raw
$sourceSummary = Get-Content (Join-Path $latest.FullName "source_summary.md") -Raw
$englishSummary = Get-Content (Join-Path $latest.FullName "english_summary.md") -Raw
if (-not $original.Trim()) { throw "Original transcript is empty." }
if (-not $sourceSummary.Trim()) { throw "Source summary is empty." }
if (-not $englishSummary.Trim()) { throw "English summary is empty." }

Write-Host ""
Write-Host "PASS: REAL LOCAL END-TO-END PIPELINE COMPLETED." -ForegroundColor Green
Write-Host "Job directory: $($latest.FullName)"
Write-Host "Selected Ollama model: $OllamaModel"
Write-Host "OpenAI API: NOT USED BY THIS APPLICATION"
