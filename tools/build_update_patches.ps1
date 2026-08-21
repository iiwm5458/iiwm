param(
    [string]$FullVersion = "0.1.18",
    [string]$LiteVersion = "0.1.10"
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DistRoot = Join-Path $ProjectRoot "dist"
$UpdatesRoot = Join-Path $DistRoot "updates"

function Write-Step([string]$Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message)
}

function Write-TextFile([string]$Path, [string]$Content) {
    [IO.File]::WriteAllText($Path, $Content.Replace("`n", [Environment]::NewLine), [Text.UTF8Encoding]::new($true))
}

function Write-BatchFile([string]$Path, [string]$Content) {
    [IO.File]::WriteAllText($Path, $Content.Replace("`n", [Environment]::NewLine), [Text.ASCIIEncoding]::new())
}

function Copy-PayloadFile([string]$ReleaseRoot, [string]$PayloadRoot, [string]$RelativePath) {
    $normalizedRelativePath = $RelativePath -replace '[\\/]+', '\'
    $source = Join-Path $ReleaseRoot $normalizedRelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Patch source is missing: $source"
    }
    $destination = Join-Path $PayloadRoot $normalizedRelativePath
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

function Copy-PayloadDirectory([string]$ReleaseRoot, [string]$PayloadRoot, [string]$RelativePath) {
    $normalizedRelativePath = $RelativePath -replace '[\\/]+', '\'
    $source = Join-Path $ReleaseRoot $normalizedRelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Patch source directory is missing: $source"
    }
    $destination = Join-Path $PayloadRoot $normalizedRelativePath
    New-Item -ItemType Directory -Force -Path $destination | Out-Null

    Get-ChildItem -LiteralPath $source -Recurse -Force -File | ForEach-Object {
        $childRelative = $_.FullName.Substring($source.Length).TrimStart([char[]]@('\', '/'))
        $isExcluded = $_.Extension -eq ".pyc" -or $childRelative -match "(^|\\)(__pycache__|alias_review|evaluation|contact_sheets)(\\|$)"
        if (-not $isExcluded) {
            $target = Join-Path $destination $childRelative
            New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
            Copy-Item -LiteralPath $_.FullName -Destination $target -Force
        }
    }
}

function Write-UpgradeScripts(
    [string]$PatchRoot,
    [string]$ExpectedLauncher,
    [string]$ProductName,
    [string]$RosterRelativePath
) {
    $applyScript = @'
$ErrorActionPreference = "Stop"
$ExpectedLauncher = "__EXPECTED_LAUNCHER__"
$ProductName = "__PRODUCT_NAME__"
$RosterRelativePath = "__ROSTER_RELATIVE_PATH__"
$PatchRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PayloadRoot = Join-Path $PatchRoot "payload"
$RosterDefaultsPath = Join-Path $PatchRoot "roster_defaults\nikke_names.json"

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

$InstallRoot = Select-InstallRoot
if (-not (Test-Path -LiteralPath (Join-Path $InstallRoot $ExpectedLauncher))) {
    throw "所选目录不是 $ProductName 的安装目录：未找到 $ExpectedLauncher"
}
if (-not (Test-Path -LiteralPath $PayloadRoot)) {
    throw "升级补丁内容不完整：未找到 payload 目录。"
}

$BackupRoot = Join-Path $InstallRoot ("update_backups\\" + (Get-Date -Format "yyyyMMdd_HHmmss"))
function Backup-ExistingFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $relative = $Path.Substring($InstallRoot.Length).TrimStart([char[]]@('\', '/'))
    $backup = Join-Path $BackupRoot $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
    Copy-Item -LiteralPath $Path -Destination $backup -Force
}

# User configuration and personal output folders never belong to an update payload.
$ProtectedPaths = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($path in @("nikke_round_config.json", "nikke_character_capture_config.json")) {
    [void]$ProtectedPaths.Add($path)
}
foreach ($payloadFile in (Get-ChildItem -LiteralPath $PayloadRoot -Recurse -File)) {
    $relative = $payloadFile.FullName.Substring($PayloadRoot.Length).TrimStart([char[]]@('\', '/'))
    if ($ProtectedPaths.Contains($relative)) {
        Write-Host "保留用户配置：$relative"
        continue
    }
    $destination = Join-Path $InstallRoot $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Backup-ExistingFile $destination
    Copy-Item -LiteralPath $payloadFile.FullName -Destination $destination -Force
}

function Get-RosterValues($Roster, [string]$PropertyName) {
    if ($null -eq $Roster -or -not ($Roster.PSObject.Properties.Name -contains $PropertyName)) {
        return @()
    }
    return @($Roster.$PropertyName)
}

function Merge-RosterNames {
    if (-not $RosterRelativePath -or -not (Test-Path -LiteralPath $RosterDefaultsPath)) { return }

    $targetPath = Join-Path $InstallRoot $RosterRelativePath
    $defaultRoster = Get-Content -LiteralPath $RosterDefaultsPath -Raw -Encoding utf8 | ConvertFrom-Json
    if (-not (Test-Path -LiteralPath $targetPath)) {
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $targetPath) | Out-Null
        Copy-Item -LiteralPath $RosterDefaultsPath -Destination $targetPath -Force
        return
    }

    try {
        $userRoster = Get-Content -LiteralPath $targetPath -Raw -Encoding utf8 | ConvertFrom-Json
    } catch {
        Write-Warning "无法合并现有妮姬名单，已保留原文件：$targetPath"
        return
    }

    Backup-ExistingFile $targetPath
    $legacyNames = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
    [void]$legacyNames.Add("天城雪子")
    [void]$legacyNames.Add("新岛真")
    $listFields = @("names", "special_names", "collection_names", "protected_names", "protected_collection_names")
    foreach ($field in $listFields) {
        $seen = [System.Collections.Generic.HashSet[string]]::new([StringComparer]::Ordinal)
        $merged = [System.Collections.Generic.List[string]]::new()
        foreach ($name in @((Get-RosterValues $userRoster $field)) + @((Get-RosterValues $defaultRoster $field))) {
            $value = [string]$name
            if ([string]::IsNullOrWhiteSpace($value) -or $legacyNames.Contains($value)) { continue }
            if ($seen.Add($value)) { [void]$merged.Add($value) }
        }
        if ($userRoster.PSObject.Properties.Name -contains $field) {
            $userRoster.$field = @($merged.ToArray())
        } else {
            $userRoster | Add-Member -NotePropertyName $field -NotePropertyValue @($merged.ToArray())
        }
    }
    foreach ($mapping in @{
        "names" = "count"
        "special_names" = "special_count"
        "collection_names" = "collection_count"
        "protected_names" = "protected_count"
        "protected_collection_names" = "protected_collection_count"
    }.GetEnumerator()) {
        $value = @(Get-RosterValues $userRoster $mapping.Key).Count
        if ($userRoster.PSObject.Properties.Name -contains $mapping.Value) {
            $userRoster.($mapping.Value) = $value
        } else {
            $userRoster | Add-Member -NotePropertyName $mapping.Value -NotePropertyValue $value
        }
    }
    if ($defaultRoster.PSObject.Properties.Name -contains "updated_at") {
        if ($userRoster.PSObject.Properties.Name -contains "updated_at") {
            $userRoster.updated_at = $defaultRoster.updated_at
        } else {
            $userRoster | Add-Member -NotePropertyName "updated_at" -NotePropertyValue $defaultRoster.updated_at
        }
    }
    $json = $userRoster | ConvertTo-Json -Depth 100
    [IO.File]::WriteAllText($targetPath, ($json + [Environment]::NewLine), [Text.UTF8Encoding]::new($false))
    Write-Host "已合并标准妮姬名单并保留用户自定义条目。"
}

Merge-RosterNames
Write-Host "升级完成：$ProductName"
Write-Host "被替换的程序文件备份位置：$BackupRoot"
'@
    $applyScript = $applyScript.Replace("__EXPECTED_LAUNCHER__", $ExpectedLauncher).Replace("__PRODUCT_NAME__", $ProductName).Replace("__ROSTER_RELATIVE_PATH__", $RosterRelativePath)
    Write-TextFile (Join-Path $PatchRoot "apply_update.ps1") $applyScript

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
    Write-BatchFile (Join-Path $PatchRoot "apply_update.bat") $batch
}

function Write-PatchDocuments(
    [string]$PatchRoot,
    [string]$ProductName,
    [string]$Version,
    [string]$LogContent,
    [string]$ReleaseDate,
    [bool]$HasRosterMerge
) {
    $usageLines = @(
        "$ProductName 升级补丁使用说明",
        "适用版本：所有已发布的旧版 $ProductName（0.1.0 及以后）",
        "目标版本：$Version",
        "",
        "1. 先完全退出程序。",
        "2. 解压本升级补丁 ZIP。",
        "3. 双击 apply_update.bat。",
        "4. 若补丁不在程序安装目录中，在弹出的窗口选择实际安装目录；该目录应包含程序启动 BAT 文件。",
        "5. 出现《升级完成》后，重新启动程序即可。",
        "",
        "本补丁直接覆盖程序文件，支持从任意已发布的同产品版本升级。",
        "不会覆盖或删除：截图参数、OCR 设置、赛区选择、主题、窗口处理方式、自定义背景、截图、导出数据和运行日志。",
        "不会重装或替换 runtime_core、CPU OCR runtime、内置 Python、Paddle 依赖和离线模型。",
        "补丁会自动备份被替换的程序文件到安装目录的 update_backups 文件夹。"
    )
    if ($HasRosterMerge) {
        $usageLines += "完整版会合并标准妮姬名单：保留用户手动增加的条目，同时修正《天城雪子》为《雪子》、《新岛真》为《QUEEN（真）》并补齐新版标准名单。"
    }
    $usageLines += "不需要重新运行安装包。"
    Write-TextFile (Join-Path $PatchRoot "升级补丁使用说明.txt") ($usageLines -join "`n")
    Write-TextFile (Join-Path $PatchRoot ("更新日志_{0}.txt" -f $ReleaseDate)) $LogContent
}

function Write-Checksums([string]$PatchRoot) {
    $lines = Get-ChildItem -LiteralPath $PatchRoot -File -Recurse |
        Where-Object { $_.Name -ne "SHA256SUMS.txt" } |
        Sort-Object FullName |
        ForEach-Object {
            $relative = $_.FullName.Substring($PatchRoot.Length).TrimStart([char[]]@('\', '/'))
            "{0}  {1}" -f (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash, $relative
        }
    Write-TextFile (Join-Path $PatchRoot "SHA256SUMS.txt") ($lines -join "`n")
}

function Build-Patch(
    [string]$PatchName,
    [string]$ReleaseRoot,
    [string]$ExpectedLauncher,
    [string]$ProductName,
    [string[]]$Files,
    [string[]]$Directories,
    [string]$LogContent,
    [string]$ReleaseDate,
    [string]$RosterSource = ""
) {
    if (-not (Test-Path -LiteralPath $ReleaseRoot)) { throw "Release directory is missing: $ReleaseRoot" }
    $patchRoot = Join-Path $UpdatesRoot $PatchName
    if (Test-Path -LiteralPath $patchRoot) { Remove-Item -LiteralPath $patchRoot -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $patchRoot | Out-Null
    $payloadRoot = Join-Path $patchRoot "payload"
    New-Item -ItemType Directory -Force -Path $payloadRoot | Out-Null

    foreach ($file in $Files) { Copy-PayloadFile $ReleaseRoot $payloadRoot $file }
    foreach ($directory in $Directories) { Copy-PayloadDirectory $ReleaseRoot $payloadRoot $directory }

    $hasRosterMerge = -not [string]::IsNullOrWhiteSpace($RosterSource)
    if ($hasRosterMerge) {
        $source = Join-Path $ReleaseRoot $RosterSource
        if (-not (Test-Path -LiteralPath $source)) { throw "Roster source is missing: $source" }
        # The active roster is personal data. It must never pass through the
        # direct-copy payload; the generated updater merges it explicitly.
        $payloadRoster = Join-Path $payloadRoot $RosterSource
        if (Test-Path -LiteralPath $payloadRoster) { Remove-Item -LiteralPath $payloadRoster -Force }
        $rosterBackupRelative = Join-Path (Split-Path -Parent $RosterSource) "nikke_names.backup.json"
        $payloadRosterBackup = Join-Path $payloadRoot $rosterBackupRelative
        if (Test-Path -LiteralPath $payloadRosterBackup) { Remove-Item -LiteralPath $payloadRosterBackup -Force }
        $rosterRoot = Join-Path $patchRoot "roster_defaults"
        New-Item -ItemType Directory -Force -Path $rosterRoot | Out-Null
        Copy-Item -LiteralPath $source -Destination (Join-Path $rosterRoot "nikke_names.json") -Force
    }

    Write-UpgradeScripts $patchRoot $ExpectedLauncher $ProductName $RosterSource
    $version = (Get-Content -LiteralPath (Join-Path $ReleaseRoot "RELEASE_INFO.json") -Raw -Encoding utf8 | ConvertFrom-Json).version
    Write-PatchDocuments $patchRoot $ProductName $version $LogContent $ReleaseDate $hasRosterMerge
    Write-Checksums $patchRoot

    $zipPath = Join-Path $UpdatesRoot ("{0}.zip" -f $PatchName)
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
    Compress-Archive -LiteralPath $patchRoot -DestinationPath $zipPath -CompressionLevel Optimal
    Write-Step "Upgrade patch is ready: $zipPath"
}

function Write-ReleaseChecksums([string[]]$Paths, [string]$OutputPath) {
    $lines = foreach ($path in $Paths) {
        if (-not (Test-Path -LiteralPath $path)) { throw "Release artifact is missing: $path" }
        "{0}  {1}" -f (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash, (Split-Path -Leaf $path)
    }
    Write-TextFile $OutputPath ($lines -join "`n")
}

New-Item -ItemType Directory -Force -Path $UpdatesRoot | Out-Null
$releaseTimestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$releaseDate = Get-Date -Format "yyyy-MM-dd"

$fullLog = @(
    "NIKKE C ARENA Tool 完整版 更新日志",
    "版本：$FullVersion",
    "更新范围：2026-08-07 正式版 0.1.17 之后至本次发行。",
    "",
    "[2026-08-09 20:46] 新增《点击玩家头像到开始截取该玩家阵容页的等待时间》及轮询检测。",
    "缘由：网络波动或页面动画可能让玩家五个 ROUND 阵容页尚未加载完成。该设置覆盖单人、应援、双方赛果、小组循环赛、晋级赛和冠军争霸赛等全部玩家阵容采集步骤；默认轮询开启，连续确认就绪后截图，10 秒未确认也会继续截取当前画面，不会终止整项任务。",
    "[2026-08-09 20:46] 详细战果页轮询超时改为继续截取当前详细区域并执行后续流程。",
    "缘由：详细战果页受网络延迟影响较大，旧逻辑会因超时结束整个截图任务。",
    "[2026-08-09 20:46] 优化国际服、港澳台服详细战果页就绪识别，新增双栏五人卡片布局、蓝色标题、亮度与左右卡列边缘的联合判定。",
    "缘由：覆盖 2560×1440 等海外服页面，以及人像卡与 DISCONNECTED 卡混合显示时的检测失败；现有全屏和窗口模式缩放逻辑保持兼容。",
    "[2026-08-21 21:26] OCR 增加海外服 2560×1600 珍藏品网格专用坐标与白色 SSR 徽章复核。",
    "缘由：该图源高度来自拼接区域而非五人阵容行，通用纵向缩放会错位；新增的六边形边缘和亮度复核可减少白色 SSR 被误判为空槽。",
    "[$releaseTimestamp] 完整版与轻量版新增跨版本 GUI 单实例互斥锁，并在截图日志记录 GUI PID、启动会话 ID 与截图运行 ID。",
    "缘由：防止用户同时启动完整版和轻量版，或重复打开窗口后并行触发自动截图，便于定位异常重复任务。",
    "[$releaseTimestamp] 战斗图像识别和图像工具的四卡槽新增无背景刷新按钮，可一键还原全部卡槽到未选择状态；按钮颜色适配两种主题并修正窄面板遮挡。",
    "缘由：用户需要快速重新选择一组图像，且原始布局会遮住刷新图标。",
    "[$releaseTimestamp] 标准妮姬名单更正《天城雪子》为《雪子》、《新岛真》为《QUEEN（真）》，保留《埃癸斯》；保护名单同步更新。",
    "缘由：保证 OCR 名称校准、离线恢复和最新游戏内标准名称一致。",
    "",
    "补丁说明：本次补丁可覆盖任意已发布完整版，不覆盖用户保存的参数、主题、赛区选择、截图、导出数据、自定义背景或运行日志；已安装的 Python、CPU OCR runtime、Paddle 依赖与离线模型不会被替换。"
) -join "`n"

$liteLog = @(
    "NIKKE C ARENA 截图工具 轻量版 更新日志",
    "版本：$LiteVersion",
    "更新范围：2026-08-07 正式版 0.1.9 之后至本次发行。",
    "",
    "[2026-08-09 20:46] 新增《点击玩家头像到开始截取该玩家阵容页的等待时间》及轮询检测。",
    "缘由：网络波动或页面动画可能让玩家五个 ROUND 阵容页尚未加载完成。该设置覆盖轻量版可用的全部玩家阵容采集步骤；默认轮询开启，10 秒未确认也会继续截取当前画面。",
    "[2026-08-09 20:46] 详细战果页轮询超时改为继续截取当前详细区域并执行后续流程。",
    "缘由：避免详细页加载缓慢或识别误判时直接结束整项截图任务。",
    "[2026-08-09 20:46] 优化国际服、港澳台服详细战果页就绪识别，新增双栏五人卡片布局、蓝色标题、亮度与左右卡列边缘的联合判定。",
    "缘由：覆盖 2560×1440 等海外服页面，以及人像卡与 DISCONNECTED 卡混合显示时的检测失败；现有全屏和窗口模式缩放逻辑保持兼容。",
    "[$releaseTimestamp] 完整版与轻量版新增跨版本 GUI 单实例互斥锁，并在截图日志记录 GUI PID、启动会话 ID 与截图运行 ID。",
    "缘由：防止重复打开窗口造成并行截图，方便排查异常重复任务。",
    "[$releaseTimestamp] 图像工具和战斗图像识别演示页的四卡槽新增无背景刷新按钮，可一键还原全部卡槽到未选择状态；按钮颜色适配两种主题并修正窄面板遮挡。",
    "缘由：用户可以快速重新选择图像，且刷新按钮在旧版窄面板中可能被遮住。",
    "",
    "补丁说明：本次补丁可覆盖任意已发布轻量版，不覆盖用户保存的参数、主题、赛区选择、截图、自定义背景或运行日志；不会替换轻量版已安装的 Python 或截图运行依赖。"
) -join "`n"

$fullPatch = @{
    PatchName = "NIKKE_C_ARENA_Tool_完整版_升级补丁_$FullVersion"
    ReleaseRoot = Join-Path $DistRoot "r_$FullVersion"
    ExpectedLauncher = "run_gui.bat"
    ProductName = "NIKKE C ARENA Tool 完整版"
    Files = @(
        "run_gui.bat", "run_stitcher.bat", "run_character_capture.bat", "run_all_characters.bat",
        "nikke_gui_bootstrap.ps1", "nikke_gui_launcher.ps1", "nikke_round_stitcher.py", "nikke_image_tools.py",
        "nikke_character_capture.py", "RELEASE_INFO.json",
        "setup_gpu_runtime.bat", "setup_gpu_runtime_cn.bat", "setup_gpu_runtime_aliyun.bat", "setup_gpu_runtime.ps1",
        "GPU_OCR_RUNTIME_SETUP_GUIDE.md", "GPU_OCR_RUNTIME_SETUP_GUIDE.pdf",
        "dataanalysis\\arena_ocr_tool\\main.py", "dataanalysis\\arena_ocr_tool\\requirements-ocr.txt",
        "dataanalysis\\arena_ocr_tool\\requirements-ocr-cpu.lock.txt", "dataanalysis\\arena_ocr_tool\\requirements-ocr-gpu.txt"
    )
    Directories = @(
        "assets", "dataanalysis\\arena_ocr_tool\\recognizer", "dataanalysis\\arena_ocr_tool\\data",
        "dataanalysis\\arena_ocr_tool\\models"
    )
    LogContent = $fullLog
    ReleaseDate = $releaseDate
    RosterSource = "dataanalysis\\arena_ocr_tool\\data\\nikke_names.json"
}
Build-Patch @fullPatch

$litePatch = @{
    PatchName = "NIKKE_C_ARENA_Capture_Lite_轻量版_升级补丁_$LiteVersion"
    ReleaseRoot = Join-Path $DistRoot "lite_r_$LiteVersion"
    ExpectedLauncher = "run_capture_lite.bat"
    ProductName = "NIKKE C ARENA 截图工具 轻量版"
    Files = @(
        "run_capture_lite.bat", "nikke_capture_lite_launcher.ps1", "nikke_round_stitcher.py", "nikke_image_tools.py",
        "nikke_character_capture.py", "RELEASE_INFO.json"
    )
    Directories = @("assets")
    LogContent = $liteLog
    ReleaseDate = $releaseDate
}
Build-Patch @litePatch

$combinedLog = @(
    "NIKKE C ARENA Tool 本次发布汇总更新日志",
    "发布日期：$releaseTimestamp",
    "",
    $fullLog,
    "",
    "轻量版说明：轻量版包含本次 GUI、自动截图、图像工具和轮询检测更新；OCR 识别、妮姬名单维护、GPU 配置与数据导出仍仅由完整版提供。"
) -join "`n"
Write-TextFile (Join-Path $UpdatesRoot ("更新日志_{0}.txt" -f $releaseDate)) $combinedLog

$releaseArtifacts = @(
    (Join-Path $DistRoot ("installer\\NIKKE_Arena_Tool_Setup_{0}.exe" -f $FullVersion)),
    (Join-Path $DistRoot ("installer\\NIKKE_Arena_Capture_Lite_Setup_{0}.exe" -f $LiteVersion)),
    (Join-Path $UpdatesRoot ("NIKKE_C_ARENA_Tool_完整版_升级补丁_{0}.zip" -f $FullVersion)),
    (Join-Path $UpdatesRoot ("NIKKE_C_ARENA_Capture_Lite_轻量版_升级补丁_{0}.zip" -f $LiteVersion))
)
Write-ReleaseChecksums $releaseArtifacts (Join-Path $UpdatesRoot ("SHA256SUMS_{0}.txt" -f $releaseDate))
