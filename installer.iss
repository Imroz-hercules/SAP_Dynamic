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

; Installer logo
WizardImageFile=Frontend\client\src\assets\modern_millslogo.png
WizardSmallImageFile=Frontend\client\src\assets\modern_millslogo.png

; Custom pages
DisableReadyPage=no
DisableFinishedPage=no

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Backend executable - RELATIVE path from installer.iss location
Source: "backend\dist\app.exe"; DestDir: "{app}\app"; Flags: ignoreversion

; Frontend - RELATIVE path from installer.iss location  
Source: "backend\public\*"; DestDir: "{app}\public"; Flags: ignoreversion recursesubdirs createallsubdirs

; Startup script
Source: "start_hercules.bat"; DestDir: "{app}"; Flags: ignoreversion

; Database setup script (optional - for manual setup if needed)
Source: "database_setup.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "database_setup_simple.py"; DestDir: "{app}"; Flags: ignoreversion

; Application icon
Source: "backend\app\modern_millslogo.ico"; DestDir: "{app}\app"; Flags: ignoreversion

[Icons]
Name: "{group}\Hercules KPI"; Filename: "{app}\start_hercules.bat"; WorkingDir: "{app}"; IconFilename: "{app}\app\modern_millslogo.ico"
Name: "{group}\Uninstall Hercules KPI"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Hercules KPI"; Filename: "{app}\start_hercules.bat"; WorkingDir: "{app}"; IconFilename: "{app}\app\modern_millslogo.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\start_hercules.bat"; Description: "{cm:LaunchProgram,Hercules KPI}"; Flags: nowait postinstall skipifsilent; WorkingDir: "{app}"

[UninstallDelete]
Type: filesandordirs; Name: "{app}\public"
Type: filesandordirs; Name: "{app}\app"
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\start_hercules.bat"
Type: files; Name: "{app}\database_setup.py"
Type: files; Name: "{app}\database_setup_simple.py"
Type: files; Name: "{app}\database_config.json"
Type: files; Name: "{app}\app\modern_millslogo.ico"

[Code]
var
  DatabaseConfigPage: TWizardPage;
  MSSQLServerEdit, MSSQLDatabaseEdit, MSSQLUsernameEdit, MSSQLPasswordEdit: TNewEdit;
  PGHostEdit, PGPortEdit, PGDatabaseEdit, PGUsernameEdit, PGPasswordEdit: TNewEdit;
  MSSQLCheckBox, PGCheckBox: TNewCheckBox;
  TestButton: TNewButton;
  LogMemo: TNewMemo;
  MSSQLLabel1, MSSQLLabel2, MSSQLLabel3, MSSQLLabel4, MSSQLLabel5: TNewStaticText;
  PGLabel1, PGLabel2, PGLabel3, PGLabel4, PGLabel5, PGLabel6: TNewStaticText;
  LogLabel: TNewStaticText;

