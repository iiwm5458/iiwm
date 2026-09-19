param(
    [string]$FullVersion = "0.1.20",
    [string]$LiteVersion = "0.1.12",
    [string]$PatchDate = (Get-Date -Format "yyyy-MM-dd")
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DistRoot = Join-Path $ProjectRoot "dist"
$UpdatesRoot = Join-Path $DistRoot "updates"
$ReleaseTimestamp = Get-Date -Format "yyyy-MM-dd HH:mm"

function Write-Utf8Text([string]$Path, [string]$Content) {
    [IO.File]::WriteAllText($Path, $Content, [Text.UTF8Encoding]::new($true))
}

function Write-AsciiText([string]$Path, [string]$Content) {
    [IO.File]::WriteAllText($Path, $Content, [Text.ASCIIEncoding]::new())
}

function Write-Step([string]$Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message)
}

function Get-RosterList($Roster, [string]$Field) {
    if ($null -eq $Roster -or -not ($Roster.PSObject.Properties.Name -contains $Field)) {
        return @()
    }
    return @($Roster.$Field | ForEach-Object { [string]$_ })
}

function Copy-PayloadFile([string]$ReleaseRoot, [string]$PayloadRoot, [string]$RelativePath) {
    $source = Join-Path $ReleaseRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Patch source is missing: $source"
    }
    $destination = Join-Path $PayloadRoot $RelativePath
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

function Write-Checksums([string]$PatchRoot) {
    $lines = Get-ChildItem -LiteralPath $PatchRoot -File -Recurse |
        Where-Object { $_.Name -ne "SHA256SUMS.txt" } |
        Sort-Object FullName |
        ForEach-Object {
            $relative = $_.FullName.Substring($PatchRoot.Length).TrimStart([char[]]@([char]92, [char]47))
            "{0}  {1}" -f (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash, $relative
        }
    Write-Utf8Text (Join-Path $PatchRoot "SHA256SUMS.txt") ($lines -join [Environment]::NewLine)
}

function Write-ReleaseChecksums([string[]]$ArtifactPaths, [string]$OutputPath) {
    $lines = foreach ($artifactPath in $ArtifactPaths) {
        if (-not (Test-Path -LiteralPath $artifactPath)) {
            throw "Release artifact is missing: $artifactPath"
        }
        "{0}  {1}" -f (Get-FileHash -LiteralPath $artifactPath -Algorithm SHA256).Hash, (Split-Path -Leaf $artifactPath)
    }
    Write-Utf8Text $OutputPath ($lines -join [Environment]::NewLine)
}

function Write-ApplyScripts(
    [string]$PatchRoot,
    [string]$ExpectedLauncher,
    [string]$ProductName,
    [string]$RosterRelativePath = ""
) {
    $applyScript = @'
$ErrorActionPreference = "Stop"
$ExpectedLauncher = "__EXPECTED_LAUNCHER__"
$ProductName = "__PRODUCT_NAME__"
$RosterRelativePath = "__ROSTER_RELATIVE_PATH__"
$PatchRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PayloadRoot = Join-Path $PatchRoot "payload"
$RosterAdditionsPath = Join-Path $PatchRoot "roster_additions.json"

function Select-InstallRoot {
    if (Test-Path -LiteralPath (Join-Path $PatchRoot $ExpectedLauncher)) { return $PatchRoot }
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "请选择 $ProductName 的安装目录（其中应包含 $ExpectedLauncher）"
    $dialog.ShowNewFolderButton = $false
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        throw "未选择安装目录，升级已取消。"
    }
    return $dialog.SelectedPath
}

function Backup-ExistingFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $relative = $Path.Substring($InstallRoot.Length).TrimStart([char[]]@([char]92, [char]47))
    $backup = Join-Path $BackupRoot $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
    Copy-Item -LiteralPath $Path -Destination $backup -Force
}

