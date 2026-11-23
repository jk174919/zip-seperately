@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul || (echo Python 3 is required. & pause & exit /b 1)
py -3 -m pip install -r requirements-pca.txt || (pause & exit /b 1)
py -3 -m pip install "pyinstaller>=6.0,<7" || (pause & exit /b 1)
py -3 -m PyInstaller --noconfirm --clean --windowed --name PrePostPCA --collect-all rasterio --collect-all numpy pre_post_pca.py || (pause & exit /b 1)
echo.
echo Build complete: dist\PrePostPCA\PrePostPCA.exe
echo To create an installer, install Inno Setup and compile pre_post_pca_installer.iss.
pause

