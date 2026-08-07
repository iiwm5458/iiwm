param(
    [string]$FullVersion = "0.1.17",
    [string]$LiteVersion = "0.1.9"
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
    $source = Join-Path $ReleaseRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Patch source is missing: $source"
    }
    $destination = Join-Path $PayloadRoot $RelativePath
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

function Copy-PayloadDirectory([string]$ReleaseRoot, [string]$PayloadRoot, [string]$RelativePath) {
    $source = Join-Path $ReleaseRoot $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Patch source directory is missing: $source"
    }
    $destination = Join-Path $PayloadRoot $RelativePath
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    Get-ChildItem -LiteralPath $source -Force | Copy-Item -Destination $destination -Recurse -Force
    Get-ChildItem -LiteralPath $destination -Recurse -Force -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $destination -Recurse -Force -File -Filter "*.pyc" -ErrorAction SilentlyContinue |
        Remove-Item -Force
}

function Write-UpgradeScripts([string]$PatchRoot, [string]$ExpectedLauncher, [string]$ProductName) {
    $applyScript = @'
$ErrorActionPreference = "Stop"
$ExpectedLauncher = "__EXPECTED_LAUNCHER__"
$ProductName = "__PRODUCT_NAME__"
$PatchRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PayloadRoot = Join-Path $PatchRoot "payload"

function Select-InstallRoot {
    if (Test-Path -LiteralPath (Join-Path $PatchRoot $ExpectedLauncher)) { return $PatchRoot }
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "请选择 $ProductName 的安装目录（其中应包含 $ExpectedLauncher）"
    $dialog.ShowNewFolderButton = $false
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) { throw "未选择安装目录，升级已取消。" }
    return $dialog.SelectedPath
}

$InstallRoot = Select-InstallRoot
if (-not (Test-Path -LiteralPath (Join-Path $InstallRoot $ExpectedLauncher))) {
    throw "所选目录不是 $ProductName 的安装目录：未找到 $ExpectedLauncher"
}
if (-not (Test-Path -LiteralPath $PayloadRoot)) { throw "升级补丁内容不完整：未找到 payload 目录。" }

