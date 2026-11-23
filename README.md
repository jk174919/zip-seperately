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

## Pre/Post image stack and PCA tool

`pre_post_pca.py` is a separate Windows GUI for pairing pre and post images by area-folder name. Each selected parent folder should contain one subfolder per area, and each area folder must contain exactly one raster (`.tif`, `.tiff`, `.img`, or `.vrt`). Matching area names are processed; unmatched names are reported and skipped.

The input rasters must each have exactly three bands in B2, B3, B4 order. If band names are missing, the GUI requires you to confirm that order. The tool checks CRS, extent, pixel resolution, dimensions, and geotransform before stacking. It skips area pairs that fail a check. It cannot prove real-world co-registration from file metadata; use images that have already been accurately co-registered.

For each valid area, the selected output parent gets:

```text
output-folder/
  AreaName/
    pre_post_stack.tif   # Pre_B2, Pre_B3, Pre_B4, Post_B2, Post_B3, Post_B4
    pca_output.tif       # PC1 through PC6; PC4 is identified by the SOP as the primary disturbance indicator
```

PCA is calculated from the covariance matrix of shared valid pixels, after centering and without standardizing the bands. Component signs are mathematically arbitrary; the app uses a consistent sign convention for repeatable output. Interpret PC4 with its eigenvector loadings and the SOP, since sign can vary between datasets.

### Run or package the PCA app

- Run from source: install Python 3.10 or newer, then double-click `Run-PrePostPCA.bat`.
- Build a Windows app: double-click `Build-PrePostPCA.bat`; it creates `dist\PrePostPCA\PrePostPCA.exe`.
- Build a Windows installer: install Inno Setup and compile `pre_post_pca_installer.iss`. The installer is written to `installer-output-pca\PrePostPCA-Setup.exe`.

The PCA tool uses NumPy and Rasterio. Rasterio's Windows wheels include GDAL dependencies for convenient installation, with some optional format drivers omitted; GeoTIFF is the recommended input format. See the [Rasterio installation guide](https://rasterio.readthedocs.io/en/stable/installation.html) and [windowed processing guide](https://rasterio.readthedocs.io/en/stable/topics/windowed-rw.html).

