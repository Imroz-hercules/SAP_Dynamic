// Custom Inno Setup page for database configuration
unit DatabaseConfigPage;

interface

uses
  Windows, Messages, SysUtils, Variants, Classes, Graphics, Controls, Forms,
  Dialogs, StdCtrls, ExtCtrls, ComCtrls, InnoSetup;

type
  TDatabaseConfigForm = class(TForm)
    PageControl1: TPageControl;
    TabSheet1: TTabSheet;
    TabSheet2: TTabSheet;
    GroupBox1: TGroupBox;
    Label1: TLabel;
    Label2: TLabel;
    Label3: TLabel;
    Label4: TLabel;
    EditMSSQLServer: TEdit;
    EditMSSQLDatabase: TEdit;
    EditMSSQLUsername: TEdit;
    EditMSSQLPassword: TEdit;
    CheckBoxMSSQL: TCheckBox;
    GroupBox2: TGroupBox;
    Label5: TLabel;
    Label6: TLabel;
    Label7: TLabel;
    Label8: TLabel;
    Label9: TLabel;
    EditPGHost: TEdit;
    EditPGPort: TEdit;
    EditPGDatabase: TEdit;
    EditPGUsername: TEdit;
    EditPGPassword: TEdit;
    CheckBoxPostgreSQL: TCheckBox;
    ButtonTest: TButton;
    MemoLog: TMemo;
    ButtonNext: TButton;
    ButtonBack: TButton;
    LabelTitle: TLabel;
    LabelDescription: TLabel;
    
    procedure FormCreate(Sender: TObject);
    procedure CheckBoxMSSQLClick(Sender: TObject);
    procedure CheckBoxPostgreSQLClick(Sender: TObject);
    procedure ButtonTestClick(Sender: TObject);
    procedure ButtonNextClick(Sender: TObject);
    procedure ButtonBackClick(Sender: TObject);
    
  private
    { Private declarations }
    procedure UpdateControls;
    procedure LogMessage(const Msg: string);
    function ValidateInputs: Boolean;
    function TestConnections: Boolean;
    
  public
    { Public declarations }
    function GetDatabaseConfig: string;
  end;

var
  DatabaseConfigForm: TDatabaseConfigForm;

function CreateDatabaseConfigPage: Boolean;
function GetDatabaseConfig: string;

implementation

uses
  InnoSetupForm;

function CreateDatabaseConfigPage: Boolean;
begin
  Result := False;
  try
    DatabaseConfigForm := TDatabaseConfigForm.Create(nil);
    try
      Result := DatabaseConfigForm.ShowModal = mrOk;
    finally
      DatabaseConfigForm.Free;
    end;
  except
    on E: Exception do
      MsgBox('Error creating database configuration page: ' + E.Message, mbError, MB_OK);
  end;
end;

function GetDatabaseConfig: string;
begin
  if Assigned(DatabaseConfigForm) then
    Result := DatabaseConfigForm.GetDatabaseConfig
  else
    Result := '';
end;

procedure TDatabaseConfigForm.FormCreate(Sender: TObject);
begin
  // Set default values
  EditMSSQLServer.Text := 'localhost';
  EditMSSQLDatabase.Text := 'HerculesKPI';
  EditMSSQLUsername.Text := 'sa';
  EditMSSQLPassword.Text := '';
  
  EditPGHost.Text := 'localhost';
  EditPGPort.Text := '5432';
  EditPGDatabase.Text := 'hercules_kpi';
  EditPGUsername.Text := 'postgres';
  EditPGPassword.Text := '';
  
  CheckBoxMSSQL.Checked := True;
  CheckBoxPostgreSQL.Checked := True;
  
  UpdateControls;
  LogMessage('Database Configuration Page Loaded');
  LogMessage('Please configure your database connections below.');
end;

procedure TDatabaseConfigForm.UpdateControls;
begin
  GroupBox1.Enabled := CheckBoxMSSQL.Checked;
  GroupBox2.Enabled := CheckBoxPostgreSQL.Checked;
  
  ButtonTest.Enabled := CheckBoxMSSQL.Checked or CheckBoxPostgreSQL.Checked;
  ButtonNext.Enabled := CheckBoxMSSQL.Checked or CheckBoxPostgreSQL.Checked;
end;

procedure TDatabaseConfigForm.CheckBoxMSSQLClick(Sender: TObject);
begin
  UpdateControls;
end;

procedure TDatabaseConfigForm.CheckBoxPostgreSQLClick(Sender: TObject);
begin
  UpdateControls;
end;

procedure TDatabaseConfigForm.LogMessage(const Msg: string);
begin
  MemoLog.Lines.Add(FormatDateTime('hh:nn:ss', Now) + ' - ' + Msg);
  MemoLog.SelStart := Length(MemoLog.Text);
  Application.ProcessMessages;
