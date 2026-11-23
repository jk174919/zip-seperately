#define MyAppName "PrePostPCA"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "FolderZipTool"
#define MyAppExeName "PrePostPCA.exe"

[Setup]
AppId={{0C940318-9161-4430-A9DA-B6C8A60279EC}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\PrePostPCA
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=installer-output-pca
OutputBaseFilename=PrePostPCA-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\PrePostPCA\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\PrePostPCA"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\PrePostPCA"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch PrePostPCA"; Flags: postinstall nowait skipifsilent

