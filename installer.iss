[Setup]
AppId={{07C37073-92D5-48D8-B9C3-6EB64F777959}
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
