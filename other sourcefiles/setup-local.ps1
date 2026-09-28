$ErrorActionPreference="Stop"
Set-Location $PSScriptRoot
$py=(Get-Command python -ErrorAction Stop).Source
Write-Host "SS Transcribe-Translate local setup" -ForegroundColor Cyan
Write-Host "Installing only local runtime dependencies: faster-whisper/CTranslate2, sherpa-onnx, yt-dlp+EJS."
& $py -m pip install -r (Join-Path $PSScriptRoot "requirements.txt")
if($LASTEXITCODE){throw "Python dependency installation failed."}

$runtime=Join-Path $PSScriptRoot "runtime"; New-Item -ItemType Directory -Force $runtime | Out-Null
$deno=Join-Path $runtime "deno.exe"
if(!(Test-Path $deno)){
  $api=Invoke-RestMethod "https://api.github.com/repos/denoland/deno/releases/latest"
  $asset=$api.assets | Where-Object {$_.name -eq "deno-x86_64-pc-windows-msvc.zip"} | Select-Object -First 1
  if(!$asset){throw "Could not find current Windows x64 Deno release."}
  $zip=Join-Path $env:TEMP "ss-deno.zip"; Invoke-WebRequest $asset.browser_download_url -OutFile $zip
  Expand-Archive $zip -DestinationPath $runtime -Force; Remove-Item $zip -Force
}
$env:PATH="$runtime;$env:PATH"
Write-Host (& $deno --version | Select-Object -First 1)

$models=Join-Path $PSScriptRoot "models\diarization"; New-Item -ItemType Directory -Force $models | Out-Null
$segDir=Join-Path $models "sherpa-onnx-pyannote-segmentation-3-0"
$segArchive=Join-Path $env:TEMP "sherpa-seg.tar.bz2"
if(!(Test-Path (Join-Path $segDir "model.onnx"))){
  Invoke-WebRequest "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-segmentation-models/sherpa-onnx-pyannote-segmentation-3-0.tar.bz2" -OutFile $segArchive
  & $py -c "import tarfile,sys; tarfile.open(sys.argv[1],'r:bz2').extractall(sys.argv[2])" $segArchive $models
  Remove-Item $segArchive -Force
}
$emb=Join-Path $models "3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"
if(!(Test-Path $emb)){
  Invoke-WebRequest "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx" -OutFile $emb
}

$local=Join-Path $PSScriptRoot "config.local.json"
# Windows PowerShell 5.1 does not support ConvertFrom-Json -AsHashtable.
# Preserve existing local settings and update only diarization.
if(Test-Path $local){ $data=Get-Content $local -Raw | ConvertFrom-Json } else { $data=[pscustomobject]@{} }
if(-not $data.PSObject.Properties["diarization"]){ $data | Add-Member -MemberType NoteProperty -Name diarization -Value ([pscustomobject]@{}) }
$diar=$data.diarization
foreach($name in @("enabled","segmentation_model","embedding_model","num_speakers","cluster_threshold")){
  if(-not $diar.PSObject.Properties[$name]){ $diar | Add-Member -MemberType NoteProperty -Name $name -Value $null }
}
$diar.enabled=if($diar.enabled -eq $null){$false}else{[bool]$diar.enabled}
$diar.segmentation_model=(Join-Path $segDir "model.onnx")
$diar.embedding_model=$emb
$diar.num_speakers=0
$diar.cluster_threshold=0.5
$json = $data | ConvertTo-Json -Depth 12
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($local, $json, $utf8NoBom)
Write-Host "Diarization installed/configured: PASS" -ForegroundColor Green
Write-Host "Deno installed locally in: $runtime"
Write-Host "No Torch, WhisperX, FFmpeg or standalone yt-dlp.exe was installed or changed."
