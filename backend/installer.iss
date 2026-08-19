; ============================================
; Hercules KPI Installer
; ============================================

[Setup]
AppName=Hercules KPI
AppVersion=1.0.0
AppPublisher=Your Company
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}

DefaultDirName={autopf}\HerculesKPI
DefaultGroupName=Hercules KPI
DisableProgramGroupPage=no

OutputDir=.
OutputBaseFilename=HerculesKPIInstaller
Compression=lzma2/ultra64
SolidCompression=yes

WizardStyle=modern
UninstallDisplayIcon={app}\app\app.exe
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Backend - RELATIVE path from installer.iss location
Source: "backend\dist\app\*"; DestDir: "{app}\app"; Flags: ignoreversion recursesubdirs createallsubdirs

; Frontend - RELATIVE path from installer.iss location  
Source: "backend\public\*"; DestDir: "{app}\public"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Hercules KPI"; Filename: "{app}\app\app.exe"; WorkingDir: "{app}"
Name: "{group}\Uninstall Hercules KPI"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Hercules KPI"; Filename: "{app}\app\app.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\app\app.exe"; Description: "{cm:LaunchProgram,Hercules KPI}"; Flags: nowait postinstall skipifsilent; WorkingDir: "{app}"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\public"
Type: filesandordirs; Name: "{app}\app"
Type: files; Name: "{app}\*.log"
