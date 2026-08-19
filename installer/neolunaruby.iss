; Inno Setup script for neolunaruby.
; Ships source only: Python, dependencies and voice models are fetched on
; first launch, so the installer stays small and contains no secrets.
; Build with: scripts\build_installer.ps1

#define AppName "neolunaruby"
#define AppPublisher "Fightersbane"
#define AppURL "https://github.com/Fightersbane/neolunaruby"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{8C2F5A31-9D4E-4B7A-A6C3-1E5B9F0D2A47}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=neolunaruby-setup-{#AppVersion}
SetupIconFile=..\assets\neolunaruby.ico
UninstallDisplayIcon={app}\assets\neolunaruby.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\staging\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\neolunaruby.cmd"; IconFilename: "{app}\assets\neolunaruby.ico"; WorkingDir: "{app}"
Name: "{userdesktop}\{#AppName}"; Filename: "{app}\neolunaruby.cmd"; IconFilename: "{app}\assets\neolunaruby.ico"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\neolunaruby.cmd"; Description: "Launch {#AppName} (first launch sets things up)"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Generated at runtime, not tracked by the installer
Type: filesandordirs; Name: "{app}\.venv"
Type: filesandordirs; Name: "{app}\audio"
Type: filesandordirs; Name: "{app}\logs"
Type: filesandordirs; Name: "{app}\__pycache__"
