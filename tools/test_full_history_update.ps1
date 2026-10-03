param(
    [string]$PatchRoot = "",
    [string]$ExpectedVersion = "0.1.24"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DistRoot = [IO.Path]::GetFullPath((Join-Path $ProjectRoot "dist"))
if (-not $PatchRoot) {
    $PatchRoot = Join-Path $DistRoot ("updates\NIKKE_C_ARENA_Tool_完整版_升级补丁_" + $ExpectedVersion)
}
$PatchRoot = [IO.Path]::GetFullPath($PatchRoot)
$Apply = Join-Path $PatchRoot "apply_update.ps1"
$PayloadRoot = Join-Path $PatchRoot "payload"
$MissingBaseRoot = Join-Path $PatchRoot "missing_only\runtime_python310_base"
$RosterDefaultsPath = Join-Path $PatchRoot "roster_defaults\nikke_names.json"
foreach ($required in @($Apply, (Join-Path $PayloadRoot "RELEASE_INFO.json"), $RosterDefaultsPath, (Join-Path $MissingBaseRoot "python.exe"))) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) { throw "Missing test input: $required" }
}

function Read-Hash([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { throw "Missing expected file: $Path" }
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash
}

function Write-TestText([string]$Path, [string]$Text) {
    New-Item -ItemType Directory -Path (Split-Path -Parent $Path) -Force | Out-Null
    [IO.File]::WriteAllText($Path, $Text, [Text.UTF8Encoding]::new($false))
}

function Write-TestJson([string]$Path, $Value) {
    Write-TestText $Path (($Value | ConvertTo-Json -Depth 100) + [Environment]::NewLine)
}

function Set-TestProperty($Object, [string]$Name, $Value) {
    if ($Object.PSObject.Properties.Name -contains $Name) {
        $Object.$Name = $Value
    } else {
        $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
    }
}

function Build-HashMap([string]$Root) {
    $map = @{}
    foreach ($file in Get-ChildItem -LiteralPath $Root -Recurse -File) {
        $relative = $file.FullName.Substring($Root.Length).TrimStart([char[]]@('\', '/'))
        $map[$relative] = Read-Hash $file.FullName
    }
    return $map
}

function Assert-HashMap([string]$Root, $Map, [string]$Description) {
    foreach ($relative in $Map.Keys) {
        $path = Join-Path $Root $relative
        if ((Read-Hash $path) -ne $Map[$relative]) {
            throw "$Description changed: $path"
        }
    }
}

function Copy-HistoricalProgram([string]$SourceRoot, [string]$TargetRoot) {
    # Do not duplicate or create links to the large original runtime directories.
    # Every program/resource file is copied; updates cannot write through to an
    # original release directory via a junction or a hard link.
    foreach ($file in Get-ChildItem -LiteralPath $SourceRoot -Recurse -File) {
        $relative = $file.FullName.Substring($SourceRoot.Length).TrimStart([char[]]@('\', '/'))
        if ($relative -match '^(runtime_[^\\]+|wheelhouse_gpu|update_backups|__pycache__)(\\|$)' -or $file.Extension -eq '.pyc') { continue }
        $destination = Join-Path $TargetRoot $relative
        New-Item -ItemType Directory -Path (Split-Path -Parent $destination) -Force | Out-Null
        Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
    }
}

function Invoke-TestUpdate([string]$InstallRoot, [string]$LogPath) {
    $output = & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Apply -InstallRoot $InstallRoot 2>&1
    $exitCode = $LASTEXITCODE
    Write-TestText $LogPath (($output | ForEach-Object { $_.ToString() }) -join [Environment]::NewLine)
    if ($exitCode -ne 0) { throw "Actual updater exited with $exitCode; see $LogPath" }
}

function Assert-Roster([string]$InstallRoot, $DefaultRoster, $CustomValues, [string]$Marker) {
    $rosterPath = Join-Path $InstallRoot "dataanalysis\arena_ocr_tool\data\nikke_names.json"
    $backupPath = Join-Path $InstallRoot "dataanalysis\arena_ocr_tool\data\nikke_names.backup.json"
    $actual = Get-Content -LiteralPath $rosterPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($actual.update_qa_marker -ne $Marker) { throw "Roster custom metadata was discarded" }
    $countFields = @{
        names = "count"
        special_names = "special_count"
        collection_names = "collection_count"
        protected_names = "protected_count"
        protected_collection_names = "protected_collection_count"
    }
    foreach ($field in $countFields.Keys) {
        $values = @($actual.$field)
        if ($values -notcontains $CustomValues[$field]) { throw "Custom roster entry was discarded: $field" }
        foreach ($name in @($DefaultRoster.$field)) {
            if ($values -notcontains $name) { throw "Standard roster entry missing after update: $field / $name" }
        }
        if ([int]$actual.($countFields[$field]) -ne $values.Count) { throw "Roster count was not refreshed: $field" }
    }
    if ((Read-Hash $rosterPath) -ne (Read-Hash $backupPath)) { throw "Roster recovery copy does not match the merged roster" }
}

function Find-OriginalBackup([string]$InstallRoot, [string]$RelativePath, [string]$ExpectedHash) {
    $backupRoot = Join-Path $InstallRoot "update_backups"
    if (-not (Test-Path -LiteralPath $backupRoot -PathType Container)) { throw "Updater created no backup directory" }
    foreach ($directory in Get-ChildItem -LiteralPath $backupRoot -Directory) {
        $candidate = Join-Path $directory.FullName $RelativePath
        if ((Test-Path -LiteralPath $candidate -PathType Leaf) -and (Read-Hash $candidate) -eq $ExpectedHash) {
            return $candidate
        }
    }
    throw "Original file was not retained in update_backups: $RelativePath"
}

function Assert-OcrPayload([string]$InstallRoot) {
    foreach ($relative in @(
        "dataanalysis\arena_ocr_tool\main.py",
        "dataanalysis\arena_ocr_tool\recognizer\arena_ocr.py",
        "dataanalysis\arena_ocr_tool\recognizer\result_parser.py",
        "dataanalysis\arena_ocr_tool\recognizer\exporter.py"
    )) {
        if ((Read-Hash (Join-Path $InstallRoot $relative)) -ne (Read-Hash (Join-Path $ProjectRoot $relative))) {
            throw "New OCR source was not installed: $relative"
        }
    }
    $engine = Get-Content -LiteralPath (Join-Path $InstallRoot "dataanalysis\arena_ocr_tool\recognizer\arena_ocr.py") -Raw -Encoding UTF8
    if (-not $engine.Contains('"use_angle_cls": False') -or -not $engine.Contains('self.reader.ocr(arr, cls=False)')) {
        throw "Updated OCR engine does not contain fixed-orientation settings"
    }
}

$patchInfo = Get-Content -LiteralPath (Join-Path $PayloadRoot "RELEASE_INFO.json") -Raw -Encoding UTF8 | ConvertFrom-Json
if ($patchInfo.version -ne $ExpectedVersion) { throw "Patch target version differs from $ExpectedVersion" }
foreach ($forbidden in @("mods", "nikke_logitech_mouse.py", "runtime_gpu", "runtime_core", "runtime_cpu", "runtime_python310_base")) {
    if (Test-Path -LiteralPath (Join-Path $PayloadRoot $forbidden)) { throw "Unexpected direct-copy payload: $forbidden" }
}
$payloadHashes = Build-HashMap $PayloadRoot
$baseHashes = Build-HashMap $MissingBaseRoot
$defaultRoster = Get-Content -LiteralPath $RosterDefaultsPath -Raw -Encoding UTF8 | ConvertFrom-Json
$history = @(Get-ChildItem -LiteralPath $DistRoot -Directory | Where-Object {
    ($_.Name -eq "NIKKE_Arena_Tool_0.1.0" -or $_.Name -match '^r_0\.1\.\d+$') -and
    (Test-Path -LiteralPath (Join-Path $_.FullName "RELEASE_INFO.json"))
} | ForEach-Object {
    $info = Get-Content -LiteralPath (Join-Path $_.FullName "RELEASE_INFO.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    if ([version]$info.version -lt [version]$ExpectedVersion) {
        [pscustomobject]@{ Root = $_.FullName; Version = [string]$info.version }
    }
} | Sort-Object { [version]$_.Version })
if ($history.Count -eq 0) { throw "No historical full-edition release directories are available for upgrade validation" }

# The unique fixture directory is deliberately retained for review. No original
# release directory or installed user application is modified or removed.
$QaRoot = [IO.Path]::GetFullPath((Join-Path $DistRoot ("isolated_" + $ExpectedVersion + "_history_" + [Guid]::NewGuid().ToString("N"))))
if (-not $QaRoot.StartsWith(($DistRoot.TrimEnd('\') + '\'), [StringComparison]::OrdinalIgnoreCase)) {
    throw "Test fixtures must remain under dist"
}
New-Item -ItemType Directory -Path $QaRoot | Out-Null
$ReportPath = Join-Path $QaRoot "history_update_report.json"
$results = [System.Collections.Generic.List[object]]::new()
$startedAt = (Get-Date).ToString("o")
$failure = $null

try {
    foreach ($release in $history) {
        $sourceRoot = $release.Root
        $installRoot = Join-Path $QaRoot ("from_" + $release.Version)
        New-Item -ItemType Directory -Path $installRoot | Out-Null
        Write-Host ("Testing historical full-edition {0} -> {1}" -f $release.Version, $ExpectedVersion)
        $originalHashes = @{}
        foreach ($relative in @(
            "run_gui.bat", "nikke_gui_launcher.ps1", "nikke_round_config.json",
            "RELEASE_INFO.json", "dataanalysis\arena_ocr_tool\main.py",
            "dataanalysis\arena_ocr_tool\data\nikke_names.json",
            "runtime_core\python.exe", "runtime_cpu\python.exe", "runtime_python310_base\python.exe"
        )) {
            $path = Join-Path $sourceRoot $relative
            if (Test-Path -LiteralPath $path -PathType Leaf) { $originalHashes[$relative] = Read-Hash $path }
        }
        Copy-HistoricalProgram $sourceRoot $installRoot
        $oldMainHash = Read-Hash (Join-Path $installRoot "dataanalysis\arena_ocr_tool\main.py")
        $protectedHashes = @{}
        $marker = "user_data_from_" + $release.Version
        foreach ($configName in @("nikke_round_config.json", "nikke_character_capture_config.json")) {
            $path = Join-Path $installRoot $configName
            if (Test-Path -LiteralPath $path) {
                $config = Get-Content -LiteralPath $path -Raw -Encoding UTF8 | ConvertFrom-Json
            } else { $config = [pscustomobject]@{} }
            Set-TestProperty $config "update_qa_marker" $marker
            Write-TestJson $path $config
            $protectedHashes[$configName] = Read-Hash $path
        }
        foreach ($relative in @(
            "screenshots\user_capture.txt", "custom_backgrounds\user_background.txt",
            "support_custom_backgrounds\user_support_background.txt", "group_custom_backgrounds\user_group_background.txt",
            "exports\user_result.txt", "logs\user_run.log", "runtime_gpu\Scripts\user_runtime_keep.txt"
        )) {
            $path = Join-Path $installRoot $relative
            Write-TestText $path ($marker + " / " + $relative)
            $protectedHashes[$relative] = Read-Hash $path
        }
        $hadBase = Test-Path -LiteralPath (Join-Path $sourceRoot "runtime_python310_base") -PathType Container
        foreach ($runtime in @("runtime_core", "runtime_cpu", "runtime_python310_base")) {
            $originalPython = Join-Path $sourceRoot ($runtime + "\python.exe")
            if (-not (Test-Path -LiteralPath $originalPython -PathType Leaf)) { continue }
            $pythonRelative = $runtime + "\python.exe"
            $pythonTarget = Join-Path $installRoot $pythonRelative
            New-Item -ItemType Directory -Path (Split-Path -Parent $pythonTarget) -Force | Out-Null
            Copy-Item -LiteralPath $originalPython -Destination $pythonTarget -Force
            $protectedHashes[$pythonRelative] = Read-Hash $pythonTarget
            $sentinelRelative = $runtime + "\existing_runtime_keep.txt"
            $sentinel = Join-Path $installRoot $sentinelRelative
            Write-TestText $sentinel ($marker + " / preserve entire " + $runtime)
            $protectedHashes[$sentinelRelative] = Read-Hash $sentinel
        }
        $customValues = @{}
        $rosterPath = Join-Path $installRoot "dataanalysis\arena_ocr_tool\data\nikke_names.json"
        $roster = Get-Content -LiteralPath $rosterPath -Raw -Encoding UTF8 | ConvertFrom-Json
        foreach ($field in @("names", "special_names", "collection_names", "protected_names", "protected_collection_names")) {
            $customValues[$field] = "QA_CUSTOM_" + $field + "_" + $release.Version
            Set-TestProperty $roster $field (@($roster.$field) + @($customValues[$field]))
        }
        Set-TestProperty $roster "update_qa_marker" $marker
        Write-TestJson $rosterPath $roster
        $oldRosterHash = Read-Hash $rosterPath

        Invoke-TestUpdate $installRoot (Join-Path $installRoot "first_update_console.log")
        Assert-HashMap $installRoot $payloadHashes "Installed program payload"
        Assert-HashMap $installRoot $protectedHashes "Existing user configuration, data or runtime"
        Assert-OcrPayload $installRoot
        Assert-Roster $installRoot $defaultRoster $customValues $marker
        $mainBackup = Find-OriginalBackup $installRoot "dataanalysis\arena_ocr_tool\main.py" $oldMainHash
        $rosterBackup = Find-OriginalBackup $installRoot "dataanalysis\arena_ocr_tool\data\nikke_names.json" $oldRosterHash
        $actualInfo = Get-Content -LiteralPath (Join-Path $installRoot "RELEASE_INFO.json") -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($actualInfo.version -ne $ExpectedVersion) { throw "Release metadata was not updated" }
        if (-not $hadBase) {
            Assert-HashMap (Join-Path $installRoot "runtime_python310_base") $baseHashes "Newly installed Python base"
        } else {
            $baseFileCount = @(Get-ChildItem -LiteralPath (Join-Path $installRoot "runtime_python310_base") -Recurse -File).Count
            if ($baseFileCount -ne 2) { throw "Existing Python base directory received additional payload files" }
        }

        # A previously missing base is now a user-owned existing directory.
        # Reapplying the patch must leave it and all original user data intact.
        $baseMarkerRelative = "runtime_python310_base\repeat_update_keep.txt"
        Write-TestText (Join-Path $installRoot $baseMarkerRelative) ($marker + " / repeated update")
        $protectedHashes[$baseMarkerRelative] = Read-Hash (Join-Path $installRoot $baseMarkerRelative)
        Invoke-TestUpdate $installRoot (Join-Path $installRoot "repeat_update_console.log")
        Assert-HashMap $installRoot $payloadHashes "Reapplied program payload"
        Assert-HashMap $installRoot $protectedHashes "User data after repeated update"
        Assert-Roster $installRoot $defaultRoster $customValues $marker
        if (-not $hadBase) {
            Assert-HashMap (Join-Path $installRoot "runtime_python310_base") $baseHashes "Python base after repeated update"
        }
        if ((Read-Hash $mainBackup) -ne $oldMainHash -or (Read-Hash $rosterBackup) -ne $oldRosterHash) {
            throw "Repeated update overwrote the original program or roster backup"
        }
        Assert-HashMap $sourceRoot $originalHashes "Read-only historical release"
        [void]$results.Add([pscustomobject]@{
            source_version = $release.Version
            target_version = $ExpectedVersion
            fixture = $installRoot
            program_payload_files_verified = $payloadHashes.Count
            preserved_user_runtime_files_verified = $protectedHashes.Count
            python_base_behavior = $(if ($hadBase) { "existing_directory_preserved" } else { "missing_directory_installed" })
            python_base_files_verified = $(if ($hadBase) { 2 } else { $baseHashes.Count })
            original_program_backup = $mainBackup
            original_roster_backup = $rosterBackup
            repeated_update = "passed"
            original_release_preserved = $true
            status = "passed"
        })
        Write-Host ("PASS historical {0}; payload {1} files; base {2}" -f $release.Version, $payloadHashes.Count, $(if ($hadBase) { "preserved" } else { "installed" }))
    }
} catch {
    $failure = $_.Exception.Message
    throw
} finally {
    Write-TestJson $ReportPath ([ordered]@{
        target_version = $ExpectedVersion
        patch_root = $PatchRoot
        started_at = $startedAt
        completed_at = (Get-Date).ToString("o")
        historical_versions_available = $history.Count
        historical_versions_passed = $results.Count
        status = $(if ($null -eq $failure) { "passed" } else { "failed" })
        failure = $failure
        fixtures = @($results.ToArray())
    })
}
Write-Host ("Full-history update verification passed for {0} historical versions. Report: {1}" -f $results.Count, $ReportPath)
