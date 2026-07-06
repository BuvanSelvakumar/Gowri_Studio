@echo off
REM Double-click this to set up (first time) and launch Gowri Studio on Windows.
cd /d "%~dp0"

echo ============================================================
echo   Gowri Studio - Windows setup and launcher
echo   First run downloads Python + libraries (5-10 minutes).
echo   Please leave this window open until it finishes.
echo ============================================================
echo.

if not exist "windows_setup.ps1" (
  echo ERROR: windows_setup.ps1 is missing.
  echo Make sure you copied the WHOLE photo folder to this PC.
  echo.
  pause
  exit /b 1
)
if not exist "requirements.txt" (
  echo ERROR: requirements.txt is missing - the folder is incomplete.
  echo.
  pause
  exit /b 1
)

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0windows_setup.ps1"

echo.
echo ============================================================
echo   Finished. If Gowri Studio did not open, the messages above
echo   show why. Take a screenshot of this window and send it.
echo ============================================================
pause
