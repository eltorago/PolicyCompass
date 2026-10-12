; Unsigned, per-user installer. User data is outside {app} and survives uninstall.
#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef PayloadDir
  #error PayloadDir is required
#endif
#ifndef ReleaseDir
  #error ReleaseDir is required
#endif

[Setup]
AppId={{78C03424-10C5-4F1A-91B7-753E0442E6D1}
AppName=PolicyCompass
AppVersion={#AppVersion}
AppPublisher=PolicyCompass
AppPublisherURL=https://github.com/eltorago/PolicyCompass
DefaultDirName={localappdata}\Programs\PolicyCompass
DefaultGroupName=PolicyCompass
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
DisableProgramGroupPage=yes
DisableDirPage=yes
OutputDir={#ReleaseDir}
OutputBaseFilename=PolicyCompass-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\PolicyCompass.exe
CloseApplications=yes
RestartApplications=no
SetupLogging=yes

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "{#PayloadDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\PolicyCompass"; Filename: "{app}\PolicyCompass.exe"; WorkingDir: "{app}"
Name: "{autodesktop}\PolicyCompass"; Filename: "{app}\PolicyCompass.exe"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "{app}\PolicyCompass.exe"; Description: "Open PolicyCompass"; Flags: nowait postinstall skipifsilent
