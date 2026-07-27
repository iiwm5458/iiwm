; [utf8-binary] 011010100110000100111101111001001011100010010110111001111001010110001100111001011011100110110011111001011001001010001100
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif

#ifndef ReleaseRoot
  #define ReleaseRoot "..\dist\NIKKE_Arena_Tool_0.1.0"
#endif

#define AppName "NIKKE C ARENA Tool"
#define AppPublisher "NIKKE C ARENA Tool"

#ifndef AppIdentifier
  #define AppIdentifier "{{E4DBE1A8-8998-4F1B-AF3B-25CD3D76B762}"
#endif

[Setup]
AppId={#AppIdentifier}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
SetupIconFile=..\assets\app_installer_hammer.ico
DefaultDirName={localappdata}\Programs\NIKKE C ARENA Tool
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\dist\installer
OutputBaseFilename=NIKKE_Arena_Tool_Setup_{#AppVersion}
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
Source: "{#ReleaseRoot}\run_gui.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\run_stitcher.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\run_character_capture.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\run_all_characters.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\nikke_gui_bootstrap.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\nikke_gui_launcher.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\nikke_round_stitcher.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\nikke_image_tools.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\nikke_character_capture.py"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\nikke_round_config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist
Source: "{#ReleaseRoot}\nikke_character_capture_config.json"; DestDir: "{app}"; Flags: onlyifdoesntexist
Source: "{#ReleaseRoot}\RELEASE_INFO.json"; DestDir: "{app}"; Flags: ignoreversion

Source: "{#ReleaseRoot}\assets\*"; DestDir: "{app}\assets"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ReleaseRoot}\vendor\*"; DestDir: "{app}\vendor"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ReleaseRoot}\runtime_core\*"; DestDir: "{app}\runtime_core"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ReleaseRoot}\runtime_python310_base\*"; DestDir: "{app}\runtime_python310_base"; Flags: ignoreversion recursesubdirs createallsubdirs

Source: "{#ReleaseRoot}\dataanalysis\arena_ocr_tool\main.py"; DestDir: "{app}\dataanalysis\arena_ocr_tool"; Flags: ignoreversion
Source: "{#ReleaseRoot}\dataanalysis\arena_ocr_tool\recognizer\*"; DestDir: "{app}\dataanalysis\arena_ocr_tool\recognizer"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ReleaseRoot}\dataanalysis\arena_ocr_tool\models\*"; DestDir: "{app}\dataanalysis\arena_ocr_tool\models"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ReleaseRoot}\dataanalysis\arena_ocr_tool\data\nikke_names.json"; DestDir: "{app}\dataanalysis\arena_ocr_tool\data"; Flags: onlyifdoesntexist
Source: "{#ReleaseRoot}\dataanalysis\arena_ocr_tool\data\nikke_names.backup.json"; DestDir: "{app}\dataanalysis\arena_ocr_tool\data"; Flags: onlyifdoesntexist
Source: "{#ReleaseRoot}\dataanalysis\arena_ocr_tool\data\*"; DestDir: "{app}\dataanalysis\arena_ocr_tool\data"; Excludes: "nikke_names.json,nikke_names.backup.json"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "{#ReleaseRoot}\dataanalysis\arena_ocr_tool\requirements-ocr.txt"; DestDir: "{app}\dataanalysis\arena_ocr_tool"; Flags: ignoreversion
Source: "{#ReleaseRoot}\dataanalysis\arena_ocr_tool\requirements-ocr-cpu.lock.txt"; DestDir: "{app}\dataanalysis\arena_ocr_tool"; Flags: ignoreversion
Source: "{#ReleaseRoot}\dataanalysis\arena_ocr_tool\requirements-ocr-gpu.txt"; DestDir: "{app}\dataanalysis\arena_ocr_tool"; Flags: ignoreversion

Source: "{#ReleaseRoot}\setup_gpu_runtime.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\setup_gpu_runtime_cn.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\setup_gpu_runtime_aliyun.bat"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\setup_gpu_runtime.ps1"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\GPU_OCR_RUNTIME_SETUP_GUIDE.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ReleaseRoot}\GPU_OCR_RUNTIME_SETUP_GUIDE.pdf"; DestDir: "{app}"; Flags: ignoreversion

Source: "{#ReleaseRoot}\runtime_cpu\*"; DestDir: "{app}\runtime_cpu"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{app}\NIKKE C ARENA Tool"; Filename: "{app}\run_gui.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app_doro_commander.ico"
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\run_gui.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app_doro_commander.ico"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\run_gui.bat"; WorkingDir: "{app}"; IconFilename: "{app}\assets\app_doro_commander.ico"; Tasks: desktopicon

[Run]
Filename: "{app}\run_gui.bat"; Description: "启动 {#AppName}"; Flags: nowait postinstall skipifsilent
