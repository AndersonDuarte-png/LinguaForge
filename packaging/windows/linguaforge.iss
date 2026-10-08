; Instalador Windows do LinguaForge (per-user, sem admin/UAC).
; Consome a distribuição onedir já validada em dist/LinguaForge.
; GGUF permanece externo; dados do usuário ficam em %LOCALAPPDATA%/%APPDATA%.

#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

#define AppName "LinguaForge"
#define AppId "{{fe274a9c-379e-48c9-9b35-590611ae033b}"
#define AppExeName "LinguaForge.exe"
#define AppIcon "linguaforge.ico"

[Setup]
AppId={#AppId}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=LinguaForge
DefaultDirName={localappdata}\Programs\LinguaForge
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
OutputBaseFilename=LinguaForge-{#AppVersion}-Setup
OutputDir=..\..\installer
SetupIconFile={#AppIcon}
UninstallDisplayIcon={app}\{#AppExeName}
UninstallDisplayName={#AppName} {#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"

[Files]
Source: "..\..\dist\LinguaForge\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{group}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent
