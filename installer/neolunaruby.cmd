@echo off
rem Launcher: runs the bootstrap (which is a no-op once set up) then the app.
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0installer\bootstrap.ps1"
if errorlevel 1 (
  echo.
  echo Setup failed. Scroll up for the error, or report it at
  echo https://github.com/Fightersbane/neolunaruby/issues
  pause
)
