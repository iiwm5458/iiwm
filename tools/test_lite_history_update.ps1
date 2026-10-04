param(
    [string]$PatchRoot = '',
    [string]$ExpectedVersion = '0.1.15'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$distRoot = [IO.Path]::GetFullPath((Join-Path $projectRoot 'dist'))
if (-not $PatchRoot) { $PatchRoot = Join-Path $distRoot ('updates\NIKKE_C_ARENA_Capture_Lite_轻量版_升级补丁_' + $ExpectedVersion) }
$PatchRoot = [IO.Path]::GetFullPath($PatchRoot)
$applyPath = Join-Path $PatchRoot 'apply_update.ps1'
$payloadRoot = Join-Path $PatchRoot 'payload'
$metadataPath = Join-Path $payloadRoot 'RELEASE_INFO.json'
foreach ($path in @($applyPath, $metadataPath, (Join-Path $payloadRoot 'run_capture_lite.bat'))) {
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "Missing Lite history-test input: $path" }
}
$patchInfo = Get-Content -LiteralPath $metadataPath -Raw -Encoding UTF8 | ConvertFrom-Json
if ([string]$patchInfo.version -ne $ExpectedVersion -or [string]$patchInfo.product -cne 'NIKKE C ARENA 截图工具 轻量版') {
    throw 'Patch metadata is not the expected Lite target version.'
}
foreach ($forbidden in @('mods', 'runtime_gpu', 'runtime_core', 'runtime_cpu', 'runtime_python310_base', 'nikke_input_plugins.py', 'nikke_logitech_mouse.py', 'dataanalysis', 'work')) {
    if (Test-Path -LiteralPath (Join-Path $payloadRoot $forbidden)) { throw "Unexpected direct-copy Lite payload: $forbidden" }
}

