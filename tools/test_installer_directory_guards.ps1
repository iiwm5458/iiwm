param([string]$IsccPath = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe')
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$qaRoot = Join-Path $projectRoot ('work\installer_directory_guards_' + [Guid]::NewGuid().ToString('N'))
if (-not (Test-Path -LiteralPath $IsccPath -PathType Leaf)) { throw 'Inno Setup compiler missing.' }
New-Item -ItemType Directory -Path $qaRoot | Out-Null

function Quote-Pascal([string]$Value) { return "'" + $Value.Replace("'", "''") + "'" }
$editions = @(
    @{ Name='Full'; Script='installer\NIKKE_Arena_Tool.iss'; Product='NIKKE C ARENA Tool'; Other='NIKKE C ARENA 截图工具 轻量版'; Launcher='run_gui.bat'; OtherLauncher='run_capture_lite.bat'; Default='C:\NIKKE_C_ARENA_Tool\NIKKE C ARENA Tool' },
    @{ Name='Lite'; Script='installer\NIKKE_Arena_Capture_Lite.iss'; Product='NIKKE C ARENA 截图工具 轻量版'; Other='NIKKE C ARENA Tool'; Launcher='run_capture_lite.bat'; OtherLauncher='run_gui.bat'; Default='C:\NIKKE_C_ARENA_Tool\NIKKE C ARENA 截图工具 轻量版' }
)
$passed = 0
foreach ($edition in $editions) {
    $source = [IO.File]::ReadAllText((Join-Path $projectRoot $edition.Script), [Text.Encoding]::UTF8)
    foreach ($line in @(('DefaultDirName=' + $edition.Default), 'DisableDirPage=no', 'UsePreviousAppDir=no', 'PrivilegesRequired=lowest')) {
        if ($source -notmatch ('(?m)^' + [regex]::Escape($line) + '\s*$')) { throw "Wrong installer setting: $($edition.Name) / $line" }
    }
    $codeParts = [regex]::Split($source, '(?mi)^\[Code\]\s*$')
    if ($codeParts.Count -ne 2) { throw 'Expected a single production [Code] section.' }
    $editionRoot = Join-Path $qaRoot $edition.Name
    New-Item -ItemType Directory -Path $editionRoot | Out-Null
    $paths = @{}
    foreach ($case in @('normal','own','other_product','other_launcher','both_launchers','escaped_own','escaped_other','invalid_info','unknown_product','new_parent','blocked')) { $paths[$case] = Join-Path $editionRoot $case }
    foreach ($case in @('own','other_product','other_launcher','both_launchers','escaped_own','escaped_other','invalid_info','unknown_product')) { New-Item -ItemType Directory -Path $paths[$case] | Out-Null }
    [IO.File]::WriteAllText((Join-Path $paths.own $edition.Launcher), '@echo off', [Text.Encoding]::ASCII)
    @{product=$edition.Product} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $paths.own 'RELEASE_INFO.json') -Encoding UTF8
    @{product=$edition.Other} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $paths.other_product 'RELEASE_INFO.json') -Encoding UTF8
    [IO.File]::WriteAllText((Join-Path $paths.other_launcher $edition.OtherLauncher), '@echo off', [Text.Encoding]::ASCII)
    foreach ($launcher in @($edition.Launcher,$edition.OtherLauncher)) { [IO.File]::WriteAllText((Join-Path $paths.both_launchers $launcher), '@echo off', [Text.Encoding]::ASCII) }
    foreach ($case in @('escaped_own','escaped_other')) {
        $product = if ($case -eq 'escaped_own') { $edition.Product } else { $edition.Other }
        $escapedProduct = -join @($product.ToCharArray() | ForEach-Object { '\u' + ([int][char]$_).ToString('x4') })
        [IO.File]::WriteAllText((Join-Path $paths[$case] 'RELEASE_INFO.json'), ('{"product":"' + $escapedProduct + '"}'), [Text.Encoding]::ASCII)
    }
    [IO.File]::WriteAllText((Join-Path $paths.invalid_info 'RELEASE_INFO.json'), '{"product":', [Text.Encoding]::ASCII)
    [IO.File]::WriteAllText((Join-Path $paths.unknown_product 'RELEASE_INFO.json'), '{"product":"Unrelated Application"}', [Text.Encoding]::ASCII)
    [IO.File]::WriteAllText($paths.blocked, 'BLOCKER MUST REMAIN', [Text.Encoding]::ASCII)
    $resultPath = Join-Path $editionRoot 'results.txt'
    $scriptPath = Join-Path $editionRoot 'native_guard_test.iss'
    $pNormal = Quote-Pascal $paths.normal
    $pOwn = Quote-Pascal $paths.own
    $pOther = Quote-Pascal $paths.other_product
    $pLauncher = Quote-Pascal $paths.other_launcher
    $pBoth = Quote-Pascal $paths.both_launchers
    $pEscapedOwn = Quote-Pascal $paths.escaped_own
    $pEscapedOther = Quote-Pascal $paths.escaped_other
    $pInvalid = Quote-Pascal $paths.invalid_info
    $pUnknown = Quote-Pascal $paths.unknown_product
    $pNested = Quote-Pascal (Join-Path $paths.new_parent 'nested\tool')
    $pBlocked = Quote-Pascal (Join-Path $paths.blocked 'nested')
    $pResult = Quote-Pascal $resultPath
    $testScript = @"
