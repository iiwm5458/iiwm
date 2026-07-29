param(
    [string]$Version = "0.1.0",
    [string]$DestinationRoot = "",
    [switch]$ReplaceExisting
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$DistRoot = Join-Path $ProjectRoot "dist"
if (-not $DestinationRoot) {
    $DestinationRoot = Join-Path $DistRoot ("NIKKE_C_ARENA_Capture_Lite_{0}" -f $Version)
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
        throw "Required lightweight release file is missing: $source"
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Force
}

function Copy-RequiredDirectory([string]$RelativePath) {
    $source = Join-Path $ProjectRoot $RelativePath
    $destination = Join-Path $resolvedDestination $RelativePath
    if (-not (Test-Path -LiteralPath $source)) {
        throw "Required lightweight release directory is missing: $source"
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destination) | Out-Null
    Copy-Item -LiteralPath $source -Destination $destination -Recurse -Force
}

New-Item -ItemType Directory -Force -Path $DistRoot | Out-Null
if (Test-Path -LiteralPath $resolvedDestination) {
    if (-not $ReplaceExisting) {
        throw "Release directory already exists: $resolvedDestination. Re-run with -ReplaceExisting."
    }
    Write-Step "Removing previous generated lightweight release directory"
    Remove-Item -LiteralPath $resolvedDestination -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $resolvedDestination | Out-Null

try {
    Write-Step "Copying lightweight GUI and screenshot workers"
    foreach ($file in @(
        "run_capture_lite.bat",
        "nikke_capture_lite_launcher.ps1",
        "nikke_round_stitcher.py",
        "nikke_image_tools.py",
        "nikke_character_capture.py",
        "nikke_character_capture_config.json"
    )) {
        Copy-RequiredFile $file
    }

    Write-Step "Creating lightweight default configuration"
    $roundConfig = Get-Content -LiteralPath (Join-Path $ProjectRoot "nikke_round_config.json") -Raw -Encoding utf8 | ConvertFrom-Json
    if (-not $roundConfig.launcher_settings) {
        $roundConfig | Add-Member -NotePropertyName launcher_settings -NotePropertyValue ([pscustomobject]@{})
    }
    foreach ($propertyName in @("ocr_runtime_cache", "ocr_roster_preflight_suppressed_month", "capture_parameters_preflight_suppressed_month")) {
        if ($roundConfig.launcher_settings.PSObject.Properties.Name -contains $propertyName) {
            [void]$roundConfig.launcher_settings.PSObject.Properties.Remove($propertyName)
        }
    }
    $roundConfig.launcher_settings.ocr_performance_mode = "cpu"
    $roundConfig.launcher_settings.ocr_thermal_mode = "safe"
    $roundConfigJson = $roundConfig | ConvertTo-Json -Depth 100
    [IO.File]::WriteAllText(
        (Join-Path $resolvedDestination "nikke_round_config.json"),
        ($roundConfigJson + [Environment]::NewLine),
        [Text.UTF8Encoding]::new($false)
    )

    Write-Step "Copying screenshot runtime and visual resources"
    foreach ($directory in @(
        "assets",
        "runtime_core"
    )) {
        Copy-RequiredDirectory $directory
    }

    foreach ($directory in @(
        "screenshots",
        "custom_backgrounds",
        "support_custom_backgrounds",
        "group_custom_backgrounds"
    )) {
        New-Item -ItemType Directory -Force -Path (Join-Path $resolvedDestination $directory) | Out-Null
    }

    $info = [ordered]@{
        product = "NIKKE C ARENA 截图工具 轻量版"
        version = $Version
        built_at = (Get-Date).ToString("o")
        components = @("runtime_core", "screenshot_workers", "ocr_demo_ui")
    }
    [IO.File]::WriteAllText(
        (Join-Path $resolvedDestination "RELEASE_INFO.json"),
        (($info | ConvertTo-Json) + [Environment]::NewLine),
        [Text.UTF8Encoding]::new($false)
    )
    Write-Step "Lightweight release directory is ready: $resolvedDestination"
} catch {
    if (Test-Path -LiteralPath $resolvedDestination) {
        Remove-Item -LiteralPath $resolvedDestination -Recurse -Force -ErrorAction SilentlyContinue
    }
    throw
}
