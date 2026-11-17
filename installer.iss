; Doomscroll Blocker Installer Script
; For Inno Setup (https://jrsoftware.org/isdl.php)

[Setup]
; Basic information
AppName=Doomscroll Blocker
AppVersion=1.0
AppPublisher=DreTec
AppPublisherURL=https://adam-mohamed-student.github.io/truefocus.github.io/
AppSupportURL=https://adam-mohamed-student.github.io/truefocus.github.io/
AppUpdatesURL=https://adam-mohamed-student.github.io/truefocus.github.io/

; Installation directory
DefaultDirName={autopf}\Doomscroll Blocker
DefaultGroupName=Doomscroll Blocker
UninstallDisplayIcon={app}\DoomscrollBlocker.exe

; Compression settings
Compression=lzma2/ultra64
SolidCompression=yes

; Output settings
OutputDir=installer_output
OutputBaseFilename=DoomscrollBlocker_Setup
SetupIconFile=app.ico

; Wizard settings (removed WizardSizePercent)
WizardStyle=modern
WizardResizable=no

; Permissions
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional icons:"; Flags: checkedonce
Name: "autostart"; Description: "Run Doomscroll Blocker when Windows starts"; GroupDescription: "Startup options:"; Flags: unchecked

[Files]
; Main executable
Source: "dist\DoomscrollBlocker.exe"; DestDir: "{app}"; Flags: ignoreversion

; Assets folder (video files)
Source: "assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs

; Visual C++ Redistributable (required for OpenCV)
Source: "vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: deleteafterinstall; Check: VCRedistNeeded

[Icons]
; Start Menu shortcuts
Name: "{group}\Doomscroll Blocker"; Filename: "{app}\DoomscrollBlocker.exe"
Name: "{group}\Uninstall Doomscroll Blocker"; Filename: "{uninstallexe}"

; Desktop shortcut (if selected)
Name: "{autodesktop}\Doomscroll Blocker"; Filename: "{app}\DoomscrollBlocker.exe"; Tasks: desktopicon

; Startup folder (if selected)
Name: "{userstartup}\Doomscroll Blocker"; Filename: "{app}\DoomscrollBlocker.exe"; Tasks: autostart

[Run]
; Run after installation (optional)
Filename: "{app}\DoomscrollBlocker.exe"; Description: "Launch Doomscroll Blocker"; Flags: postinstall nowait skipifsilent unchecked

; Install VC++ Redist if needed
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/quiet /norestart"; StatusMsg: "Installing Visual C++ Redistributable..."; Check: VCRedistNeeded; Flags: waituntilterminated

[UninstallRun]
; Cleanup any running instances
Filename: "taskkill"; Parameters: "/f /im DoomscrollBlocker.exe"; Flags: runhidden waituntilterminated

[Code]
function VCRedistNeeded: Boolean;
var
  Version: String;
begin
  // Check if VC++ 2015-2022 Redistributable is installed
  if RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{31a7d4a4-8c93-4f53-b8bf-340db1160eab}', 'DisplayVersion', Version) or
     RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{e31cb1a4-76b5-46a5-a084-3fa419e82201}', 'DisplayVersion', Version) or
     RegQueryStringValue(HKLM, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{ad2a9d6d-8b6a-4c3d-9f7c-6a4d9a8b7c5e}', 'DisplayVersion', Version) then
  begin
    Result := False;  // Already installed
  end
  else
  begin
    Result := True;   // Needs installation
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Check if assets folder has video files
    if not FileExists(ExpandConstant('{app}\assets\*.mp4')) then
    begin
      MsgBox(
        'Please put your punishment video (.mp4) in the assets folder:' + #13#10 +
        ExpandConstant('{app}\assets\'),
        mbInformation, MB_OK
      );
    end;
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Ask if user wants to keep videos
    if MsgBox('Do you want to keep your punishment videos?', mbConfirmation, MB_YESNO) = IDNO then
    begin
      DelTree(ExpandConstant('{app}\assets'), True, True, True);
    end;
  end;
end;