function Get-StringList($Object, [string]$PropertyName) {
    if ($null -eq $Object -or -not ($Object.PSObject.Properties.Name -contains $PropertyName)) {
        return @()
    }
    return @($Object.$PropertyName | ForEach-Object { [string]$_ })
}

function Merge-RosterAdditions {
    if ([string]::IsNullOrWhiteSpace($RosterRelativePath) -or -not (Test-Path -LiteralPath $RosterAdditionsPath)) {
        return
    }
    $targetPath = Join-Path $InstallRoot $RosterRelativePath
    if (-not (Test-Path -LiteralPath $targetPath)) {
        Write-Warning "未找到用户妮姬名单，已跳过名单增量合并：$targetPath"
        return
    }
    try {
        $roster = Get-Content -LiteralPath $targetPath -Raw -Encoding utf8 | ConvertFrom-Json
        $additions = Get-Content -LiteralPath $RosterAdditionsPath -Raw -Encoding utf8 | ConvertFrom-Json
    } catch {
        Write-Warning "无法读取现有妮姬名单，已保留原文件：$targetPath"
        return
    }

    $changed = $false
    foreach ($field in @("names", "special_names", "protected_names")) {
        $current = [System.Collections.Generic.List[string]]::new()
        $seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        foreach ($value in Get-StringList $roster $field) {
            if (-not [string]::IsNullOrWhiteSpace($value) -and $seen.Add($value)) {
                [void]$current.Add($value)
            }
        }
        foreach ($value in Get-StringList $additions $field) {
            if (-not [string]::IsNullOrWhiteSpace($value) -and $seen.Add($value)) {
                [void]$current.Add($value)
                $changed = $true
            }
        }
        if ($roster.PSObject.Properties.Name -contains $field) {
            $roster.$field = @($current.ToArray())
        } else {
            $roster | Add-Member -NotePropertyName $field -NotePropertyValue @($current.ToArray())
            $changed = $true
        }
    }

    foreach ($mapping in @{
        "names" = "count"
        "special_names" = "special_count"
        "protected_names" = "protected_count"
    }.GetEnumerator()) {
        $count = @(Get-StringList $roster $mapping.Key).Count
        if ($roster.PSObject.Properties.Name -contains $mapping.Value) {
            if ([int]$roster.($mapping.Value) -ne $count) { $changed = $true }
            $roster.($mapping.Value) = $count
        } else {
            $roster | Add-Member -NotePropertyName $mapping.Value -NotePropertyValue $count
            $changed = $true
        }
    }

    if ($additions.PSObject.Properties.Name -contains "updated_at") {
        $updatedAt = [string]$additions.updated_at
        if (-not [string]::IsNullOrWhiteSpace($updatedAt)) {
            if ($roster.PSObject.Properties.Name -contains "updated_at") {
                if ([string]$roster.updated_at -ne $updatedAt) { $changed = $true }
                $roster.updated_at = $updatedAt
            } else {
                $roster | Add-Member -NotePropertyName "updated_at" -NotePropertyValue $updatedAt
                $changed = $true
            }
        }
    }

    if ($changed) {
        Backup-ExistingFile $targetPath
        [IO.File]::WriteAllText(
            $targetPath,
            (($roster | ConvertTo-Json -Depth 100) + [Environment]::NewLine),
            [Text.UTF8Encoding]::new($false)
        )
        Write-Host "已合并本次新增妮姬名单。"
    }
}

$InstallRoot = Select-InstallRoot
if (-not (Test-Path -LiteralPath (Join-Path $InstallRoot $ExpectedLauncher))) {
    throw "所选目录不是 $ProductName 的安装目录：未找到 $ExpectedLauncher"
}
if (-not (Test-Path -LiteralPath $PayloadRoot)) {
    throw "补丁内容不完整：未找到 payload 文件夹。"
}