function Get-LiteHistoryHash([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing expected fixture file: $Path" }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}
function Write-LiteHistoryText([string]$Path, [string]$Text) {
    $null = New-Item -ItemType Directory -Path (Split-Path -Parent $Path) -Force
    [IO.File]::WriteAllText($Path, $Text, [Text.UTF8Encoding]::new($false))
}
function Write-LiteHistoryJson([string]$Path, $Value) {
    Write-LiteHistoryText $Path (($Value | ConvertTo-Json -Depth 100) + [Environment]::NewLine)
}
function Get-LiteHistoryHashMap([string]$Root) {
    $map = @{}
    foreach ($file in @(Get-ChildItem -LiteralPath $Root -File -Recurse)) {
        $relative = $file.FullName.Substring($Root.Length).TrimStart([char[]]@('\', '/'))
        $map[$relative] = Get-LiteHistoryHash $file.FullName
    }
    return $map
}
function Assert-LiteHistoryHashes([string]$Root, $Map, [string]$Description) {
    foreach ($relative in $Map.Keys) {
        if ((Get-LiteHistoryHash (Join-Path $Root $relative)) -ne $Map[$relative]) { throw "$Description changed: $relative" }
    }
}
function Copy-LiteHistoricalProgram([string]$SourceRoot, [string]$TargetRoot) {
    $originalHashes = @{}
    foreach ($file in @(Get-ChildItem -LiteralPath $SourceRoot -File -Recurse)) {
        $relative = $file.FullName.Substring($SourceRoot.Length).TrimStart([char[]]@('\', '/'))
        if ($relative -match '^(runtime_[^\\]+|wheelhouse_gpu|update_backups|__pycache__)(\\|$)' -or $file.Extension -eq '.pyc') { continue }
        $originalHashes[$relative] = Get-LiteHistoryHash $file.FullName
        $destination = Join-Path $TargetRoot $relative
        $null = New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force
        Copy-Item -LiteralPath $file.FullName -Destination $destination
    }
    return $originalHashes
}
function Invoke-LiteHistoryUpdate([string]$InstallRoot, [string]$LogPath) {
    # The generated updater only copies/merges files; no runtime or GUI is run.
    $nativeOutput = @(& powershell.exe -NoProfile -ExecutionPolicy Bypass -File $applyPath -InstallRoot $InstallRoot 2>&1)
    $exitCode = $LASTEXITCODE
    Write-LiteHistoryText $LogPath (($nativeOutput | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine)
    if ($exitCode -ne 0) { throw "Actual Lite updater failed with $exitCode; see $LogPath" }
}
function Find-LiteHistoryBackup([string]$InstallRoot, [string]$RelativePath, [string]$ExpectedHash) {
    $backupRoot = Join-Path $InstallRoot 'update_backups'
    foreach ($directory in @(Get-ChildItem -LiteralPath $backupRoot -Directory -ErrorAction SilentlyContinue)) {
        $candidate = Join-Path $directory.FullName $RelativePath
        if ((Test-Path -LiteralPath $candidate -PathType Leaf) -and (Get-LiteHistoryHash $candidate) -eq $ExpectedHash) { return $candidate }
    }
    throw "Original Lite program backup was not preserved: $RelativePath"
}

$history = @(Get-ChildItem -LiteralPath $distRoot -Directory | Where-Object {
    $_.Name -match '^(lite_r_\d+\.\d+\.\d+|NIKKE_C_ARENA_Capture_Lite_\d+\.\d+\.\d+)$' -and
    (Test-Path -LiteralPath (Join-Path $_.FullName 'RELEASE_INFO.json') -PathType Leaf)
} | ForEach-Object {
    $info = Get-Content -LiteralPath (Join-Path $_.FullName 'RELEASE_INFO.json') -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([string]$info.product -cne 'NIKKE C ARENA 截图工具 轻量版') { throw "Historical folder contains the wrong product: $($_.FullName)" }
    if ([version]$info.version -lt [version]$ExpectedVersion) { [PSCustomObject]@{ Root=$_.FullName; Version=[string]$info.version } }
} | Sort-Object { [version]$_.Version })
if ($history.Count -eq 0) { throw 'No historical Lite releases are available.' }
$qaRoot = [IO.Path]::GetFullPath((Join-Path $distRoot ('isolated_lite_' + $ExpectedVersion + '_history_' + [Guid]::NewGuid().ToString('N'))))
if (-not $qaRoot.StartsWith($distRoot.TrimEnd('\') + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'History fixtures must stay within dist.' }
$null = New-Item -ItemType Directory -Path $qaRoot
$reportPath = Join-Path $qaRoot 'lite_history_update_report.json'
$payloadHashes = Get-LiteHistoryHashMap $payloadRoot
$results = [System.Collections.Generic.List[object]]::new()
$startedAt = (Get-Date).ToString('o')
$failure = $null
try {
    foreach ($release in $history) {
        $sourceRoot = [string]$release.Root
        $installRoot = Join-Path $qaRoot ('from_' + $release.Version)
        $null = New-Item -ItemType Directory -Path $installRoot
        Write-Output ("Testing historical Lite {0} -> {1}" -f $release.Version, $ExpectedVersion)
        $originalHashes = Copy-LiteHistoricalProgram $sourceRoot $installRoot
        $oldLauncherHash = Get-LiteHistoryHash (Join-Path $installRoot 'run_capture_lite.bat')
        $oldGuiHash = Get-LiteHistoryHash (Join-Path $installRoot 'nikke_capture_lite_launcher.ps1')
        $sourceRuntimePython = Join-Path $sourceRoot 'runtime_core\python.exe'
        if (Test-Path -LiteralPath $sourceRuntimePython -PathType Leaf) { $originalHashes['runtime_core\python.exe'] = Get-LiteHistoryHash $sourceRuntimePython }
        $marker = 'QA_KEEP_FROM_LITE_' + $release.Version
        $protectedHashes = @{}
        foreach ($configName in @('nikke_round_config.json', 'nikke_character_capture_config.json')) {
            $configPath = Join-Path $installRoot $configName
            $config = if (Test-Path -LiteralPath $configPath -PathType Leaf) { Get-Content -LiteralPath $configPath -Raw -Encoding UTF8 | ConvertFrom-Json } else { [PSCustomObject]@{} }
            if ($config.PSObject.Properties.Name -contains 'update_qa_marker') { $config.update_qa_marker = $marker }
            else { $config | Add-Member -NotePropertyName update_qa_marker -NotePropertyValue $marker }
            Write-LiteHistoryJson $configPath $config
            $protectedHashes[$configName] = Get-LiteHistoryHash $configPath
        }
        foreach ($relative in @(
            'runtime_core\python.exe', 'runtime_core\Lib\user_runtime_keep.txt',
            'screenshots\user_capture.txt', 'custom_backgrounds\user_background.txt',
            'support_custom_backgrounds\user_support_background.txt', 'group_custom_backgrounds\user_group_background.txt',
            'logs\user_capture.log', 'exports\user_export.txt', 'user_directory\nested\user_notes.txt'
        )) {
            Write-LiteHistoryText (Join-Path $installRoot $relative) ($marker + ' / inert sentinel / ' + $relative)
            $protectedHashes[$relative] = Get-LiteHistoryHash (Join-Path $installRoot $relative)
        }
        Invoke-LiteHistoryUpdate $installRoot (Join-Path $installRoot 'first_update_console.log')
        Assert-LiteHistoryHashes $installRoot $payloadHashes 'Updated Lite payload'
        Assert-LiteHistoryHashes $installRoot $protectedHashes 'Existing Lite settings, runtime and personal data'
        $actualInfo = Get-Content -LiteralPath (Join-Path $installRoot 'RELEASE_INFO.json') -Raw -Encoding UTF8 | ConvertFrom-Json
        if ([string]$actualInfo.version -ne $ExpectedVersion -or [string]$actualInfo.product -cne [string]$patchInfo.product) { throw 'Installed Lite metadata was not updated correctly.' }
        $launcherBackup = Find-LiteHistoryBackup $installRoot 'run_capture_lite.bat' $oldLauncherHash
        $guiBackup = Find-LiteHistoryBackup $installRoot 'nikke_capture_lite_launcher.ps1' $oldGuiHash
        Invoke-LiteHistoryUpdate $installRoot (Join-Path $installRoot 'repeat_update_console.log')
        Assert-LiteHistoryHashes $installRoot $payloadHashes 'Reapplied Lite payload'
        Assert-LiteHistoryHashes $installRoot $protectedHashes 'Lite personal data after repeat update'
        if ((Get-LiteHistoryHash $launcherBackup) -ne $oldLauncherHash -or (Get-LiteHistoryHash $guiBackup) -ne $oldGuiHash) { throw 'Repeated update changed the original program backup.' }
        Assert-LiteHistoryHashes $sourceRoot $originalHashes 'Read-only original historical Lite release'
        $null = $results.Add([PSCustomObject]@{
            source_version=$release.Version; target_version=$ExpectedVersion; fixture=$installRoot
            payload_files_verified=$payloadHashes.Count; preserved_user_runtime_files_verified=$protectedHashes.Count
            original_source_hashes_verified=$originalHashes.Count; original_launcher_backup=$launcherBackup
            original_gui_backup=$guiBackup; repeated_update='passed'; original_release_preserved=$true; status='passed'
        })
        Write-Output ("PASS historical Lite {0}; payload {1} files; {2} protected files" -f $release.Version, $payloadHashes.Count, $protectedHashes.Count)
    }
    Assert-LiteHistoryHashes $payloadRoot $payloadHashes 'Read-only patch payload'
} catch { $failure = $_.Exception.Message; throw }
finally {
    Write-LiteHistoryJson $reportPath ([ordered]@{
        target_version=$ExpectedVersion; patch_root=$PatchRoot; started_at=$startedAt; completed_at=(Get-Date).ToString('o')
        historical_versions_available=$history.Count; historical_versions_passed=$results.Count
        status=$(if ($null -eq $failure) { 'passed' } else { 'failed' }); failure=$failure; fixtures=@($results.ToArray())
    })
}
Write-Output ("Lite history update verification passed for {0} historical releases; report: {1}" -f $results.Count, $reportPath)
