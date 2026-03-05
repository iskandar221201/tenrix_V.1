; ============================================================
; setup.iss — Tenrix Inno Setup Script
; Generates: tenrix-install.exe
;
; Requirements:
;   - Inno Setup 6.x: https://jrsoftware.org/isinfo.php
;   - install.bat must exist in the same folder as this file
;   - tenrix.bat must exist in the same folder as this file
;
; How to build:
;   1. Install Inno Setup 6
;   2. Open this file in Inno Setup Compiler
;   3. Click Build → Compile (or press F9)
;   4. Output: Output\tenrix-install.exe
; ============================================================

#define AppName      "Tenrix"
#define AppVersion   "1.0.0"
#define AppPublisher "Tenrix"
#define AppURL       "https://github.com/iskandar221201/tenrix_V.1"
#define AppInstallDir "{localappdata}\Tenrix"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}/issues
AppUpdatesURL={#AppURL}/releases

; Install to AppData\Local\Tenrix (no admin required)
DefaultDirName={#AppInstallDir}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes

; Output settings
OutputDir=Output
OutputBaseFilename=tenrix-install
SetupIconFile=..\assets\tenrix.ico
UninstallDisplayIcon=..\assets\tenrix.ico

; No admin rights needed
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Compression
Compression=lzma2/ultra64
SolidCompression=yes

; Wizard style
WizardStyle=modern
WizardResizable=no

; Minimum Windows version: Windows 10
MinVersion=10.0

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
; installer bat — runs during installation
Source: "install.bat"; DestDir: "{tmp}"; Flags: deleteafterinstall

; tenrix.bat wrapper — copied to install dir, registered to PATH
Source: "tenrix.bat"; DestDir: "{#AppInstallDir}"; Flags: ignoreversion

; INSTALL.txt — user reference
Source: "INSTALL.txt"; DestDir: "{#AppInstallDir}"; Flags: ignoreversion

[Run]
; Run install.bat silently during installation
; This handles: Git check, Python install, git clone, pip install, GTK3
Filename: "{cmd}"; \
  Parameters: "/C ""{tmp}\install.bat"""; \
  WorkingDir: "{tmp}"; \
  StatusMsg: "Installing Tenrix and dependencies (this may take 10-15 minutes)..."; \
  Flags: runhidden waituntilterminated

[Registry]
; Add Tenrix install dir to User PATH
; So user can run 'tenrix' from any terminal
Root: HKCU; \
  Subkey: "Environment"; \
  ValueType: expandsz; \
  ValueName: "PATH"; \
  ValueData: "{olddata};{#AppInstallDir}"; \
  Check: PathNotExists('{#AppInstallDir}')

[UninstallDelete]
; Clean up entire install dir on uninstall
Type: filesandordirs; Name: "{#AppInstallDir}"

[UninstallRun]
; Remove from PATH on uninstall
Filename: "{cmd}"; \
  Parameters: "/C setx PATH ""%PATH:{#AppInstallDir};=%"""; \
  Flags: runhidden waituntilterminated

[Code]
{ ── Helper: cek apakah path sudah ada di PATH ── }
function PathNotExists(Path: string): Boolean;
var
  CurrentPath: string;
begin
  if RegQueryStringValue(HKCU, 'Environment', 'PATH', CurrentPath) then
    Result := Pos(ExpandConstant(Path), CurrentPath) = 0
  else
    Result := True;
end;

{ ── Setelah install selesai: broadcast PATH change ke semua window ── }
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssDone then
  begin
    { Broadcast WM_SETTINGCHANGE agar terminal yang sudah buka ikut update PATH }
    Exec('cmd.exe',
      '/C setx PATH "%PATH%"',
      '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

{ ── Custom wizard page: tampilkan pesan sebelum install ── }
function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;
  if CurPageID = wpReady then
  begin
    MsgBox(
      'Tenrix will now:' + #13#10 + #13#10 +
      '  1. Check and install Git (if needed)' + #13#10 +
      '  2. Check and install Python 3.12 (if needed)' + #13#10 +
      '  3. Download Tenrix from GitHub' + #13#10 +
      '  4. Install all Python dependencies' + #13#10 +
      '  5. Install GTK3 Runtime (for PDF export)' + #13#10 +
      '  6. Register "tenrix" command to your PATH' + #13#10 + #13#10 +
      'This may take 10-15 minutes.' + #13#10 +
      'Please keep your internet connection active.',
      mbInformation, MB_OK
    );
  end;
end;