$BackupRoot = Join-Path $InstallRoot ("update_backups\incremental_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
$ProtectedPaths = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($path in @("nikke_round_config.json", "nikke_character_capture_config.json")) {
    [void]$ProtectedPaths.Add($path)
}

foreach ($payloadFile in Get-ChildItem -LiteralPath $PayloadRoot -File -Recurse) {
    $relative = $payloadFile.FullName.Substring($PayloadRoot.Length).TrimStart([char[]]@([char]92, [char]47))
    if ($ProtectedPaths.Contains($relative)) {
        Write-Host "保留用户配置：$relative"
        continue
    }
    $destination = Join-Path $InstallRoot $relative
    Backup-ExistingFile $destination
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $payloadFile.FullName -Destination $destination -Force
}

Merge-RosterAdditions
Write-Host "增量更新完成：$ProductName"
Write-Host "被替换文件的备份位置：$BackupRoot"
'@
    $applyScript = $applyScript.Replace("__EXPECTED_LAUNCHER__", $ExpectedLauncher)
    $applyScript = $applyScript.Replace("__PRODUCT_NAME__", $ProductName)
    $applyScript = $applyScript.Replace("__ROSTER_RELATIVE_PATH__", $RosterRelativePath)
    Write-Utf8Text (Join-Path $PatchRoot "apply_update.ps1") $applyScript

    $batch = @'
@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0apply_update.ps1"
set "rc=%ERRORLEVEL%"
echo.
if not "%rc%"=="0" (echo Update did not complete. Review the message above.) else (echo Update completed. You can restart the app.)
pause
exit /b %rc%
'@
    Write-AsciiText (Join-Path $PatchRoot "apply_update.bat") $batch
}

function Build-IncrementalPatch(
    [string]$PatchName,
    [string]$ReleaseRoot,
    [string]$ExpectedLauncher,
    [string]$ProductName,
    [string[]]$Files,
    [string]$UsageText,
    [string]$UpdateText,
    [string]$RosterRelativePath = ""
) {
    if (-not (Test-Path -LiteralPath $ReleaseRoot)) {
        throw "Release directory is missing: $ReleaseRoot"
    }
    $patchRoot = Join-Path $UpdatesRoot $PatchName
    if (Test-Path -LiteralPath $patchRoot) {
        Remove-Item -LiteralPath $patchRoot -Recurse -Force
    }
    $payloadRoot = Join-Path $patchRoot "payload"
    New-Item -ItemType Directory -Force -Path $payloadRoot | Out-Null
    foreach ($file in $Files) {
        Copy-PayloadFile $ReleaseRoot $payloadRoot $file
    }

    if (-not [string]::IsNullOrWhiteSpace($RosterRelativePath)) {
        $releaseRoster = Join-Path $ReleaseRoot $RosterRelativePath
        if (-not (Test-Path -LiteralPath $releaseRoster)) {
            throw "Release roster is missing: $releaseRoster"
        }
        $roster = Get-Content -LiteralPath $releaseRoster -Raw -Encoding utf8 | ConvertFrom-Json
        $newName = "吉尔提：神力兔女郎"
        if (
            $newName -notin @(Get-RosterList $roster "names") -or
            $newName -notin @(Get-RosterList $roster "special_names") -or
            $newName -notin @(Get-RosterList $roster "protected_names")
        ) {
            throw "Release roster does not include the required new Nikke: $newName"
        }
        $additions = [ordered]@{
            names = @($newName)
            special_names = @($newName)
            protected_names = @($newName)
            updated_at = [string]$roster.updated_at
        } | ConvertTo-Json -Depth 4
        Write-Utf8Text (Join-Path $patchRoot "roster_additions.json") ($additions + [Environment]::NewLine)
    }

    Write-ApplyScripts $patchRoot $ExpectedLauncher $ProductName $RosterRelativePath
    Write-Utf8Text (Join-Path $patchRoot "增量更新补丁使用说明.txt") $UsageText
    Write-Utf8Text (Join-Path $patchRoot ("更新日志_{0}.txt" -f $PatchDate)) $UpdateText
    Write-Checksums $patchRoot

    $zipPath = Join-Path $UpdatesRoot ("{0}.zip" -f $PatchName)
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Compress-Archive -LiteralPath $patchRoot -DestinationPath $zipPath -CompressionLevel Optimal
    Write-Step "Incremental patch is ready: $zipPath"
    return $zipPath
}

