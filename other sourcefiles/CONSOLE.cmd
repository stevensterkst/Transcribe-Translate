@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title SS Transcribe-Translate Console
:menu
cls
echo ============================================================
echo SS TRANSCRIBE-TRANSLATE
echo ============================================================
echo Repository: %CD%
echo.
echo [1] Start application
echo [2] Run final source/build audit
echo [3] Run local verification only
echo [4] Build Windows EXE
echo [5] Open repository in Explorer
echo [6] Exit
echo.
choice /C 123456 /N /M "Select: "
if errorlevel 6 exit /b 0
if errorlevel 5 start "" explorer "%CD%" & goto menu
if errorlevel 4 powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%CD%\build-exe.ps1" & pause & goto menu
if errorlevel 3 set /p "MEDIA=Full path to test audio/video: " & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%CD%\verify-local.ps1" -Media "%MEDIA%" & pause & goto menu
if errorlevel 2 powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%CD%\verify-final.ps1" & pause & goto menu
if errorlevel 1 start "" "%CD%\dist\SS-Transcribe-Translate\SS-Transcribe-Translate.exe" & goto menu