procedure InitializeWizard;
begin
  // Create database configuration page
  DatabaseConfigPage := CreateCustomPage(wpSelectTasks, 'Database Configuration', 
    'Please configure your database connections. The installer will create the required tables automatically.');
  
  // MSSQL Configuration Group
  MSSQLLabel1 := TNewStaticText.Create(DatabaseConfigPage);
  MSSQLLabel1.Parent := DatabaseConfigPage.Surface;
  MSSQLLabel1.Left := 0;
  MSSQLLabel1.Top := 20;
  MSSQLLabel1.Width := 200;
  MSSQLLabel1.Caption := 'MSSQL Database Configuration:';
  MSSQLLabel1.Font.Style := [fsBold];
  
  MSSQLCheckBox := TNewCheckBox.Create(DatabaseConfigPage);
  MSSQLCheckBox.Parent := DatabaseConfigPage.Surface;
  MSSQLCheckBox.Left := 0;
  MSSQLCheckBox.Top := 40;
  MSSQLCheckBox.Width := 200;
  MSSQLCheckBox.Caption := 'Enable MSSQL Database';
  MSSQLCheckBox.Checked := True;
  
  MSSQLLabel2 := TNewStaticText.Create(DatabaseConfigPage);
  MSSQLLabel2.Parent := DatabaseConfigPage.Surface;
  MSSQLLabel2.Left := 0;
  MSSQLLabel2.Top := 65;
  MSSQLLabel2.Width := 60;
  MSSQLLabel2.Caption := 'Server:';
  
  MSSQLServerEdit := TNewEdit.Create(DatabaseConfigPage);
  MSSQLServerEdit.Parent := DatabaseConfigPage.Surface;
  MSSQLServerEdit.Left := 70;
  MSSQLServerEdit.Top := 63;
  MSSQLServerEdit.Width := 120;
  MSSQLServerEdit.Text := 'localhost';
  
  MSSQLLabel3 := TNewStaticText.Create(DatabaseConfigPage);
  MSSQLLabel3.Parent := DatabaseConfigPage.Surface;
  MSSQLLabel3.Left := 0;
  MSSQLLabel3.Top := 90;
  MSSQLLabel3.Width := 60;
  MSSQLLabel3.Caption := 'Database:';
  
  MSSQLDatabaseEdit := TNewEdit.Create(DatabaseConfigPage);
  MSSQLDatabaseEdit.Parent := DatabaseConfigPage.Surface;
  MSSQLDatabaseEdit.Left := 70;
  MSSQLDatabaseEdit.Top := 88;
  MSSQLDatabaseEdit.Width := 120;
  MSSQLDatabaseEdit.Text := 'HerculesV2';
  
  MSSQLLabel4 := TNewStaticText.Create(DatabaseConfigPage);
  MSSQLLabel4.Parent := DatabaseConfigPage.Surface;
  MSSQLLabel4.Left := 0;
  MSSQLLabel4.Top := 115;
  MSSQLLabel4.Width := 60;
  MSSQLLabel4.Caption := 'Username:';
  
  MSSQLUsernameEdit := TNewEdit.Create(DatabaseConfigPage);
  MSSQLUsernameEdit.Parent := DatabaseConfigPage.Surface;
  MSSQLUsernameEdit.Left := 70;
  MSSQLUsernameEdit.Top := 113;
  MSSQLUsernameEdit.Width := 120;
  MSSQLUsernameEdit.Text := 'sa';
  
  MSSQLLabel5 := TNewStaticText.Create(DatabaseConfigPage);
  MSSQLLabel5.Parent := DatabaseConfigPage.Surface;
  MSSQLLabel5.Left := 0;
  MSSQLLabel5.Top := 140;
  MSSQLLabel5.Width := 60;
  MSSQLLabel5.Caption := 'Password:';
  
  MSSQLPasswordEdit := TNewEdit.Create(DatabaseConfigPage);
  MSSQLPasswordEdit.Parent := DatabaseConfigPage.Surface;
  MSSQLPasswordEdit.Left := 70;
  MSSQLPasswordEdit.Top := 138;
  MSSQLPasswordEdit.Width := 120;
  MSSQLPasswordEdit.PasswordChar := '*';
  
  // PostgreSQL Configuration Group
  PGLabel1 := TNewStaticText.Create(DatabaseConfigPage);
  PGLabel1.Parent := DatabaseConfigPage.Surface;
  PGLabel1.Left := 250;
  PGLabel1.Top := 20;
  PGLabel1.Width := 200;
  PGLabel1.Caption := 'PostgreSQL Database Configuration:';
  PGLabel1.Font.Style := [fsBold];
  
  PGCheckBox := TNewCheckBox.Create(DatabaseConfigPage);
  PGCheckBox.Parent := DatabaseConfigPage.Surface;
  PGCheckBox.Left := 250;
  PGCheckBox.Top := 40;
  PGCheckBox.Width := 200;
  PGCheckBox.Caption := 'Enable PostgreSQL Database';
  PGCheckBox.Checked := True;
  
  PGLabel2 := TNewStaticText.Create(DatabaseConfigPage);
  PGLabel2.Parent := DatabaseConfigPage.Surface;
  PGLabel2.Left := 250;
  PGLabel2.Top := 65;
  PGLabel2.Width := 40;
  PGLabel2.Caption := 'Host:';
  
  PGHostEdit := TNewEdit.Create(DatabaseConfigPage);
  PGHostEdit.Parent := DatabaseConfigPage.Surface;
  PGHostEdit.Left := 300;
  PGHostEdit.Top := 63;
  PGHostEdit.Width := 120;
  PGHostEdit.Text := 'localhost';
  
  PGLabel3 := TNewStaticText.Create(DatabaseConfigPage);
  PGLabel3.Parent := DatabaseConfigPage.Surface;
  PGLabel3.Left := 250;
  PGLabel3.Top := 90;
  PGLabel3.Width := 40;
  PGLabel3.Caption := 'Port:';
  
  PGPortEdit := TNewEdit.Create(DatabaseConfigPage);
  PGPortEdit.Parent := DatabaseConfigPage.Surface;
  PGPortEdit.Left := 300;
  PGPortEdit.Top := 88;
  PGPortEdit.Width := 120;
  PGPortEdit.Text := '5432';
  
  PGLabel4 := TNewStaticText.Create(DatabaseConfigPage);
  PGLabel4.Parent := DatabaseConfigPage.Surface;
  PGLabel4.Left := 250;
  PGLabel4.Top := 115;
  PGLabel4.Width := 60;
  PGLabel4.Caption := 'Database:';
  
  PGDatabaseEdit := TNewEdit.Create(DatabaseConfigPage);
  PGDatabaseEdit.Parent := DatabaseConfigPage.Surface;
  PGDatabaseEdit.Left := 320;
  PGDatabaseEdit.Top := 113;
  PGDatabaseEdit.Width := 100;
  PGDatabaseEdit.Text := 'Hercules2';
  
  PGLabel5 := TNewStaticText.Create(DatabaseConfigPage);
  PGLabel5.Parent := DatabaseConfigPage.Surface;
  PGLabel5.Left := 250;
  PGLabel5.Top := 140;
  PGLabel5.Width := 60;
  PGLabel5.Caption := 'Username:';
  
  PGUsernameEdit := TNewEdit.Create(DatabaseConfigPage);
  PGUsernameEdit.Parent := DatabaseConfigPage.Surface;
  PGUsernameEdit.Left := 320;
  PGUsernameEdit.Top := 138;
  PGUsernameEdit.Width := 100;
  PGUsernameEdit.Text := 'postgres';
  
  PGLabel6 := TNewStaticText.Create(DatabaseConfigPage);
  PGLabel6.Parent := DatabaseConfigPage.Surface;
  PGLabel6.Left := 250;
  PGLabel6.Top := 165;
  PGLabel6.Width := 60;
  PGLabel6.Caption := 'Password:';
  
  PGPasswordEdit := TNewEdit.Create(DatabaseConfigPage);
  PGPasswordEdit.Parent := DatabaseConfigPage.Surface;
  PGPasswordEdit.Left := 320;
  PGPasswordEdit.Top := 163;
  PGPasswordEdit.Width := 100;
  PGPasswordEdit.PasswordChar := '*';
  
  // Test button and log
  TestButton := TNewButton.Create(DatabaseConfigPage);
  TestButton.Parent := DatabaseConfigPage.Surface;
  TestButton.Left := 0;
  TestButton.Top := 190;
  TestButton.Width := 100;
  TestButton.Height := 25;
  TestButton.Caption := 'Test Connections';
  
  LogLabel := TNewStaticText.Create(DatabaseConfigPage);
  LogLabel.Parent := DatabaseConfigPage.Surface;
  LogLabel.Left := 0;
  LogLabel.Top := 220;
  LogLabel.Width := 100;
  LogLabel.Caption := 'Setup Log:';
  
  LogMemo := TNewMemo.Create(DatabaseConfigPage);
  LogMemo.Parent := DatabaseConfigPage.Surface;
  LogMemo.Left := 0;
  LogMemo.Top := 240;
  LogMemo.Width := 450;
  LogMemo.Height := 80;
  LogMemo.ReadOnly := True;
  LogMemo.ScrollBars := ssVertical;
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ConfigFile: string;
  AppConfigFile: string;
  ConfigContent: string;
  ResultCode: Integer;