end;

function TDatabaseConfigForm.ValidateInputs: Boolean;
begin
  Result := True;
  
  if CheckBoxMSSQL.Checked then
  begin
    if Trim(EditMSSQLServer.Text) = '' then
    begin
      MsgBox('Please enter MSSQL Server name', mbError, MB_OK);
      EditMSSQLServer.SetFocus;
      Result := False;
      Exit;
    end;
    
    if Trim(EditMSSQLDatabase.Text) = '' then
    begin
      MsgBox('Please enter MSSQL Database name', mbError, MB_OK);
      EditMSSQLDatabase.SetFocus;
      Result := False;
      Exit;
    end;
    
    if Trim(EditMSSQLUsername.Text) = '' then
    begin
      MsgBox('Please enter MSSQL Username', mbError, MB_OK);
      EditMSSQLUsername.SetFocus;
      Result := False;
      Exit;
    end;
  end;
  
  if CheckBoxPostgreSQL.Checked then
  begin
    if Trim(EditPGHost.Text) = '' then
    begin
      MsgBox('Please enter PostgreSQL Host', mbError, MB_OK);
      EditPGHost.SetFocus;
      Result := False;
      Exit;
    end;
    
    if Trim(EditPGDatabase.Text) = '' then
    begin
      MsgBox('Please enter PostgreSQL Database name', mbError, MB_OK);
      EditPGDatabase.SetFocus;
      Result := False;
      Exit;
    end;
    
    if Trim(EditPGUsername.Text) = '' then
    begin
      MsgBox('Please enter PostgreSQL Username', mbError, MB_OK);
      EditPGUsername.SetFocus;
      Result := False;
      Exit;
    end;
  end;
end;

function TDatabaseConfigForm.TestConnections: Boolean;
var
  Config: string;
  TempFile: string;
  ResultCode: Integer;
begin
  Result := False;
  
  if not ValidateInputs then
    Exit;
  
  LogMessage('Testing database connections...');
  
  Config := GetDatabaseConfig;
  TempFile := ExpandConstant('{tmp}\db_config.json');
  
  try
    // Save config to temp file
    SaveStringToFile(TempFile, Config, False);
    
    // Run database setup script
    LogMessage('Running database setup script...');
    if Exec(ExpandConstant('{app}\app\python.exe'), 
            ExpandConstant('"{app}\database_setup.py" "{tmp}\db_config.json"'),
            '', SW_HIDE, ewWaitUntilTerminated, ResultCode) then
    begin
      if ResultCode = 0 then
      begin
        LogMessage('✅ Database setup completed successfully!');
        Result := True;
      end
      else
      begin
        LogMessage('❌ Database setup failed with error code: ' + IntToStr(ResultCode));
      end;
    end
    else
    begin
      LogMessage('❌ Failed to run database setup script');
    end;
  except
    on E: Exception do
      LogMessage('❌ Error: ' + E.Message);
  end;
end;

procedure TDatabaseConfigForm.ButtonTestClick(Sender: TObject);
begin
  TestConnections;
end;

procedure TDatabaseConfigForm.ButtonNextClick(Sender: TObject);
begin
  if TestConnections then
    ModalResult := mrOk
  else
    MsgBox('Database setup failed. Please check the configuration and try again.', mbError, MB_OK);
end;

procedure TDatabaseConfigForm.ButtonBackClick(Sender: TObject);
begin
  ModalResult := mrCancel;
end;

function TDatabaseConfigForm.GetDatabaseConfig: string;
var
  Config: TStringList;
begin
  Config := TStringList.Create;
  try
    Config.Add('{');
    
    if CheckBoxMSSQL.Checked then
    begin
      Config.Add('  "mssql": {');
      Config.Add('    "server": "' + EditMSSQLServer.Text + '",');
      Config.Add('    "database": "' + EditMSSQLDatabase.Text + '",');
      Config.Add('    "username": "' + EditMSSQLUsername.Text + '",');
      Config.Add('    "password": "' + EditMSSQLPassword.Text + '"');
      Config.Add('  }');
    end;
    
    if CheckBoxMSSQL.Checked and CheckBoxPostgreSQL.Checked then
      Config.Add(',');
    
    if CheckBoxPostgreSQL.Checked then
    begin
      Config.Add('  "postgresql": {');
      Config.Add('    "host": "' + EditPGHost.Text + '",');
      Config.Add('    "port": "' + EditPGPort.Text + '",');
      Config.Add('    "database": "' + EditPGDatabase.Text + '",');
      Config.Add('    "username": "' + EditPGUsername.Text + '",');
      Config.Add('    "password": "' + EditPGPassword.Text + '"');
      Config.Add('  }');
    end;
    
    Config.Add('}');
    
    Result := Config.Text;
  finally
    Config.Free;
  end;
end;

end.
