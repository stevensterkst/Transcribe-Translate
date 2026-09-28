$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot

$py=(Get-Command python -ErrorAction Stop).Source
$pyi=Get-Command pyinstaller -ErrorAction SilentlyContinue
if(-not $pyi){
  & $py -m PyInstaller --version *> $null
  if($LASTEXITCODE -ne 0){
    Write-Host "PyInstaller not found; installing it for the build..."
    & $py -m pip install pyinstaller
    if($LASTEXITCODE){throw "PyInstaller installation failed."}
  }
}

# Stop a previously launched copy of this application before replacing its bundled DLL/PYD files.
$running = Get-Process -Name "SS-Transcribe-Translate" -ErrorAction SilentlyContinue
if($running){
  Write-Host "A previous SS-Transcribe-Translate instance is running; closing it for a clean rebuild..."
  $running | Stop-Process -Force -ErrorAction SilentlyContinue
  Start-Sleep -Milliseconds 800
}
# Remove old build outputs. Retry because Windows can briefly retain a DLL/PYD handle after process exit.
foreach($target in @("build","dist")){
  if(Test-Path $target){
    $removed=$false
    for($attempt=1;$attempt -le 5;$attempt++){
      try {
        Remove-Item -LiteralPath $target -Recurse -Force -ErrorAction Stop
        $removed=$true
        break
      } catch {
        if($attempt -eq 5){
          throw "Cannot remove '$target'. A process (possibly antivirus/indexing software) is still locking a build file. Close SS-Transcribe-Translate and retry. Original error: $($_.Exception.Message)"
        }
        Start-Sleep -Milliseconds (500 * $attempt)
      }
    }
    if(!$removed){throw "Failed to remove old $target directory."}
  }
}
& $py -m PyInstaller --noconfirm --clean --onedir --windowed --name "SS-Transcribe-Translate" --collect-all sherpa_onnx --collect-all faster_whisper --collect-all ctranslate2 app.py
if($LASTEXITCODE){throw "PyInstaller build failed."}

$bundle=Join-Path $PSScriptRoot "dist\SS-Transcribe-Translate"
Copy-Item config.json $bundle -Force
if(Test-Path config.local.json){Copy-Item config.local.json $bundle -Force}
if(Test-Path "models\diarization"){
  New-Item -ItemType Directory -Force (Join-Path $bundle "models") | Out-Null
  Copy-Item "models\diarization" (Join-Path $bundle "models") -Recurse -Force
}
if(Test-Path "runtime\deno.exe"){
  New-Item -ItemType Directory -Force (Join-Path $bundle "runtime") | Out-Null
  Copy-Item "runtime\deno.exe" (Join-Path $bundle "runtime\deno.exe") -Force
}
if(Test-Path "SS-Transcribe-Translate.ico"){Copy-Item "SS-Transcribe-Translate.ico" $bundle -Force}

$exe=Join-Path $bundle "SS-Transcribe-Translate.exe"
if(!(Test-Path $exe)){throw "Windows EXE missing after build."}
Write-Host "Windows app built: $exe" -ForegroundColor Green