New-Item -ItemType Directory -Force -Path $UpdatesRoot | Out-Null

$fullLog = @(
    "NIKKE C ARENA Tool 完整版 本轮增量更新日志",
    "目标版本：$FullVersion",
    "适用基线：完整版 0.1.19。",
    "发布日期：$ReleaseTimestamp。",
    "",
    "1. 国际服与港澳台服自动截图改为人工左键确认推进。",
    "程序仍会把光标定位到当前操作目标，但每一步都等待指挥官亲自按下鼠标左键后才继续；国服原有自动点击逻辑不变。点偏时会把光标放回目标位置，不会误推进截图流程。",
    "缘由：适应海外客户端更新后对程序注入式点击兼容性下降的情况，让截图流程继续可用，同时保持用户对每一次操作的可见控制。",
    "",
    "2. 人工确认提示音改为原创霓虹 8bit 音序。",
    "提示音由方波主音、轻微八度与五度泛音组成，并在后台队列中播放；不阻塞截图，不会连续叠音，也不携带外部音频文件或受版权保护的游戏旋律。",
    "缘由：让连续人工点击更容易跟上节奏，同时避免单调蜂鸣和版权音乐分发风险。",
    "",
    "3. OCR 标准妮姬名单新增《吉尔提：神力兔女郎》。",
    "完整版本补丁会把该角色追加合并到主名单、受保护名单与带冒号特殊名集合；运行时会自动生成安全别名，支持完整名与滚动时可见片段的校准。",
    "缘由：让新角色可被 OCR 正确识别，同时不影响用户自行维护的名单和珍藏品设定。",
    "",
    "补丁范围：仅替换本轮相关启动器、截图核心与版本信息，并增量合并上述妮姬名称；不覆盖截图参数、主题、赛区选择、背景、截图、导出数据或运行日志，也不替换任何 Python、OCR runtime、Paddle 依赖与离线模型。"
) -join [Environment]::NewLine

$liteLog = @(
    "NIKKE C ARENA 截图工具 轻量版 本轮增量更新日志",
    "目标版本：$LiteVersion",
    "适用基线：轻量版 0.1.11。",
    "发布日期：$ReleaseTimestamp。",
    "",
    "1. 国际服与港澳台服自动截图改为人工左键确认推进。",
    "程序仍会把光标定位到当前操作目标，但每一步都等待指挥官亲自按下鼠标左键后才继续；国服原有自动点击逻辑不变。点偏时会把光标放回目标位置，不会误推进截图流程。",
    "缘由：适应海外客户端更新后对程序注入式点击兼容性下降的情况，让截图流程继续可用，同时保持用户对每一次操作的可见控制。",
    "",
    "2. 人工确认提示音改为原创霓虹 8bit 音序。",
    "提示音由方波主音、轻微八度与五度泛音组成，并在后台队列中播放；不阻塞截图，不会连续叠音，也不携带外部音频文件或受版权保护的游戏旋律。",
    "缘由：让连续人工点击更容易跟上节奏，同时避免单调蜂鸣和版权音乐分发风险。",
    "",
    "补丁范围：仅替换本轮相关启动器、截图核心与版本信息，不覆盖截图参数、主题、赛区选择、背景、截图或运行日志，也不替换任何 Python 或截图运行依赖。"
) -join [Environment]::NewLine

