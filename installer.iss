[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName=InstantCourier
AppVersion=1.0.0
AppPublisher=InstantCourier
DefaultDirName={autopf}\InstantCourier
DefaultGroupName=InstantCourier
OutputBaseFilename=InstantCourierSetup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Files]
Source: "dist\InstantCourier.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\InstantCourier"; Filename: "{app}\InstantCourier.exe"
Name: "{commondesktop}\InstantCourier"; Filename: "{app}\InstantCourier.exe"

[Run]
Filename: "{app}\InstantCourier.exe"; Description: "Launch InstantCourier"; Flags: nowait postinstall
