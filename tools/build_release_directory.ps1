param(
    [string]$Version = "0.1.0",
    [string]$DestinationRoot = "",
    [switch]$ReplaceExisting
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DistRoot = Join-Path $ProjectRoot "dist"
if (-not $DestinationRoot) {
    $DestinationRoot = Join-Path $DistRoot ("NIKKE_Arena_Tool_{0}" -f $Version)
}

$resolvedDistRoot = ([IO.Path]::GetFullPath($DistRoot)).TrimEnd([char[]]@('\', '/')) + '\'
$resolvedDestination = [IO.Path]::GetFullPath($DestinationRoot)
if (-not $resolvedDestination.StartsWith($resolvedDistRoot, [StringComparison]::OrdinalIgnoreCase)) {
    throw "Release destination must stay under dist: $resolvedDestination"
}

function Write-Step([string]$Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message)
}

function Copy-RequiredFile([string]$RelativePath) {
    $source = Join-Path $ProjectRoot $RelativePath
    $destination = Join-Path $resolvedDestination $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Required release file is missing: $source"
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

function Copy-RequiredDirectory([string]$RelativePath) {
    $source = Join-Path $ProjectRoot $RelativePath
    $destination = Join-Path $resolvedDestination $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Required release directory is missing: $source"
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
}

function Remove-ReleaseDevelopmentFiles {
    $toolRoot = Join-Path $resolvedDestination "dataanalysis\arena_ocr_tool"
    $removeDirectories = @(
        (Join-Path $toolRoot "backups"),
        (Join-Path $toolRoot "tmp"),
        (Join-Path $toolRoot "tools"),
        (Join-Path $toolRoot "__pycache__"),
        (Join-Path $toolRoot "data\alias_review")
    )
    foreach ($path in $removeDirectories) {
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Recurse -Force
        }
    }
    Get-ChildItem -LiteralPath (Join-Path $toolRoot "data") -Directory -Recurse -Force -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -in @("evaluation", "contact_sheets") } |
        Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $toolRoot -Recurse -Force -File -Filter "*.pyc" -ErrorAction SilentlyContinue |
        Remove-Item -Force
    Get-ChildItem -LiteralPath $resolvedDestination -Recurse -Force -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $resolvedDestination -Recurse -Force -File -Filter "*.pyc" -ErrorAction SilentlyContinue |
        Remove-Item -Force
}

New-Item -ItemType Directory -Force -Path $DistRoot | Out-Null
if (Test-Path -LiteralPath $resolvedDestination) {
    if (-not $ReplaceExisting) {
        throw "Release directory already exists: $resolvedDestination. Re-run with -ReplaceExisting."
    }
    Write-Step "Removing previous generated release directory"
    Remove-Item -LiteralPath $resolvedDestination -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $resolvedDestination | Out-Null

try {
    Write-Step "Copying application entry points and capture workers"
    foreach ($file in @(
        "run_gui.bat",
        "run_stitcher.bat",
        "run_character_capture.bat",
        "run_all_characters.bat",
        "nikke_gui_bootstrap.ps1",
        "nikke_gui_launcher.ps1",
        "nikke_round_stitcher.py",
        "nikke_image_tools.py",
        "nikke_character_capture.py",
        "nikke_character_capture_config.json",
        "setup_gpu_runtime.bat",
        "setup_gpu_runtime_cn.bat",
        "setup_gpu_runtime_aliyun.bat",
        "setup_gpu_runtime.ps1",
        "GPU_OCR_RUNTIME_SETUP_GUIDE.md",
        "GPU_OCR_RUNTIME_SETUP_GUIDE.pdf"
    )) {
        Copy-RequiredFile $file
    }

    Write-Step "Creating release-safe default configuration"
    $roundConfig = Get-Content -LiteralPath (Join-Path $ProjectRoot "nikke_round_config.json") -Raw -Encoding utf8 | ConvertFrom-Json
    if (-not $roundConfig.launcher_settings) {
        $roundConfig | Add-Member -NotePropertyName launcher_settings -NotePropertyValue ([pscustomobject]@{})
    }
    $roundConfig.launcher_settings.ocr_performance_mode = "cpu"
    $roundConfig.launcher_settings.ocr_thermal_mode = "safe"
    $roundConfigJson = $roundConfig | ConvertTo-Json -Depth 100
    [IO.File]::WriteAllText(
        (Join-Path $resolvedDestination "nikke_round_config.json"),
        ($roundConfigJson + [Environment]::NewLine),
        [Text.UTF8Encoding]::new($false)
    )

    Write-Step "Copying GUI, OCR, and model resources"
    foreach ($directory in @(
        "assets",
        "vendor",
        "dataanalysis\arena_ocr_tool\recognizer",
        "dataanalysis\arena_ocr_tool\data",
        "dataanalysis\arena_ocr_tool\models",
        "runtime_core",
        "runtime_cpu",
        "runtime_python310_base"
    )) {
        Copy-RequiredDirectory $directory
    }
    foreach ($file in @(
        "dataanalysis\arena_ocr_tool\main.py",
        "dataanalysis\arena_ocr_tool\requirements-ocr.txt",
        "dataanalysis\arena_ocr_tool\requirements-ocr-cpu.lock.txt",
        "dataanalysis\arena_ocr_tool\requirements-ocr-gpu.txt"
    )) {
        Copy-RequiredFile $file
    }
    Remove-ReleaseDevelopmentFiles

    foreach ($directory in @("screenshots", "custom_backgrounds", "support_custom_backgrounds", "group_custom_backgrounds")) {
        New-Item -ItemType Directory -Force -Path (Join-Path $resolvedDestination $directory) | Out-Null
    }

    $info = [ordered]@{
        product = "NIKKE C ARENA Tool"
        version = $Version
        built_at = (Get-Date).ToString("o")
        components = @("runtime_core", "runtime_cpu", "runtime_python310_base", "offline_paddle_models", "gpu_setup_scripts")
    }
    $info | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $resolvedDestination "RELEASE_INFO.json") -Encoding utf8
    Write-Step "Release directory is ready: $resolvedDestination"
} catch {
    if (Test-Path -LiteralPath $resolvedDestination) {
        Remove-Item -LiteralPath $resolvedDestination -Recurse -Force -ErrorAction SilentlyContinue
    }
    throw
}
