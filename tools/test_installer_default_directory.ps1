param([string]$IsccPath = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$qaRoot = Join-Path $projectRoot ('work\installer_default_directory_' + [Guid]::NewGuid().ToString('N'))
if (-not (Test-Path -LiteralPath $IsccPath -PathType Leaf)) { throw 'Inno Setup compiler missing.' }
$null = New-Item -ItemType Directory -Path $qaRoot
$editions = @(
    @{ Name='Full'; Script='installer\NIKKE_Arena_Tool.iss'; Default='C:\NIKKE_C_ARENA_Tool\NIKKE C ARENA Tool' },
    @{ Name='Lite'; Script='installer\NIKKE_Arena_Capture_Lite.iss'; Default='C:\NIKKE_C_ARENA_Tool\NIKKE C ARENA 截图工具 轻量版' }
)
$script:NativePassed = 0
$script:DirectivePassed = 0
$script:ResultRecords = @()
function Quote-DefaultDirPascal([string]$Value) { return "'" + $Value.Replace("'", "''") + "'" }
function Convert-DefaultDirCodes([string]$Value) {
    return -join @($Value.Split(',') | Where-Object { $_ -ne '' } | ForEach-Object { [char][int]$_ })
}
function Invoke-DefaultDirNativeCase([string]$ExePath, [string]$Edition, [string]$Name, [string]$ExpectedDir, [string]$CustomDir = '') {
    $resultPath = Join-Path (Split-Path -Parent $ExePath) ($Name + '.result.txt')
    $logPath = Join-Path (Split-Path -Parent $ExePath) ($Name + '.setup.log')
    $arguments = @('/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/SP-', ('/RESULT="' + $resultPath + '"'), ('/LOG="' + $logPath + '"'))
    if ($CustomDir) { $arguments += '/DIR="' + $CustomDir + '"' }
    $process = Start-Process -FilePath $ExePath -ArgumentList $arguments -WindowStyle Hidden -PassThru
    try {
        if (-not $process.WaitForExit(30000)) { throw "Native inert setup timed out: $Edition / $Name" }
        $exitCode = $process.ExitCode
    } finally { $process.Dispose() }
    if (-not (Test-Path -LiteralPath $resultPath -PathType Leaf)) { throw "Native setup produced no initialization result: $Edition / $Name" }
    $resultText = [IO.File]::ReadAllText($resultPath)
    $codes = [regex]::Match($resultText, '(?m)^DIR_CODES=(.*)$').Groups[1].Value.Trim()
    $actualDir = Convert-DefaultDirCodes $codes
    if ($actualDir -ine $ExpectedDir) { throw "Native directory mismatch: $Edition / $Name. Actual=$actualDir Expected=$ExpectedDir" }
    if ($resultText -match 'INSTALL_REACHED|PREPARE_REACHED') { throw "Inert setup went beyond the first wizard page: $Edition / $Name" }
    if ($exitCode -eq 0) { throw "Inert setup should abort rather than succeed: $Edition / $Name" }
    $script:NativePassed++
    $script:ResultRecords += [PSCustomObject]@{ Edition=$Edition; Case=$Name; ActualDirectory=$actualDir; ExitCode=$exitCode }
}

foreach ($edition in $editions) {
    $source = [IO.File]::ReadAllText((Join-Path $projectRoot $edition.Script), [Text.Encoding]::UTF8)
    foreach ($line in @(('DefaultDirName=' + $edition.Default), 'UsePreviousAppDir=no', 'DisableDirPage=no')) {
        if ($source -notmatch ('(?m)^' + [regex]::Escape($line) + '\s*$')) { throw "Production installer directive mismatch: $($edition.Name) / $line" }
        $script:DirectivePassed++
    }
    $editionRoot = Join-Path $qaRoot $edition.Name
    $null = New-Item -ItemType Directory -Path $editionRoot
    $oldExisting = Join-Path $editionRoot 'old_existing'
    $oldDeleted = Join-Path $editionRoot 'old_manually_deleted'
    $customDir = Join-Path $editionRoot 'explicit_user_choice'
    $null = New-Item -ItemType Directory -Path $oldExisting
    $null = New-Item -ItemType Directory -Path $oldDeleted
    [IO.File]::WriteAllText((Join-Path $oldExisting 'sentinel.txt'), 'Existing QA data must survive.', [Text.Encoding]::ASCII)
    # Remove only this newly-created empty fixture, using one native PowerShell command.
    if (-not ([IO.Path]::GetFullPath($oldDeleted).StartsWith([IO.Path]::GetFullPath($qaRoot) + '\', [StringComparison]::OrdinalIgnoreCase))) { throw 'Unsafe deleted-directory fixture.' }
    Remove-Item -LiteralPath $oldDeleted
    $appId = 'NIKKE_DefaultDir_QA_' + $edition.Name + '_' + [Guid]::NewGuid().ToString('N')
    $regPath = 'Software\Microsoft\Windows\CurrentVersion\Uninstall\' + $appId + '_is1'
    $baseKey = [Microsoft.Win32.RegistryKey]::OpenBaseKey([Microsoft.Win32.RegistryHive]::CurrentUser, [Microsoft.Win32.RegistryView]::Registry64)
    $fixtureKey = $null
    $ownsKey = $false
    try {
        $existingKey = $baseKey.OpenSubKey($regPath)
        if ($null -ne $existingKey) { $existingKey.Dispose(); throw 'Unexpected collision with temporary QA registry key.' }
        foreach ($variant in @(@{ Name='previous_yes'; Previous='yes' }, @{ Name='previous_no'; Previous='no' })) {
            $issPath = Join-Path $editionRoot ($variant.Name + '.iss')
            $issText = @"
[Setup]
AppId=$appId
AppName=Inert installer default-directory QA
AppVersion=0.0.0
DefaultDirName=$($edition.Default)
UsePreviousAppDir=$($variant.Previous)
DisableDirPage=no
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
Uninstallable=yes
CreateUninstallRegKey=no
DisableWelcomePage=yes
DisableReadyPage=no
DisableProgramGroupPage=yes
OutputBaseFilename=$($variant.Name)
Compression=none

[Code]
function ToCodeUnits(const Text: String): String;
var I: Integer;
begin
  Result := '';
  for I := 1 to Length(Text) do
    Result := Result + IntToStr(Ord(Text[I])) + ',';
end;

procedure RecordLine(const Text: String);
begin
  SaveStringToFile(ExpandConstant('{param:RESULT}'), Text + #13#10, True);
end;

procedure InitializeWizard;
begin
  RecordLine('DIR_CODES=' + ToCodeUnits(WizardDirValue));
  RecordLine('STOPPED_BEFORE_INSTALL=true');
  Abort;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  RecordLine('PREPARE_REACHED=true');
  Result := 'Inert QA: installation is forbidden.';
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssInstall then begin
    RecordLine('INSTALL_REACHED=true');
    Abort;
  end;
end;
"@
            [IO.File]::WriteAllText($issPath, $issText, [Text.UTF8Encoding]::new($true))
            $compileOutput = & $IsccPath /Q ('/O' + $editionRoot) $issPath 2>&1
            if ($LASTEXITCODE -ne 0) { throw "Inert native fixture compilation failed: $($compileOutput | Out-String)" }
        }
        $fixtureKey = $baseKey.CreateSubKey($regPath)
        $ownsKey = $true
        $fixtureKey.SetValue('DisplayName', 'Temporary NIKKE default-directory QA ' + $appId, [Microsoft.Win32.RegistryValueKind]::String)
        $fixtureKey.SetValue('Inno Setup: App Path', $oldExisting, [Microsoft.Win32.RegistryValueKind]::String)
        $fixtureKey.SetValue('InstallLocation', $oldExisting, [Microsoft.Win32.RegistryValueKind]::String)
        $fixtureKey.Flush()
        $yesExe = Join-Path $editionRoot 'previous_yes.exe'
        $noExe = Join-Path $editionRoot 'previous_no.exe'
        Invoke-DefaultDirNativeCase $yesExe $edition.Name 'yes_existing_control' $oldExisting
        Invoke-DefaultDirNativeCase $noExe $edition.Name 'no_existing' $edition.Default
        $fixtureKey.SetValue('Inno Setup: App Path', $oldDeleted, [Microsoft.Win32.RegistryValueKind]::String)
        $fixtureKey.SetValue('InstallLocation', $oldDeleted, [Microsoft.Win32.RegistryValueKind]::String)
        $fixtureKey.Flush()
        Invoke-DefaultDirNativeCase $yesExe $edition.Name 'yes_deleted_control' $oldDeleted
        Invoke-DefaultDirNativeCase $noExe $edition.Name 'no_deleted' $edition.Default
        Invoke-DefaultDirNativeCase $noExe $edition.Name 'no_explicit_user_choice' $customDir -CustomDir $customDir
        Invoke-DefaultDirNativeCase $yesExe $edition.Name 'yes_explicit_user_choice_control' $customDir -CustomDir $customDir
        $fixtureKey.Dispose()
        $fixtureKey = $null
        $baseKey.DeleteSubKeyTree($regPath)
        $ownsKey = $false
        Invoke-DefaultDirNativeCase $noExe $edition.Name 'no_fresh_install' $edition.Default
        if ((Test-Path -LiteralPath $oldDeleted) -or (Test-Path -LiteralPath $customDir)) { throw 'Inert setup created a deleted or selected application directory.' }
        if ([IO.File]::ReadAllText((Join-Path $oldExisting 'sentinel.txt')) -ne 'Existing QA data must survive.' -or @(Get-ChildItem -LiteralPath $oldExisting -Force).Count -ne 1) { throw 'Inert setup changed existing fixture data.' }
        Write-Output ("PASS {0}: 7 native directory/history cases; production directory-page directive verified" -f $edition.Name)
    } finally {
        if ($null -ne $fixtureKey) { $fixtureKey.Dispose() }
        if ($ownsKey) { $baseKey.DeleteSubKeyTree($regPath, $false) }
        $remaining = $baseKey.OpenSubKey($regPath)
        if ($null -ne $remaining) { $remaining.Dispose(); $baseKey.Dispose(); throw ('Temporary QA registry key was not cleaned: HKCU\' + $regPath) }
        $baseKey.Dispose()
    }
}
$script:ResultRecords | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $qaRoot 'results.json') -Encoding UTF8
Write-Output "PASS native=$script:NativePassed directives=$script:DirectivePassed; both temporary HKCU QA keys cleaned; no installation or C/D program writes"
Write-Output "QA=$qaRoot"