begin
  Result := True;
  
  if CurPageID = DatabaseConfigPage.ID then
  begin
    // Validate inputs
    if not MSSQLCheckBox.Checked and not PGCheckBox.Checked then
    begin
      MsgBox('Please enable at least one database type.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
    
    if MSSQLCheckBox.Checked then
    begin
      if (Trim(MSSQLServerEdit.Text) = '') or (Trim(MSSQLDatabaseEdit.Text) = '') then
      begin
        MsgBox('Please fill in MSSQL Server and Database fields. Username and Password can be left empty for Windows Authentication.', mbError, MB_OK);
        Result := False;
        Exit;
      end;
    end;
    
    if PGCheckBox.Checked then
    begin
      if (Trim(PGHostEdit.Text) = '') or (Trim(PGDatabaseEdit.Text) = '') or (Trim(PGUsernameEdit.Text) = '') then
      begin
        MsgBox('Please fill in all PostgreSQL database fields.', mbError, MB_OK);
        Result := False;
        Exit;
      end;
    end;
    
    // Create configuration JSON
    ConfigContent := '{';
    
    if MSSQLCheckBox.Checked then
    begin
      ConfigContent := ConfigContent + '"mssql": {' +
        '"server": "' + MSSQLServerEdit.Text + '",' +
        '"database": "' + MSSQLDatabaseEdit.Text + '",' +
        '"username": "' + MSSQLUsernameEdit.Text + '",' +
        '"password": "' + MSSQLPasswordEdit.Text + '"' +
        '}';
    end;
    
    if MSSQLCheckBox.Checked and PGCheckBox.Checked then
      ConfigContent := ConfigContent + ',';
    
    if PGCheckBox.Checked then
    begin
      ConfigContent := ConfigContent + '"postgresql": {' +
        '"host": "' + PGHostEdit.Text + '",' +
        '"port": "' + PGPortEdit.Text + '",' +
        '"database": "' + PGDatabaseEdit.Text + '",' +
        '"username": "' + PGUsernameEdit.Text + '",' +
        '"password": "' + PGPasswordEdit.Text + '"' +
        '}';
    end;
    
    ConfigContent := ConfigContent + '}';
    
    // Save config to temp file
    ConfigFile := ExpandConstant('{tmp}\db_config.json');
    SaveStringToFile(ConfigFile, ConfigContent, False);
    
    // Save database configuration for application to use
    LogMemo.Text := 'Saving database configuration...' + #13#10;
    
    // Ensure app directory exists
    if not DirExists(ExpandConstant('{app}')) then
    begin
      if not CreateDir(ExpandConstant('{app}')) then
      begin
        LogMemo.Text := LogMemo.Text + '❌ Failed to create application directory' + #13#10;
        MsgBox('Failed to create application directory. Please check permissions.', mbError, MB_OK);
        Result := False;
        Exit;
      end;
    end;
    
    // Copy config to application directory
    AppConfigFile := ExpandConstant('{app}\database_config.json');
    
    if FileExists(ConfigFile) then
    begin
      if CopyFile(ConfigFile, AppConfigFile, False) then
      begin
        LogMemo.Text := LogMemo.Text + '✅ Database configuration saved successfully!' + #13#10;
        Result := True;
      end
      else
      begin
        LogMemo.Text := LogMemo.Text + '❌ Failed to save database configuration' + #13#10;
        MsgBox('Failed to save database configuration. Please check file permissions and try again.', mbError, MB_OK);
        Result := False;
      end;
    end
    else
    begin
      LogMemo.Text := LogMemo.Text + '❌ Configuration file not found' + #13#10;
      MsgBox('Configuration file not found. Please try again.', mbError, MB_OK);
      Result := False;
    end;
  end;
end;
