@echo off
setlocal
title Windows System Cleanup Utility v2.0
color 0b

:: Check for administrative privileges
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo [!] Requesting administrative privileges...
    powershell -Command "Start-Process -FilePath '%0' -Verb RunAs"
    exit /b
)

echo ======================================================
echo       WINDOWS SYSTEM CLEANUP UTILITY (ADMIN)
echo ======================================================
echo.
echo This script will purge temporary files, caches, and system logs.
echo This will NOT affect your personal documents or browser history.
echo.
pause

echo.
echo [*] Cleaning Windows Temp directory...
del /q /f /s "C:\Windows\Temp\*.*" >nul 2>&1
for /d %%p in ("C:\Windows\Temp\*") do rd /s /q "%%p" >nul 2>&1

echo [*] Cleaning User Temp directory...
del /q /f /s "%temp%\*.*" >nul 2>&1
for /d %%p in ("%temp%\*") do rd /s /q "%%p" >nul 2>&1

echo [*] Purging Prefetch cache...
del /q /f /s "C:\Windows\Prefetch\*.*" >nul 2>&1

echo [*] Clearing SoftwareDistribution (Update) cache...
net stop wuauserv >nul 2>&1
del /q /f /s "C:\Windows\SoftwareDistribution\Download\*.*" >nul 2>&1
net start wuauserv >nul 2>&1

echo [*] Flushing DNS cache...
ipconfig /flushdns >nul 2>&1

echo [*] Cleaning Thumbnail cache...
del /f /s /q /a "%LocalAppData%\Microsoft\Windows\Explorer\thumbcache_*.db" >nul 2>&1

echo [*] Purging System Event Logs...
for /F "tokens=*" %%G in ('wevtutil.exe el') DO (wevtutil.exe cl "%%G" 2>nul)

echo [*] Running DISM Component Store Cleanup (Background)...
start /b Dism.exe /online /Cleanup-Image /StartComponentCleanup /NoRestart >nul 2>&1

echo.
echo ======================================================
echo Cleanup cycle finished.
echo Note: Some files may remain if they are currently locked by the OS.
echo ======================================================
echo.
pause