$BackupRoot = Join-Path $InstallRoot ("update_backups\" + (Get-Date -Format "yyyyMMdd_HHmmss"))
function Backup-ExistingFile([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    $relative = $Path.Substring($InstallRoot.Length).TrimStart([char[]]@('\', '/'))
    $backup = Join-Path $BackupRoot $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
    Copy-Item -LiteralPath $Path -Destination $backup -Force
}
foreach ($payloadFile in (Get-ChildItem -LiteralPath $PayloadRoot -Recurse -File)) {
    $relative = $payloadFile.FullName.Substring($PayloadRoot.Length).TrimStart([char[]]@('\', '/'))
    $destination = Join-Path $InstallRoot $relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Backup-ExistingFile $destination
    Copy-Item -LiteralPath $payloadFile.FullName -Destination $destination -Force
}

Write-Host "升级完成：$ProductName"
Write-Host "原文件备份位置：$BackupRoot"
'@
    $applyScript = $applyScript.Replace("__EXPECTED_LAUNCHER__", $ExpectedLauncher).Replace("__PRODUCT_NAME__", $ProductName)
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

function Write-PatchDocuments([string]$PatchRoot, [string]$ProductName, [string]$Version, [string]$LogContent, [string]$ConfigResetNotice) {
    $usage = @(
        "$ProductName 升级补丁使用说明",
        "适用版本：所有已发布的旧版 $ProductName（0.1.0 及以后）",
        "目标版本：$Version",
        "",
        "1. 先完全退出程序。",
        "2. 解压本升级补丁 ZIP。",
        "3. 双击 apply_update.bat。",
        "4. 若补丁不在程序安装目录中，弹出的窗口中选择实际安装目录；该目录应包含程序启动 BAT 文件。",
        "5. 出现《升级完成》后，重新启动程序即可。",
        "",
        "补丁会自动备份被替换的程序文件到安装目录的 update_backups 文件夹。",
        "本补丁采用直接覆盖方式，支持从任意已发布的同产品版本升级；不会解析或合并 JSON 配置。",
        "截图、导出数据、用户主题和自定义背景不会被删除。",
        $ConfigResetNotice,
        "不需要重新运行安装包。"
    ) -join "`n"
    Write-TextFile (Join-Path $PatchRoot "升级补丁使用说明.txt") $usage
    Write-TextFile (Join-Path $PatchRoot ("更新日志_{0}.txt" -f $releaseDate)) $LogContent
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
    [string]$ConfigResetNotice
) {
    if (-not (Test-Path -LiteralPath $ReleaseRoot)) { throw "Release directory is missing: $ReleaseRoot" }
    $patchRoot = Join-Path $UpdatesRoot $PatchName
    if (Test-Path -LiteralPath $patchRoot) { Remove-Item -LiteralPath $patchRoot -Recurse -Force }
    New-Item -ItemType Directory -Force -Path $patchRoot | Out-Null
    $payloadRoot = Join-Path $patchRoot "payload"
    New-Item -ItemType Directory -Force -Path $payloadRoot | Out-Null

    foreach ($file in $Files) { Copy-PayloadFile $ReleaseRoot $payloadRoot $file }
    foreach ($directory in $Directories) { Copy-PayloadDirectory $ReleaseRoot $payloadRoot $directory }

    Write-UpgradeScripts $patchRoot $ExpectedLauncher $ProductName
    $version = (Get-Content -LiteralPath (Join-Path $ReleaseRoot "RELEASE_INFO.json") -Raw -Encoding utf8 | ConvertFrom-Json).version
    Write-PatchDocuments $patchRoot $ProductName $version $LogContent $ConfigResetNotice
    Write-Checksums $patchRoot

    $zipPath = Join-Path $UpdatesRoot ("{0}.zip" -f $PatchName)
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
    Compress-Archive -LiteralPath $patchRoot -DestinationPath $zipPath -CompressionLevel Optimal
    Write-Step "Upgrade patch is ready: $zipPath"
}

function Write-ReleaseChecksums([string[]]$Paths, [string]$OutputPath) {
    $lines = foreach ($path in $Paths) {
        if (-not (Test-Path -LiteralPath $path)) {
            throw "Release artifact is missing: $path"
        }
        "{0}  {1}" -f (Get-FileHash -Algorithm SHA256 -LiteralPath $path).Hash, (Split-Path -Leaf $path)
    }
    Write-TextFile $OutputPath ($lines -join "`n")
}

New-Item -ItemType Directory -Force -Path $UpdatesRoot | Out-Null
$releaseTimestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$releaseDate = Get-Date -Format "yyyy-MM-dd"

$fullLog = @(
    "NIKKE C ARENA Tool 完整版 更新日志",
    "版本：0.1.17",
    "更新基线：0.1.0（本补丁可直接覆盖升级；包含至 0.1.17 的全部累计改动）",
    "时间说明：每条记录均标记对应功能最终修订时间，精确到分钟。",
    "",
    "[2026-07-15 01:47] GPU 环境一键配置新增阿里云镜像脚本；完整版本补丁包含该脚本。",
    "[2026-07-15 01:49] GPU 配置说明同步更新为最新 PDF 与 Markdown 文档。",
    "[2026-07-15 04:42] 新增图像工具：支持 PNG 截图压缩为 JPEG，以及多张图像的横向或纵向拼接。",
    "[2026-07-15 14:09] GUI 主窗口任务栏图标改为与桌面快捷方式一致的程序图标。",
    "[2026-07-15 13:03] OCR 新增 2560×1600 图源适配和详细战果强制判定，提升不同截图来源的识别兼容性。",
    "[2026-07-15 13:03] OCR 循环等级支持 1 至 999；增加合并文本框复核、数值行二次确认与尾部字形校验，修复部分 99 级被误读为 66 级的问题。",
    "[2026-07-15 13:03] OCR 调整收藏品空槽与正样本判定，减少收藏品与阵容数据的误判。",
    "[2026-07-15 07:59] 妮姬名单及离线兜底名单增补《灰姑娘：琉璃波光》《玛律恰那：海洋进修》。",
    "[2026-07-15 14:05] 新增国服、国际服、港澳台服进程识别，并在主面板显示对应服务器状态。",
    "[2026-07-15 14:05] 国际服与港澳台服的自动化截图改为侧边空白点击关闭弹窗，并使用左下角《返回》按钮完成晋级赛到冠军争霸赛转场。",
    "[2026-07-15 14:05] 国际服与港澳台服详细战果页新增独立裁切规格和就绪检测兼容，避免蓝色标题边缘及网络断连画面导致流程停滞。",
    "[2026-07-15 14:05] 所有勾选《赛后数据（详）》的自动化截图流程改为轮询确认详细战果页完整加载后再截取；超时会提示检查网络环境，避免误点黑色战果按钮。",
    "[2026-07-15 14:05] 国际服与港澳台服的循环等级拼图裁切补齐辅助型等级右侧边缘，国服原有裁切逻辑保持不变。",
    "[2026-07-15 14:05] 所有服务器的截图文件名追加《国服》《国际服》或《港澳台》后缀，便于区分图像来源。",
    "[2026-07-15 14:09] 参数页新增《点击用户头像后截取基本信息页等待时间》和《点击出线图战果标签后等待战果页加载时间》；后者独立于普通点击等待，范围均为 0.45 至 5 秒，战果标签等待默认 1 秒。",
    "[2026-07-15 14:14] 完整版与轻量版的设置页收紧标题、间距和控件高度，并加入垂直滚动保护，避免小窗口高度下显示不全。",
    "[2026-07-15 17:08] 升级补丁改为备份后直接覆盖全部更新文件与标准配置，修复旧合并方式可能把国际服、港澳台服二维坐标写坏的问题。",
    "[2026-07-18 04:48] OCR 增加国服/海外服图源配置；海外服使用独立玩家资料卡、昵称、收藏品和详细战果坐标，不改变国服原有解析路径。",
    "[2026-07-18 04:48] OCR 新增海外服 DISCONNECTED 失败标识模板检测，补足国际服、港澳台服详细战果页无法沿用国服失败标记的问题。",
    "[2026-07-19 09:18] OCR 统一细化同存活人数的胜负规则：海外服读取全部幸存妮姬的 HP 百分比总和，任一存活卡 HP 漏读时保持未知；国服因不显示单卡 HP，按游戏守方优势规则判定，避免误用海外服策略。",
    "[2026-07-19 09:18] OCR 新增繁体中文昵称识别模型与多语言候选交叉筛选，改善港澳台服玩家昵称、ID、阵容和赛果对应关系的稳定性。",
    "[2026-07-19 09:43] OCR 命令行与 GUI 增加海外服图源选择、详细战果强制判定传递，并把新增模板/模型纳入离线发行内容。",
    "[2026-07-20 14:42] 图像工具扩展为高清压缩、深度压缩、极限压缩三档 JPEG 输出；保留横向/纵向拼接与间距控制。",
    "[2026-07-20 14:42] 图像工具新增赛果标记：可按 Excel/JSON 数据在全部 GROUP 阵容图和冠军争霸赛图上标注 WIN/LOSE、GROUP 分组框，并可为失败阵容添加浅灰蒙版。",
    "[2026-07-20 16:46] 自动截图新增基础信息页轮询检测；启用后最长等待 10 秒，超时仍会截取当前画面，避免检测误判导致整段任务中断。",
    "[2026-07-20 16:46] 自动截图新增窗口客户区捕获与实时坐标换算；窗口移动后仍能正确点击和裁图。窗口模式仅支持单人阵容、应援双方阵容与冠亚军截图，其他流程会提示切换全屏。",
    "[2026-07-20 16:56] 完整版与轻量版主界面增加赛区选择下拉菜单：自动、国服、港澳台、国际服；手动选择会同时切换截图逻辑与状态显示。",
    "[2026-07-20 16:56] 全屏/窗口模式提示会随当前游戏窗口状态更新；4:3、16:9、21:9 窗口比例沿用客户区比例坐标，国际服与港澳台服共享窗口适配逻辑。",
    "[2026-07-20 16:56] 完整版启动时会缓存 CPU/GPU OCR 运行环境的指纹；首次检测后直接复用有效缓存，环境变动或手动点击《重新检测 OCR 环境》时才重新完整扫描，缩短后续打开程序的等待时间。",
    "[2026-07-20 19:04] 发行默认参数更新：基础信息页等待、轮询开关、出线图战果标签等待、赛区选择与窗口模式相关坐标均写入标准配置。",
    "[2026-07-25 12:08] 图像工具新增《单张详细战果自动标记》：选择一张带详细战果页的双人对局图后，可直接读取中间赛果并为双方阵容标注 WIN/LOSE；可选浅灰蒙版标记失败阵容，不需要 JSON 或 Excel。",
    "[2026-07-25 12:18] 战斗图像识别与图像工具的四个卡槽支持一次多选填入剩余空槽，最多四张；继续限制 PNG/JPG 格式并阻止同名文件重复选择。",
    "[2026-07-25 12:18] 图像工具拼接取消最大图像尺寸限制，保留原始图像尺寸与用户选择的横向、纵向和间距设置。",
    "[2026-07-25 12:30] 识别前新增妮姬名单检查：显示名单更新时间，可前往更新名单或继续识别，并支持本月不再提醒。",
    "[2026-07-25 12:30] 妮姬名单增补《麦斯威尔：平凡技师》《拉普拉斯：究极英雄》，并登记舒格、潘托姆、芙罗拉、罗珊娜的珍藏品状态。",
    "[2026-07-25 12:40] 所有自动化截图任务新增截图参数检查：可前往参数设置或继续截图，并支持本月不再提醒；修复检查弹窗按钮错误显示颜色值的问题。",
    "[2026-07-27 11:40] 完整版与轻量版窗口新增外层《帮助》入口和主题化说明弹窗，集中说明功能、运行方式、开发初心、风险提示与禁止用途。",
    "[2026-07-27 11:55] 帮助入口调整为更紧凑的纯《帮助》文字按钮，移除问号并保持两种主题颜色适配。",
    "[$releaseTimestamp] 图像工具的战果标记新增小、中、大三档固定尺寸 WIN/LOSE 像素标记；中号、大号加粗放大，且不依赖玩家立绘覆盖区域的动态计算。",
    "[$releaseTimestamp] 妮姬名单统一修正《士兵F.A.》《士兵O.W.》《士兵E.G.》的末尾句点，并同步更新保护名单；OCR 漏读句点时仍会归一到标准名称。",
    "[$releaseTimestamp] 赛季一键截图从晋级赛转入冠军争霸赛时，返回赛区选择页后固定等待 3 秒，点击冠军争霸赛入口后固定等待 5 秒；两项不受参数设置控件影响。",
    "[$releaseTimestamp] 完整版与轻量版帮助页底部新增 GitHub Releases 超链接，点击可打开发布下载页，并适配两种主题。",
    "[$releaseTimestamp] 修复完整版首次自检时可选 GPU runtime 探测可能遗留非零退出码的问题，确保发行验证与不含 GPU runtime 的标准安装包正常构建。",
    "[$releaseTimestamp] OCR 按导入文件名识别 1920×1080、1920×1200、1920×1440、2560×1080、2560×1440、2560×1600、3440×1440、3840×2160 图源规格。",
    "[$releaseTimestamp] OCR 为海外服 2560×1440 珍藏品增加独立模板配置、坐标相位校准与 R15 保留判定，减少不同分辨率下珍藏品等级误判。",
    "[$releaseTimestamp] 图像工具补齐透明、纯白、粉色、蓝色、黑色、奶白与自定义背景拼接；自定义背景会裁切铺满画布，并以半透明方式叠放顶层图像。",
    "[$releaseTimestamp] 图像压缩同时支持 PNG 与 JPG 输入，并保留原图宽高比例；拼接解除单图最大尺寸限制后，超大循环赛输出会自动拆分为每张 8 个 GROUP。",
    "[$releaseTimestamp] 新增《小组循环赛》自动截图：可采集当前 GROUP 的 4 名玩家资料页，按横向排列并支持间距、背景和窗口模式坐标换算。",
    "[$releaseTimestamp] 小组循环赛新增《战斗结果（赛后用）》：在四人资料页前截取结果区域，并在最终拼图最左侧垂直居中放置该结果图。",
    "[$releaseTimestamp] 小组循环赛新增全部 GROUP 批量采集：支持设置起始 GROUP、切换等待时间、每组单独深度压缩输出和日期目录下的专用文件夹。",
    "[$releaseTimestamp] 小组循环赛文件夹拼接支持纵向或横向分批输出、背景颜色、GROUP 像素标记与加粗外框；修复黑色背景与 GROUP49/50 标记截断问题。",
    "[$releaseTimestamp] 新增《双方赛果截图》：从已打开的两人赛果窗口依次采集双方资料，可选简化或默认详细赛果，并复用国服及海外服的战果裁切、轮询与关闭页面规则。",
    "[$releaseTimestamp] 《双方赛果截图》支持窗口模式；主面板将《小组循环赛》调整到《C ARENA 晋级赛》正上方。",
    "[$releaseTimestamp] 妮姬名单与离线保护名单新增《天城雪子》《新岛真》《埃癸斯》，供本地 OCR 名称校准与恢复使用。",
    "[$releaseTimestamp] 重建完整版直接覆盖升级补丁；补丁包含完整内置 assets、基础 Python 运行时、最新 GUI、图像工具、妮姬名单、标准配置和 GPU 配置文档，不包含 GPU/CUDA 运行时。"
) -join "`n"

$liteLog = @(
    "NIKKE C ARENA 截图工具 轻量版 更新日志",
    "版本：0.1.9",
    "更新基线：0.1.0（本补丁可直接覆盖升级；包含至 0.1.9 的全部累计改动）",
    "时间说明：每条记录均标记对应功能最终修订时间，精确到分钟。",
    "",
    "[2026-07-15 04:42] 新增图像工具：支持 PNG 截图压缩为 JPEG，以及多张图像的横向或纵向拼接。",
    "[2026-07-15 14:14] GUI 主窗口任务栏图标改为与桌面快捷方式一致的程序图标。",
    "[2026-07-15 14:05] 新增国服、国际服、港澳台服进程识别，并在主面板显示对应服务器状态。",
    "[2026-07-15 14:05] 国际服与港澳台服的自动化截图改为侧边空白点击关闭弹窗，并使用左下角《返回》按钮完成晋级赛到冠军争霸赛转场。",
    "[2026-07-15 14:05] 国际服与港澳台服详细战果页新增独立裁切规格和就绪检测兼容，避免蓝色标题边缘及网络断连画面导致流程停滞。",
    "[2026-07-15 14:05] 所有勾选《赛后数据（详）》的自动化截图流程改为轮询确认详细战果页完整加载后再截取；超时会提示检查网络环境，避免误点黑色战果按钮。",
    "[2026-07-15 14:05] 国际服与港澳台服的循环等级拼图裁切补齐辅助型等级右侧边缘，国服原有裁切逻辑保持不变。",
    "[2026-07-15 14:05] 所有服务器的截图文件名追加《国服》《国际服》或《港澳台》后缀，便于区分图像来源。",
    "[2026-07-15 14:14] 参数页新增《点击用户头像后截取基本信息页等待时间》和《点击出线图战果标签后等待战果页加载时间》；后者独立于普通点击等待，范围均为 0.45 至 5 秒，战果标签等待默认 1 秒。",
    "[2026-07-15 14:14] 设置页收紧标题、间距和控件高度，并加入垂直滚动保护，避免小窗口高度下显示不全。",
    "[2026-07-15 17:08] 升级补丁改为备份后直接覆盖全部更新文件与标准配置，修复旧合并方式可能把国际服、港澳台服二维坐标写坏的问题。",
    "[2026-07-20 14:42] 图像工具扩展为高清压缩、深度压缩、极限压缩三档 JPEG 输出；保留横向/纵向拼接与间距控制。",
    "[2026-07-20 16:46] 自动截图新增基础信息页轮询检测；启用后最长等待 10 秒，超时仍会截取当前画面，避免检测误判导致整段任务中断。",
    "[2026-07-20 16:46] 自动截图新增窗口客户区捕获与实时坐标换算；窗口移动后仍能正确点击和裁图。窗口模式仅支持单人阵容、应援双方阵容与冠亚军截图，其他流程会提示切换全屏。",
    "[2026-07-20 16:56] 轻量版主界面增加赛区选择下拉菜单：自动、国服、港澳台、国际服；手动选择会同时切换截图逻辑与状态显示。",
    "[2026-07-20 16:56] 全屏/窗口模式提示会随当前游戏窗口状态更新；4:3、16:9、21:9 窗口比例沿用客户区比例坐标，国际服与港澳台服共享窗口适配逻辑。",
    "[2026-07-20 16:56] 轻量版主界面新增简体中文、日语、英语、韩语的界面语言切换按钮；主要页面、设置、提示与任务状态会随当前语言即时切换。",
    "[2026-07-20 19:04] 发行默认参数更新：基础信息页等待、轮询开关、出线图战果标签等待、赛区选择与窗口模式相关坐标均写入标准配置。",
    "[2026-07-25 12:08] 图像工具新增《单张详细战果自动标记》：选择一张带详细战果页的双人对局图后，可直接读取中间赛果并为双方阵容标注 WIN/LOSE；可选浅灰蒙版标记失败阵容，不需要 JSON 或 Excel。",
    "[2026-07-25 12:18] 战斗图像识别演示页与图像工具的四个卡槽支持一次多选填入剩余空槽，最多四张；继续限制 PNG/JPG 格式并阻止同名文件重复选择。",
    "[2026-07-25 12:18] 图像工具拼接取消最大图像尺寸限制，保留原始图像尺寸与用户选择的横向、纵向和间距设置。",
    "[2026-07-25 12:40] 所有自动化截图任务新增截图参数检查：可前往参数设置或继续截图，并支持本月不再提醒；修复检查弹窗按钮错误显示颜色值的问题。",
    "[2026-07-27 11:40] 完整版与轻量版窗口新增外层《帮助》入口和主题化说明弹窗，集中说明功能、运行方式、开发初心、风险提示与禁止用途。",
    "[2026-07-27 11:55] 帮助入口调整为更紧凑的纯《帮助》文字按钮，移除问号并保持两种主题颜色适配。",
    "[$releaseTimestamp] 图像工具的战果标记新增小、中、大三档固定尺寸 WIN/LOSE 像素标记；中号、大号加粗放大，且不依赖玩家立绘覆盖区域的动态计算。",
    "[$releaseTimestamp] 帮助页底部新增 GitHub Releases 超链接，点击可打开发布下载页，并适配两种主题。",
    "[$releaseTimestamp] 图像工具补齐透明、纯白、粉色、蓝色、黑色、奶白与自定义背景拼接；自定义背景会裁切铺满画布，并以半透明方式叠放顶层图像。",
    "[$releaseTimestamp] 图像压缩同时支持 PNG 与 JPG 输入，并保留原图宽高比例；拼接解除单图最大尺寸限制后，超大循环赛输出会自动拆分为每张 8 个 GROUP。",
    "[$releaseTimestamp] 新增《小组循环赛》自动截图：可采集当前 GROUP 的 4 名玩家资料页，按横向排列并支持间距、背景和窗口模式坐标换算。",
    "[$releaseTimestamp] 小组循环赛新增《战斗结果（赛后用）》、全部 GROUP 批量采集、起始 GROUP、切换等待时间、深度压缩输出及文件夹拼接功能。",
    "[$releaseTimestamp] 小组循环赛拼接支持纵向或横向分批输出、背景颜色、GROUP 像素标记与加粗外框；修复黑色背景与 GROUP49/50 标记截断问题。",
    "[$releaseTimestamp] 新增《双方赛果截图》：从已打开的两人赛果窗口依次采集双方资料，可选简化或默认详细赛果，并复用国服及海外服的战果裁切、轮询与关闭页面规则。",
    "[$releaseTimestamp] 《双方赛果截图》支持窗口模式；主面板将《小组循环赛》调整到《C ARENA 晋级赛》正上方。",
    "[$releaseTimestamp] 妮姬名单与离线保护名单新增《天城雪子》《新岛真》《埃癸斯》，供完整版 OCR 名称校准与恢复使用。",
    "[$releaseTimestamp] 重建轻量版直接覆盖升级补丁；补齐完整内置 assets，不包含 PaddleCPU、PaddleGPU、OCR 模型、OCR 导出、GPU 配置文档或 GPU/CUDA 运行时。"
) -join "`n"

$fullPatch = @{
    PatchName = "NIKKE_C_ARENA_Tool_完整版_升级补丁_0.1.17"
    ReleaseRoot = Join-Path $DistRoot "r_$FullVersion"
    ExpectedLauncher = "run_gui.bat"
    ProductName = "NIKKE C ARENA Tool 完整版"
    Files = @(
        "run_gui.bat", "run_stitcher.bat", "run_character_capture.bat", "run_all_characters.bat",
        "nikke_gui_bootstrap.ps1", "nikke_gui_launcher.ps1", "nikke_round_stitcher.py", "nikke_image_tools.py",
        "nikke_character_capture.py", "nikke_character_capture_config.json", "RELEASE_INFO.json",
        "setup_gpu_runtime.bat", "setup_gpu_runtime_cn.bat", "setup_gpu_runtime_aliyun.bat", "setup_gpu_runtime.ps1",
        "GPU_OCR_RUNTIME_SETUP_GUIDE.md", "GPU_OCR_RUNTIME_SETUP_GUIDE.pdf", "nikke_round_config.json",
        "dataanalysis\\arena_ocr_tool\\main.py", "dataanalysis\\arena_ocr_tool\\data\\nikke_names.json",
        "dataanalysis\\arena_ocr_tool\\data\\nikke_names.backup.json", "dataanalysis\\arena_ocr_tool\\models\\nickname\\README.md"
    )
    Directories = @(
        "assets",
        "runtime_python310_base",
        "dataanalysis\\arena_ocr_tool\\recognizer",
        "dataanalysis\\arena_ocr_tool\\data\\defeat_templates",
        "dataanalysis\\arena_ocr_tool\\data\\collection_cv_templates",
        "dataanalysis\\arena_ocr_tool\\models\\nickname\\chinese_cht"
    )
    LogContent = $fullLog
    ConfigResetNotice = "nikke_round_config.json、nikke_character_capture_config.json 与妮姬名单会恢复为新版标准内容；截图与识别参数和手工维护的名单会重置，旧文件可在 update_backups 文件夹中找回。"
}
Build-Patch @fullPatch

$litePatch = @{
    PatchName = "NIKKE_C_ARENA_Capture_Lite_轻量版_升级补丁_0.1.9"
    ReleaseRoot = Join-Path $DistRoot "lite_r_$LiteVersion"
    ExpectedLauncher = "run_capture_lite.bat"
    ProductName = "NIKKE C ARENA 截图工具 轻量版"
    Files = @(
        "run_capture_lite.bat", "nikke_capture_lite_launcher.ps1", "nikke_round_stitcher.py", "nikke_image_tools.py",
        "nikke_character_capture.py", "nikke_character_capture_config.json", "nikke_round_config.json", "RELEASE_INFO.json"
    )
    Directories = @(
        "assets"
    )
    LogContent = $liteLog
    ConfigResetNotice = "nikke_round_config.json 与 nikke_character_capture_config.json 会恢复为新版标准内容；截图参数会重置，旧文件可在 update_backups 文件夹中找回。"
}
Build-Patch @litePatch

$combinedLog = @(
    "NIKKE C ARENA Tool 本次发布汇总更新日志",
    "发布日期：$releaseTimestamp",
    "",
    $fullLog,
    "",
    "轻量版说明：轻量版包含以上所有自动化截图、拼图、服务器适配与参数页更新；GPU 配置脚本、OCR 识别和数据导出仍仅由完整版提供。"
) -join "`n"
Write-TextFile (Join-Path $UpdatesRoot ("更新日志_{0}.txt" -f $releaseDate)) $combinedLog

$releaseArtifacts = @(
    (Join-Path $DistRoot ("installer\\NIKKE_Arena_Tool_Setup_{0}.exe" -f $FullVersion)),
    (Join-Path $DistRoot ("installer\\NIKKE_Arena_Capture_Lite_Setup_{0}.exe" -f $LiteVersion)),
    (Join-Path $UpdatesRoot ("NIKKE_C_ARENA_Tool_完整版_升级补丁_{0}.zip" -f $FullVersion)),
    (Join-Path $UpdatesRoot ("NIKKE_C_ARENA_Capture_Lite_轻量版_升级补丁_{0}.zip" -f $LiteVersion))
)
Write-ReleaseChecksums $releaseArtifacts (Join-Path $UpdatesRoot ("SHA256SUMS_{0}.txt" -f $releaseDate))
