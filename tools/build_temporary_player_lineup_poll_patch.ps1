param(
    [string]$PatchDate = (Get-Date -Format "yyyy-MM-dd")
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$UpdatesRoot = Join-Path $ProjectRoot "dist\updates"
$Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm"
$DateStamp = Get-Date -Format "yyyyMMdd"

function Write-Utf8Text([string]$Path, [string]$Content) {
    [IO.File]::WriteAllText($Path, $Content.Replace("`n", [Environment]::NewLine), [Text.UTF8Encoding]::new($true))
}

function Write-AsciiText([string]$Path, [string]$Content) {
    [IO.File]::WriteAllText($Path, $Content.Replace("`n", [Environment]::NewLine), [Text.ASCIIEncoding]::new())
}

function Add-Checksums([string]$PatchRoot) {
    $lines = Get-ChildItem -LiteralPath $PatchRoot -File -Recurse |
        Where-Object { $_.Name -ne "SHA256SUMS.txt" } |
        Sort-Object FullName |
        ForEach-Object {
            $relative = $_.FullName.Substring($PatchRoot.Length).TrimStart([char[]]@('\', '/'))
            "{0}  {1}" -f (Get-FileHash -Algorithm SHA256 -LiteralPath $_.FullName).Hash, $relative
        }
    Write-Utf8Text (Join-Path $PatchRoot "SHA256SUMS.txt") ($lines -join "`n")
}

function Write-ApplyScripts([string]$PatchRoot, [string]$ExpectedLauncher, [string]$ProductName) {
    $applyScript = @'
$ErrorActionPreference = "Stop"
$ExpectedLauncher = "__EXPECTED_LAUNCHER__"
$ProductName = "__PRODUCT_NAME__"
$PatchRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PayloadRoot = Join-Path $PatchRoot "payload"

function Get-InstallRoot {
    if (Test-Path -LiteralPath (Join-Path $PatchRoot $ExpectedLauncher)) { return $PatchRoot }
    Add-Type -AssemblyName System.Windows.Forms
    $dialog = New-Object System.Windows.Forms.FolderBrowserDialog
    $dialog.Description = "请选择 $ProductName 的安装目录（其中应包含 $ExpectedLauncher）"
    $dialog.ShowNewFolderButton = $false
    if ($dialog.ShowDialog() -ne [System.Windows.Forms.DialogResult]::OK) {
        throw "未选择安装目录，更新已取消。"
    }
    return $dialog.SelectedPath
}

$InstallRoot = Get-InstallRoot
if (-not (Test-Path -LiteralPath (Join-Path $InstallRoot $ExpectedLauncher))) {
    throw "所选目录不是 $ProductName 的安装目录：未找到 $ExpectedLauncher"
}
if (-not (Test-Path -LiteralPath $PayloadRoot)) {
    throw "补丁内容不完整：未找到 payload 文件夹。"
}

$BackupRoot = Join-Path $InstallRoot ("update_backups\\" + (Get-Date -Format "yyyyMMdd_HHmmss"))
foreach ($file in Get-ChildItem -LiteralPath $PayloadRoot -File -Recurse) {
    $relative = $file.FullName.Substring($PayloadRoot.Length).TrimStart([char[]]@('\', '/'))
    $destination = Join-Path $InstallRoot $relative
    if (Test-Path -LiteralPath $destination) {
        $backup = Join-Path $BackupRoot $relative
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $backup) | Out-Null
        Copy-Item -LiteralPath $destination -Destination $backup -Force
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $file.FullName -Destination $destination -Force
}

Write-Host "临时更新完成：$ProductName"
Write-Host "被替换文件的备份位置：$BackupRoot"
'@
    $applyScript = $applyScript.Replace("__EXPECTED_LAUNCHER__", $ExpectedLauncher).Replace("__PRODUCT_NAME__", $ProductName)
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

function Build-TemporaryPatch(
    [string]$PatchName,
    [string]$ExpectedLauncher,
    [string]$ProductName,
    [string]$LauncherSource,
    [string]$UsageText,
    [string]$UpdateText
) {
    $patchRoot = Join-Path $UpdatesRoot $PatchName
    if (Test-Path -LiteralPath $patchRoot) {
        Remove-Item -LiteralPath $patchRoot -Recurse -Force
    }
    $payloadRoot = Join-Path $patchRoot "payload"
    New-Item -ItemType Directory -Force -Path $payloadRoot | Out-Null

    Copy-Item -LiteralPath (Join-Path $ProjectRoot $LauncherSource) -Destination (Join-Path $payloadRoot $LauncherSource) -Force
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "nikke_round_stitcher.py") -Destination (Join-Path $payloadRoot "nikke_round_stitcher.py") -Force

    Write-ApplyScripts $patchRoot $ExpectedLauncher $ProductName
    Write-Utf8Text (Join-Path $patchRoot "临时更新补丁使用说明.txt") $UsageText
    Write-Utf8Text (Join-Path $patchRoot "临时更新内容.txt") $UpdateText
    Add-Checksums $patchRoot

    $zipPath = Join-Path $UpdatesRoot ("{0}.zip" -f $PatchName)
    if (Test-Path -LiteralPath $zipPath) {
        Remove-Item -LiteralPath $zipPath -Force
    }
    Compress-Archive -LiteralPath $patchRoot -DestinationPath $zipPath -CompressionLevel Optimal
    return $zipPath
}

New-Item -ItemType Directory -Force -Path $UpdatesRoot | Out-Null

$updateText = @(
    "NIKKE C ARENA 临时更新内容",
    "",
    "[$Timestamp] 玩家阵容页轮询检测默认开启。",
    "[$Timestamp] 已安装旧版的用户在首次启动后也会自动启用此选项；之后如手动关闭并保存，程序会保留该选择。",
    "[$Timestamp] 轮询最长等待 10 秒；未能识别时仍会继续截取，不会终止任务。"
) -join "`n"

$usageText = @(
    "NIKKE C ARENA 临时更新补丁使用说明",
    "",
    "适用范围：对应产品的当前版本安装目录。",
    "1. 完全退出程序。",
    "2. 解压 ZIP 文件。",
    "3. 双击 apply_update.bat。",
    "4. 若补丁不在安装目录内，选择实际安装目录。",
    "5. 出现《临时更新完成》后重新启动程序。",
    "",
    "补丁仅直接覆盖本次所需的启动器与截图核心文件，不覆盖用户的 JSON 参数设置、截图或导出数据。",
    "被替换文件会自动备份到安装目录 update_backups 文件夹。"
) -join "`n"

$fullZip = Build-TemporaryPatch `
    -PatchName ("NIKKE_C_ARENA_Tool_完整版_临时更新补丁_{0}_玩家阵容轮询默认开启" -f $DateStamp) `
    -ExpectedLauncher "run_gui.bat" `
    -ProductName "NIKKE C ARENA Tool 完整版" `
    -LauncherSource "nikke_gui_launcher.ps1" `
    -UsageText $usageText `
    -UpdateText $updateText

$liteZip = Build-TemporaryPatch `
    -PatchName ("NIKKE_C_ARENA_Capture_Lite_轻量版_临时更新补丁_{0}_玩家阵容轮询默认开启" -f $DateStamp) `
    -ExpectedLauncher "run_capture_lite.bat" `
    -ProductName "NIKKE C ARENA 截图工具 轻量版" `
    -LauncherSource "nikke_capture_lite_launcher.ps1" `
    -UsageText $usageText `
    -UpdateText $updateText

Write-Utf8Text (Join-Path $UpdatesRoot ("临时更新内容_{0}_玩家阵容轮询默认开启.txt" -f $DateStamp)) $updateText
Write-Host "完整版临时补丁：$fullZip"
Write-Host "轻量版临时补丁：$liteZip"
