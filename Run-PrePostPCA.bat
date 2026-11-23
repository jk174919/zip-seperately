@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0pre_post_pca.py"
) else (
  python "%~dp0pre_post_pca.py"
)
if errorlevel 1 (
  echo.
  echo Could not start the PCA app. Install Python 3 and run: py -3 -m pip install -r requirements-pca.txt
  pause
)

