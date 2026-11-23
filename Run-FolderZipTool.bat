@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0folder_zipper.py"
) else (
  python "%~dp0folder_zipper.py"
)
if errorlevel 1 (
  echo.
  echo Could not start FolderZipTool. Install Python 3 from https://www.python.org/downloads/windows/ and try again.
  pause
)