[Setup]
AppId=InstallerDirectoryGuardQA_$($edition.Name)_$([Guid]::NewGuid().ToString('N'))
AppName=Installer directory guard QA
AppVersion=0.0.0
DefaultDirName={tmp}\inert_guard_qa
PrivilegesRequired=lowest
Uninstallable=no
CreateUninstallRegKey=no
OutputBaseFilename=native_guard_test
Compression=none
DisableWelcomePage=yes
DisableReadyPage=yes

[Code]
$($codeParts[1])

var TestFailures: Integer;

procedure RecordTest(const Name: String; const OK: Boolean);
begin
  if OK then
    SaveStringToFile($pResult, 'PASS ' + Name + #13#10, True)
  else begin
    SaveStringToFile($pResult, 'FAIL ' + Name + #13#10, True);
    TestFailures := TestFailures + 1;
  end;
end;

function InitializeSetup(): Boolean;
begin
  TestFailures := 0;
  RecordTest('new directory allowed', CheckEditionInstallDirectory($pNormal) = '');
  RecordTest('directory validation is read only', not DirExists($pNormal));
  RecordTest('same edition allowed', CheckEditionInstallDirectory($pOwn) = '');
  RecordTest('opposite product refused', CheckEditionInstallDirectory($pOther) <> '');
  RecordTest('opposite launcher refused', CheckEditionInstallDirectory($pLauncher) <> '');
  RecordTest('both launchers refused', CheckEditionInstallDirectory($pBoth) <> '');
  RecordTest('Unicode escaped same product allowed', CheckEditionInstallDirectory($pEscapedOwn) = '');
  RecordTest('Unicode escaped opposite product refused', CheckEditionInstallDirectory($pEscapedOther) <> '');
  RecordTest('broken product metadata refused', CheckEditionInstallDirectory($pInvalid) <> '');
  RecordTest('unrelated product refused', CheckEditionInstallDirectory($pUnknown) <> '');
  RecordTest('nested target can be created and written', EnsureInstallDirectoryWritable($pNested) = '');
  RecordTest('nested target exists', DirExists($pNested));
  RecordTest('file blocker returns a write error', EnsureInstallDirectoryWritable($pBlocked) <> '');
  RecordTest('same directory writable probe succeeds', ProbeInstallDirectoryWritable($pOwn) = '');
  SaveStringToFile($pResult, 'FAILURES=' + IntToStr(TestFailures) + #13#10, True);
  Result := False;
end;
"@
    [IO.File]::WriteAllText($scriptPath, $testScript, [Text.UTF8Encoding]::new($true))
    $compileOutput = & $IsccPath /Q ('/O' + $editionRoot) $scriptPath 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Native test compilation failed: $($compileOutput | Out-String)" }
    $process = Start-Process -FilePath (Join-Path $editionRoot 'native_guard_test.exe') -ArgumentList '/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART','/SP-' -WindowStyle Hidden -PassThru
    try {
        if (-not $process.WaitForExit(30000)) { throw 'Native guard self-test did not finish; no installation was requested.' }
    } finally { $process.Dispose() }
    if (-not (Test-Path -LiteralPath $resultPath)) { throw 'Native test produced no result.' }
    $results = [IO.File]::ReadAllText($resultPath)
    if ($results.Contains('FAIL ') -or -not $results.Contains('FAILURES=0')) { throw "Native guard test failed: $results" }
    if ([IO.File]::ReadAllText($paths.blocked) -ne 'BLOCKER MUST REMAIN') { throw 'Write guard changed the file blocker.' }
    if (@(Get-ChildItem -LiteralPath $paths.own -Force).Count -ne 2) { throw 'Write guard left probe files in existing directory.' }
    if (@(Get-ChildItem -LiteralPath (Join-Path $paths.new_parent 'nested\tool') -Force).Count -ne 0) { throw 'Write guard left probe files in new directory.' }
    $passed += 14
    Write-Output ("PASS $($edition.Name): 14 native directory guard cases, defaults and existing data preserved")
}
Write-Output "PASS total=$passed native cases; no real installation, C/D target write or registry registration"
Write-Output "QA=$qaRoot"
