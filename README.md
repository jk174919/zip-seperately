Attempting to perform the InitializeDefaultDrives operation on the 'FileSystem' provider failed.
# FolderZipTool

A small Windows desktop app that makes one ZIP archive per selected folder. Choose a parent folder to add all of its immediate subfolders at once, then click **Create ZIP files**. Each archive is saved in its own same-named output folder, for example `destination\Photos\Photos.zip`. Folder contents stay grouped under the folder name inside each archive.

GitHub repository: [jk174919/zip-seperately](https://github.com/jk174919/zip-seperately)

## Run from source

Install Python 3 for Windows, then double-click `Run-FolderZipTool.bat` (or run `py -3 folder_zipper.py`). The app uses only Python's built-in modules.

## Build a Windows app and installer

1. On Windows, double-click `Build-Windows.bat`. It installs PyInstaller and creates `dist\FolderZipTool\FolderZipTool.exe`.
2. Install [Inno Setup](https://jrsoftware.org/isinfo.php), open `installer.iss`, and compile it. The setup executable is written to `installer-output\FolderZipTool-Setup.exe`.

The installer creates a Start Menu shortcut and optionally a desktop shortcut. It installs for all users and asks Windows for administrator permission.

## Upload to Git

The project is published at [jk174919/zip-seperately](https://github.com/jk174919/zip-seperately). To push future changes from this folder, run:

```powershell
git init
git add .
git commit -m "Add FolderZipTool Windows app"
git branch -M main
git remote add origin <your-repository-url>
git push -u origin main
```

