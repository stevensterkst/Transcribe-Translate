param([string]$Source)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$launcher = Join-Path $PSScriptRoot 'START-APP.vbs'
if (-not (Test-Path -LiteralPath $launcher -PathType Leaf)) { throw 'START-APP.vbs is missing.' }
if ($Source) {
  if (-not (Test-Path -LiteralPath $Source -PathType Leaf)) { throw ('Source media does not exist: ' + $Source) }
  $env:SS_TRANSCRIBE_SOURCE = (Resolve-Path -LiteralPath $Source).Path
}
# Compatibility entry point for old shortcuts. The real launcher is silent and uses pythonw.
& wscript.exe $launcher
exit 0
