Attempting to perform the InitializeDefaultDrives operation on the 'FileSystem' provider failed.
@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul || (echo Python 3 is required. & pause & exit /b 1)
py -3 -m pip install -r requirements-build.txt || (pause & exit /b 1)
py -3 -m PyInstaller --noconfirm --clean --windowed --name FolderZipTool folder_zipper.py || (pause & exit /b 1)
echo.
echo Build complete: dist\FolderZipTool\FolderZipTool.exe
echo To create an installer, install Inno Setup and compile installer.iss.
pause