$fullUsage = @(
    "NIKKE C ARENA Tool 完整版 0.1.20 增量更新补丁使用说明",
    "",
    "适用基线：完整版 0.1.19。",
    "本补丁只包含本轮海外服人工左键确认、原创 8bit 提示音和名单新增所需文件，不用于补齐更早版本的全部更新。",
    "",
    "1. 完全退出程序。",
    "2. 解压 ZIP。",
    "3. 双击 apply_update.bat。",
    "4. 若补丁不在安装目录中，请在弹窗选择包含 run_gui.bat 的完整版安装目录。",
    "5. 显示《增量更新完成》后重新启动程序。",
    "",
    "不会覆盖：nikke_round_config.json、nikke_character_capture_config.json、用户妮姬名单、主题、赛区、背景、截图、OCR 导出和运行日志。",
    "《吉尔提：神力兔女郎》只会追加进主名单、受保护名单和特殊名集合；原有自定义条目会保留。",
    "被替换的启动器、截图核心与版本信息会备份至安装目录 update_backups\incremental_时间戳。"
) -join [Environment]::NewLine

$liteUsage = @(
    "NIKKE C ARENA 截图工具 轻量版 0.1.12 增量更新补丁使用说明",
    "",
    "适用基线：轻量版 0.1.11。",
    "本补丁只包含本轮海外服人工左键确认与原创 8bit 提示音所需文件，不用于补齐更早版本的全部更新。",
    "",
    "1. 完全退出程序。",
    "2. 解压 ZIP。",
    "3. 双击 apply_update.bat。",
    "4. 若补丁不在安装目录中，请在弹窗选择包含 run_capture_lite.bat 的轻量版安装目录。",
    "5. 显示《增量更新完成》后重新启动程序。",
    "",
    "不会覆盖：nikke_round_config.json、nikke_character_capture_config.json、主题、赛区、背景、截图或运行日志。",
    "被替换的启动器、截图核心与版本信息会备份至安装目录 update_backups\incremental_时间戳。"
) -join [Environment]::NewLine

$fullPatch = @{
    PatchName = "NIKKE_C_ARENA_Tool_完整版_增量更新补丁_$FullVersion"
    ReleaseRoot = Join-Path $DistRoot ("r_$FullVersion")
    ExpectedLauncher = "run_gui.bat"
    ProductName = "NIKKE C ARENA Tool 完整版"
    Files = @("nikke_gui_launcher.ps1", "nikke_round_stitcher.py", "RELEASE_INFO.json")
    UsageText = $fullUsage
    UpdateText = $fullLog
    RosterRelativePath = "dataanalysis\arena_ocr_tool\data\nikke_names.json"
}
$fullZip = Build-IncrementalPatch @fullPatch

$litePatch = @{
    PatchName = "NIKKE_C_ARENA_Capture_Lite_轻量版_增量更新补丁_$LiteVersion"
    ReleaseRoot = Join-Path $DistRoot ("lite_r_$LiteVersion")
    ExpectedLauncher = "run_capture_lite.bat"
    ProductName = "NIKKE C ARENA 截图工具 轻量版"
    Files = @("nikke_capture_lite_launcher.ps1", "nikke_round_stitcher.py", "RELEASE_INFO.json")
    UsageText = $liteUsage
    UpdateText = $liteLog
}
$liteZip = Build-IncrementalPatch @litePatch

$combinedLog = @(
    "NIKKE C ARENA Tool 本次发布更新日志",
    "发布日期：$ReleaseTimestamp",
    "",
    $fullLog,
    "",
    $liteLog
) -join [Environment]::NewLine
Write-Utf8Text (Join-Path $UpdatesRoot ("更新日志_$PatchDate.txt")) $combinedLog

Write-ReleaseChecksums @(
    (Join-Path $DistRoot ("installer\NIKKE_Arena_Tool_Setup_{0}.exe" -f $FullVersion)),
    (Join-Path $DistRoot ("installer\NIKKE_Arena_Capture_Lite_Setup_{0}.exe" -f $LiteVersion)),
    $fullZip,
    $liteZip
) (Join-Path $UpdatesRoot ("SHA256SUMS_$PatchDate.txt"))

Write-Host "完整版增量补丁：$fullZip"
Write-Host "轻量版增量补丁：$liteZip"
