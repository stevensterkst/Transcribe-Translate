@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title SS Transcribe-Translate - FINAL SETUP AND TEST
echo ============================================================
echo SS TRANSCRIBE-TRANSLATE - FINAL SETUP / BUILD / TEST
echo ============================================================
echo Folder: %CD%
echo.
echo This window is intentionally kept open. All output is visible here.
echo.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -NoExit -File "%~dp0finish-local.ps1"
set "RC=%ERRORLEVEL%"
echo.
echo ============================================================
if not "%RC%"=="0" (
  echo FINAL RUN FAILED - exit code %RC%
) else (
  echo FINAL RUN FINISHED
)
echo ============================================================
pause
exit /b %RC%
