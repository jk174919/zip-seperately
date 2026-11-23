Attempting to perform the InitializeDefaultDrives operation on the 'FileSystem' provider failed.
#define MyAppName "FolderZipTool"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "FolderZipTool"
#define MyAppExeName "FolderZipTool.exe"

[Setup]
AppId={{9D4D9F99-9029-4F22-BA52-6B6BB68D3A04}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\FolderZipTool
DefaultGroupName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
OutputDir=installer-output
OutputBaseFilename=FolderZipTool-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
PrivilegesRequired=admin

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "dist\FolderZipTool\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\FolderZipTool"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\FolderZipTool"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch FolderZipTool"; Flags: postinstall nowait skipifsilent

