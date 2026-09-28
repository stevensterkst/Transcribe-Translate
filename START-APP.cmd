@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if exist "%~dp0dist\SS-Transcribe-Translate\SS-Transcribe-Translate.exe" (
  start "" "%~dp0dist\SS-Transcribe-Translate\SS-Transcribe-Translate.exe"
  exit /b 0
)
if exist "C:\Python313\pythonw.exe" (
  start "" "C:\Python313\pythonw.exe" "%~dp0app.py"
  exit /b 0
)
where pythonw.exe >nul 2>&1
if not errorlevel 1 (
  start "" pythonw.exe "%~dp0app.py"
  exit /b 0
)
echo ERROR: Neither packaged EXE nor Python launcher was found.
pause
exit /b 2
