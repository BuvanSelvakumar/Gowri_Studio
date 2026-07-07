; Inno Setup script — builds GowriStudioSetup.exe (a real Windows installer).
; Compiled by GitHub Actions after PyInstaller produces dist\Gowri Studio\.

[Setup]
AppName=Gowri Studio
AppVersion=1.0
AppPublisher=Sri Gowri Studio
DefaultDirName={autopf}\Gowri Studio
DisableProgramGroupPage=yes
OutputDir=Output
OutputBaseFilename=GowriStudioSetup
SetupIconFile=..\assets\AppIcon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64
; Install per-user so no admin password is needed.
PrivilegesRequired=lowest

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Shortcuts:"

[Files]
Source: "..\dist\Gowri Studio\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\Gowri Studio"; Filename: "{app}\Gowri Studio.exe"
Name: "{autodesktop}\Gowri Studio"; Filename: "{app}\Gowri Studio.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Gowri Studio.exe"; Description: "Launch Gowri Studio now"; Flags: nowait postinstall skipifsilent
