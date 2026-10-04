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
DefaultDirName=C:\NIKKE_C_ARENA_Tool\NIKKE C ARENA 截图工具 轻量版
UsePreviousAppDir=no
DisableDirPage=no
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

[Code]
const
  OwnEditionProduct = 'NIKKE C ARENA 截图工具 轻量版';
  OtherEditionName = 'NIKKE C ARENA Tool 完整版';
  OtherEditionLauncher = 'run_gui.bat';

procedure SkipJsonWhitespace(const Text: String; var Index: Integer);
begin
  while Index <= Length(Text) do
  begin
    if (Text[Index] = ' ') or (Text[Index] = #9) or
       (Text[Index] = #10) or (Text[Index] = #13) then
      Index := Index + 1
    else
      Break;
  end;
end;

function JsonCodePointToString(CodePoint: Integer): String;
var
  Bytes: AnsiString;
begin
  { Chr is byte-sized in some Inno 6 script engines. Decode explicit UTF-8
    bytes instead of truncating the Chinese product's UTF-16 code units. }
  if CodePoint <= $7F then
  begin
    SetLength(Bytes, 1);
    Bytes[1] := Chr(CodePoint);
  end
  else if CodePoint <= $7FF then
  begin
    SetLength(Bytes, 2);
    Bytes[1] := Chr($C0 + (CodePoint div 64));
    Bytes[2] := Chr($80 + (CodePoint mod 64));
  end
  else
  begin
    SetLength(Bytes, 3);
    Bytes[1] := Chr($E0 + (CodePoint div 4096));
    Bytes[2] := Chr($80 + ((CodePoint div 64) mod 64));
    Bytes[3] := Chr($80 + (CodePoint mod 64));
  end;
  Result := Utf8Decode(Bytes);
end;

function ReadReleaseProduct(const FileName: String; var Product: String): Boolean;
var
  Lines: TArrayOfString;
  Text: String;
  Index, LineIndex, HexIndex, HexDigit, CodePoint: Integer;
  Character: Char;
begin
  Result := False;
  Product := '';
  if not LoadStringsFromFile(FileName, Lines) then
    Exit;
  Text := '';
  for LineIndex := 0 to GetArrayLength(Lines) - 1 do
    Text := Text + Lines[LineIndex] + #10;
  Index := Pos('"product"', Text);
  if Index = 0 then
    Exit;
  Index := Index + Length('"product"');
  SkipJsonWhitespace(Text, Index);
  if Index > Length(Text) then
    Exit;
  if Text[Index] <> ':' then
    Exit;
  Index := Index + 1;
  SkipJsonWhitespace(Text, Index);
  if Index > Length(Text) then
    Exit;
  if Text[Index] <> '"' then
    Exit;
  Index := Index + 1;
  while Index <= Length(Text) do
  begin
    Character := Text[Index];
    if Character = '"' then
    begin
      Index := Index + 1;
      SkipJsonWhitespace(Text, Index);
      if Index > Length(Text) then
        Exit;
      Result := (Text[Index] = ',') or (Text[Index] = '}');
      Exit;
    end;
    if Character = '\' then
    begin
      Index := Index + 1;
      if Index > Length(Text) then
        Exit;
      Character := Text[Index];
      case Character of
        '"', '\', '/': Product := Product + Character;
        'b': Product := Product + #8;
        'f': Product := Product + #12;
        'n': Product := Product + #10;
        'r': Product := Product + #13;
        't': Product := Product + #9;
        'u':
          begin
            CodePoint := 0;
            for HexIndex := 1 to 4 do
            begin
              Index := Index + 1;
              if Index > Length(Text) then
                Exit;
              HexDigit := Pos(UpperCase(Text[Index]), '0123456789ABCDEF') - 1;
              if HexDigit < 0 then
                Exit;
              CodePoint := (CodePoint * 16) + HexDigit;
            end;
            Product := Product + JsonCodePointToString(CodePoint);
          end;
      else
        Exit;
      end;
    end
    else
    begin
      if Ord(Character) < 32 then
        Exit;
      Product := Product + Character;
    end;
    Index := Index + 1;
  end;
end;

function CheckEditionInstallDirectory(const TargetDir: String): String;
var
  InfoPath, Product: String;
begin
  Result := '';
  if FileExists(AddBackslash(TargetDir) + OtherEditionLauncher) then
  begin
    Result := '所选目录已包含' + OtherEditionName + '，两版不能安装到同一目录。' +
      (#13#10) + '请为本版选择独立目录：' + TargetDir;
    Exit;
  end;
  InfoPath := AddBackslash(TargetDir) + 'RELEASE_INFO.json';
  if FileExists(InfoPath) then
  begin
    if not ReadReleaseProduct(InfoPath, Product) then
    begin
      Result := '无法确认所选目录中已有程序的版本信息，已停止覆盖。' +
        (#13#10) + '请检查 RELEASE_INFO.json，或选择独立目录：' + TargetDir;
      Exit;
    end;
    if not SameText(Product, OwnEditionProduct) then
      Result := '所选目录属于另一版本或其它程序，已停止覆盖。' +
        (#13#10) + '已有产品：' + Product +
        (#13#10) + '请为本版选择独立目录：' + TargetDir;
  end;
end;

function ProbeInstallDirectoryWritable(const Directory: String): String;
var
  ProbeDir, ProbeFile: String;
  Attempt: Integer;
  ProbeCreated, FileWritten, FileRemoved, DirRemoved: Boolean;
begin
  Result := '';
  ProbeCreated := False;
  for Attempt := 1 to 20 do
  begin
    ProbeDir := AddBackslash(Directory) + '.nikke_install_probe_' +
      GetDateTimeString('yyyymmddhhnnss', '-', ':') + '_' + IntToStr(Random(2147483647));
    if not FileOrDirExists(ProbeDir) then
    begin
      ProbeCreated := CreateDir(ProbeDir);
      Break;
    end;
  end;
  if not ProbeCreated then
  begin
    Result := '无法在所选位置创建目录，请选择有读写权限的目录。' +
      (#13#10) + '检查位置：' + Directory +
      (#13#10) + '安装器不会自动提权或更改目录权限。';
    Exit;
  end;
  ProbeFile := AddBackslash(ProbeDir) + 'write_test.tmp';
  FileWritten := False;
  FileRemoved := True;
  DirRemoved := False;
  try
    FileWritten := SaveStringToFile(ProbeFile, 'NIKKE installer write check', False);
  finally
    if FileExists(ProbeFile) then
      FileRemoved := DeleteFile(ProbeFile);
    DirRemoved := RemoveDir(ProbeDir);
  end;
  if not FileWritten then
    Result := '无法在所选位置写入文件，请检查目录权限、剩余空间或安全软件拦截。' +
      (#13#10) + '检查位置：' + Directory +
      (#13#10) + '请选择有读写权限的目录；安装器不会自动提权或更改权限。'
  else if (not FileRemoved) or (not DirRemoved) then
    Result := '所选目录可写，但无法清理本次临时检查文件，已停止安装。' +
      (#13#10) + '请检查目录权限或安全软件拦截：' + ProbeDir;
end;

function EnsureInstallDirectoryWritable(const TargetDir: String): String;
var
  ExistingParent, Parent: String;
begin
  Result := '';
  ExistingParent := ExpandFileName(TargetDir);
  while not DirExists(ExistingParent) do
  begin
    if FileExists(ExistingParent) then
    begin
      Result := '目标路径的一部分已经是文件，无法创建安装目录：' + ExistingParent;
      Exit;
    end;
    Parent := ExtractFileDir(ExistingParent);
    if (Parent = '') or SameText(Parent, ExistingParent) then
    begin
      Result := '找不到可用的目标驱动器或父目录：' + TargetDir;
      Exit;
    end;
    ExistingParent := Parent;
  end;
  Result := ProbeInstallDirectoryWritable(ExistingParent);
  if Result <> '' then
    Exit;
  if not DirExists(TargetDir) then
  begin
    if not ForceDirectories(TargetDir) then
    begin
      Result := '无法创建所选安装目录，请选择有读写权限的目录：' + TargetDir +
        (#13#10) + '安装器不会自动提权、更改权限或移动旧安装。';
      Exit;
    end;
  end;
  Result := ProbeInstallDirectoryWritable(TargetDir);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
var
  ErrorText: String;
begin
  Result := True;
  if CurPageID = wpSelectDir then
  begin
    { The directory page is read-only: no target directory is created here. }
    ErrorText := CheckEditionInstallDirectory(WizardDirValue);
    if ErrorText <> '' then
    begin
      MsgBox(ErrorText, mbError, MB_OK);
      Result := False;
    end;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
var
  TargetDir: String;
begin
  TargetDir := ExpandConstant('{app}');
  Result := CheckEditionInstallDirectory(TargetDir);
  if Result <> '' then
    Exit;
  { Also runs during silent installation, before any program files are copied. }
  Result := EnsureInstallDirectoryWritable(TargetDir);
  if Result = '' then
    Result := CheckEditionInstallDirectory(TargetDir);
end;
