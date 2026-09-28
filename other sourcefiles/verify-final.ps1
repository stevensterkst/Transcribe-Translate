$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$log=Join-Path $PSScriptRoot ("FINAL-AUDIT-"+(Get-Date -Format "yyyyMMdd-HHmmss")+".log")
Start-Transcript -Path $log -Force | Out-Null
try {
  Write-Host "=== SS TRANSCRIBE-TRANSLATE FINAL SOURCE/BUILD AUDIT ==="
  git rev-parse HEAD
  & (Get-Command python).Source -m compileall -q app.py core tests
  if($LASTEXITCODE){throw "Python compileall FAILED"}
  python -m unittest discover -s tests -p "test_*.py" -v
  if($LASTEXITCODE){throw "Python unit tests FAILED"}
  Write-Host "PASS: Python compileall + unit tests"

  $importCheck = Join-Path $env:TEMP "ss_transcribe_import_check.py"
  @'
import faster_whisper
import ctranslate2
import requests
import yt_dlp
import sherpa_onnx
print("runtime imports OK")
'@ | Set-Content -LiteralPath $importCheck -Encoding utf8
  & (Get-Command python).Source $importCheck
  $importExit=$LASTEXITCODE
  Remove-Item -LiteralPath $importCheck -Force -ErrorAction SilentlyContinue
  if($importExit){throw "Runtime imports FAILED"}
  Write-Host "PASS: required local runtime imports"

  $bad=Get-ChildItem app.py,core -Recurse -File -Filter *.py | Select-String -Pattern '(^|\s)(import|from) (torch|whisper|whisperx|torchaudio|pyannote)(\s|$)'
  if($bad){$bad;throw "Obsolete runtime import found"}
  $asr=Get-Content core/asr.py -Raw
  $pipeline=Get-Content core/pipeline.py -Raw
  $text=Get-Content core/text.py -Raw
  if($asr -notmatch 'BatchedInferencePipeline'){throw "Batched ASR missing"}
  if($asr -notmatch 'batch_size'){throw "Adaptive batch sizing missing"}
  if($pipeline -notmatch 'finally:'){throw "Guaranteed cleanup missing"}
  if($pipeline -notmatch 'shutil\.rmtree\(work, ignore_errors=True\)'){throw "Temporary media cleanup missing"}
  if($text -notmatch 'api/chat'){throw "Ollama provider missing"}
  $query=Get-Content core/query.py -Raw
  if($query -notmatch 'ask_ollama'){throw "Transcript-grounded Ollama Q&A missing"}
  Write-Host "PASS: architecture checks"
  $featureFiles = @{
    "Caption-first remote transcript path" = @("core/captions.py","scrape_transcript")
    "Local faster-whisper batched ASR" = @("core/asr.py","BatchedInferencePipeline")
    "Adaptive ASR batch sizing" = @("core/asr.py","batch_size")
    "Source-language summary" = @("core/pipeline.py","source_summary")
    "English summary" = @("core/pipeline.py","english_summary")
    "Optional translation" = @("core/pipeline.py","translate_summary_to_english")
    "Ollama local provider" = @("core/text.py","api/chat")
    "Source-grounded analysis" = @("core/text.py","analysis")
    "Transcript-grounded Q&A" = @("core/text.py","ask_transcript")
    "Search/report" = @("core/search.py","search")
    "Speaker diarization" = @("core/diarization.py","OfflineSpeakerDiarization")
    "Batch processing" = @("core/batch.py","run_batch")
    "Persistent library" = @("core/library.py","search_jobs")
    "Watch folder" = @("core/watch.py","watch_folder")
    "Synchronized transcript player" = @("core/player.py","write_player")
    "Structured output manifest" = @("core/outputs.py","output_manifest")
  }
  foreach($feature in $featureFiles.GetEnumerator()){
    $f=Get-Content $feature.Value[0] -Raw
    if($f -notmatch [regex]::Escape($feature.Value[1])){throw "Required feature missing: $($feature.Key)"}
  }
  $ui=Get-Content app.py -Raw
  $uiChecks=@{
    "Source language"="Source language"
    "Whisper model"="Whisper model"
    "Ollama model"="Ollama model"
    "Word timestamps"="word-level timestamps"
    "Source-grounded analysis"="source-grounded meeting/evidence analysis"
    "Analysis language"="Analysis language"
    "Transcript-grounded Q&A"="Transcript-grounded Q&A"
    "Target language"="Target language"
    "Full transcript translation"="translate the FULL source transcript"
    "Speaker diarization"="speaker diarization"
    "Batch"="Batch folder"
    "Library"="Library"
    "Watch"="Watch folder"
    "Transcription range"="Transcription range"
  }
  foreach($name in $uiChecks.Keys){
    if($ui -notmatch [regex]::Escape($uiChecks[$name])){throw "Required GUI control/feature marker missing: $name"}
  }
  $out=Get-Content core/outputs.py -Raw
  foreach($artifact in @("original.txt","original.json","original.srt","original.vtt","transcript.md","segments.csv","source_summary.md","english_summary.md","output_manifest.json","translation.txt","analysis_source.md","analysis.md","qa.md","search_report.json")){
    if($out -notmatch [regex]::Escape($artifact)){throw "Required output artifact marker missing: $artifact"}
  }
  Write-Host "PASS: agreed feature coverage + GUI/output checks"
  $cfg=Get-Content config.json -Raw
  if($cfg -notmatch '"range"'){throw "Tracked config missing range defaults"}
  $app=Get-Content app.py -Raw
  $pipe=Get-Content core/pipeline.py -Raw
  $media=Get-Content core/media.py -Raw
  $caps=Get-Content core/captions.py -Raw
  if($app -notmatch 'range_mode' -or $app -notmatch 'range_value'){throw "GUI transcription range controls missing"}
  if($pipe -notmatch '_range_seconds' -or $pipe -notmatch 'extract_audio\(media, work / "audio.wav", limit\)'){throw "Pipeline range integration missing"}
  if($media -notmatch 'max_seconds'){throw "Media range extraction missing"}
  if($caps -notmatch 'range_mode' -or $caps -notmatch 'range_value'){throw "Remote caption range integration missing"}
  if((Get-Content tests/test_ranges.py -Raw) -notmatch 'test_first_percent'){throw "Range regression tests missing"}
  $launcher=Get-Content START-APP.vbs -Raw
  if($launcher -match "git -C"){throw "Start launcher must not run git pull on every application launch"}
  if($launcher -notmatch 'SS-Transcribe-Translate\.exe'){throw "Start launcher does not target packaged EXE"}
  if((Get-Content START-APP.vbs -Raw) -notmatch 'exePath'){throw "Launcher EXE path declaration missing"}
  if(!(Test-Path "CONSOLE.cmd")){throw "Console launcher missing"}
  if(!(Test-Path "AGENTS.md")){throw "AGENTS.md missing"}
  Write-Host "PASS: range, launcher, console and AI coordination checks"

  Write-Host "PASS: source/feature verification complete; starting clean Windows EXE build"
  & (Join-Path $PSScriptRoot "build-exe.ps1")
  if($LASTEXITCODE){throw "Windows build script FAILED"}
  $exe=Join-Path $PSScriptRoot "dist\SS-Transcribe-Translate\SS-Transcribe-Translate.exe"
  if(!(Test-Path $exe)){throw "EXE missing"}
  $bundle=Join-Path $PSScriptRoot "dist\SS-Transcribe-Translate"
  if(!(Test-Path (Join-Path $bundle "config.json"))){throw "Packaged config.json missing"}
  if((Test-Path "runtime\deno.exe") -and !(Test-Path (Join-Path $bundle "runtime\deno.exe"))){throw "Packaged Deno runtime missing"}
  $hash=(Get-FileHash $exe -Algorithm SHA256).Hash
  "SS-Transcribe-Translate.exe SHA256  $hash" | Set-Content (Join-Path $bundle "SHA256.txt") -Encoding utf8
  Copy-Item (Join-Path $bundle "SHA256.txt") (Join-Path $PSScriptRoot "SHA256.txt") -Force
  Write-Host "PASS: Windows EXE built"
  Write-Host "EXE: $exe"
  Write-Host "SHA256: $hash"
  Write-Host "=== AUDIT PASS ==="
} catch {
  Write-Host "=== AUDIT FAIL ==="
  Write-Host $_
  exit 1
} finally { Stop-Transcript | Out-Null }