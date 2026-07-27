; [utf8-binary] 01101011011011110011110111101100100001001011100011101010101100111000010000100000111011011000111110001001111011011001100110010100
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

#ifndef ReleaseRoot
  #define ReleaseRoot "..\dist\NIKKE_C_ARENA_Capture_Lite_0.1.0"
#endif

#define AppName "NIKKE C ARENA 截图工具 轻量版"
#define AppPublisher "NIKKE C ARENA Tool"

#ifndef AppIdentifier
  #define AppIdentifier "{{4B7BBD85-F7E5-41DC-955B-0B7756B4C344}"
#endif

[Setup]
AppId={#AppIdentifier}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
SetupIconFile=..\assets\app_installer_hammer.ico
DefaultDirName={localappdata}\Programs\NIKKE C ARENA 截图工具 轻量版
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=NIKKE_Arena_Capture_Lite_Setup_{#AppVersion}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加任务："; Flags: unchecked

[Dirs]
Name: "{app}\screenshots"; Flags: uninsneveruninstall
Name: "{app}\custom_backgrounds"; Flags: uninsneveruninstall
Name: "{app}\support_custom_backgrounds"; Flags: uninsneveruninstall
Name: "{app}\group_custom_backgrounds"; Flags: uninsneveruninstall

[Files]
Source: "{#ReleaseRoot}\run_capture_lite.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\nikke_capture_lite_launcher.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\nikke_round_stitcher.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\nikke_image_tools.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\nikke_character_capture.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\nikke_round_config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist
Source: "{#ReleaseRoot}\nikke_character_capture_config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist
Source: "{#ReleaseRoot}\RELEASE_INFO.json"; DestDir: "{app}"; Flags: ignoreversion

Source: "{#ReleaseRoot}\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ReleaseRoot}\runtime_core\*"; DestDir: "{app}\runtime_core"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{app}\NIKKE C ARENA 截图工具 轻量版"; Filename: "{app}\run_capture_lite.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app_doro_commander.ico"
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\run_capture_lite.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app_doro_commander.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\run_capture_lite.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app_doro_commander.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\run_capture_lite.bat"; Description: "启动 {#AppName}"; Flags: nowait postinstall skipifsilent
