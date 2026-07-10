param(
    [string]$BuildPythonExe = "",
    [switch]$ReplaceExisting
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WorkRoot = Join-Path $ProjectRoot "work\portable_runtime_build"
$EmbedVersion = "3.10.8"
$EmbedFileName = "python-3.10.8-embed-amd64.zip"
$EmbedUrl = "https://www.python.org/ftp/python/$EmbedVersion/$EmbedFileName"
$EmbedMd5 = "923be16c4cef2474b7982d16cea60ddb"
$CoreTarget = Join-Path $ProjectRoot "runtime_core"
$CpuTarget = Join-Path $ProjectRoot "runtime_cpu"
$DefaultModelSource = Join-Path $env:USERPROFILE ".paddleocr\whl"
$DefaultModelTarget = Join-Path $ProjectRoot "dataanalysis\arena_ocr_tool\models\paddle_default"
$CpuRequirements = Join-Path $ProjectRoot "dataanalysis\arena_ocr_tool\requirements-ocr.txt"
$CpuLockRequirements = Join-Path $ProjectRoot "dataanalysis\arena_ocr_tool\requirements-ocr-cpu.lock.txt"

function Write-Step([string]$Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message)
}

function Resolve-BuildPython {
    if ($BuildPythonExe) {
        $candidate = $BuildPythonExe
    } else {
        $candidate = Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"
    }
    if (-not (Test-Path -LiteralPath $candidate)) {
        throw "Python 3.10 x64 build interpreter was not found. Pass -BuildPythonExe with its full path."
    }

    $check = & $candidate -c "import platform, sys; print(sys.version_info[:2] == (3, 10)); print(platform.architecture()[0])"
    if ($LASTEXITCODE -ne 0 -or $check.Count -lt 2 -or $check[0].Trim() -ne "True" -or $check[1].Trim() -ne "64bit") {
        throw "Build interpreter must be Python 3.10 64-bit: $candidate"
    }
    return (Resolve-Path -LiteralPath $candidate).Path
}

function Get-EmbedArchive {
    $archive = Join-Path $WorkRoot $EmbedFileName
    if (-not (Test-Path -LiteralPath $archive)) {
        Write-Step "Downloading official CPython embeddable package $EmbedVersion"
        Invoke-WebRequest -Uri $EmbedUrl -OutFile $archive
    }
    $actualMd5 = (Get-FileHash -LiteralPath $archive -Algorithm MD5).Hash.ToLowerInvariant()
    if ($actualMd5 -ne $EmbedMd5) {
        throw "CPython archive checksum mismatch: expected $EmbedMd5, got $actualMd5"
    }
    return $archive
}

function Enable-EmbeddedSitePackages([string]$RuntimeDir) {
    $pthPath = Join-Path $RuntimeDir "python310._pth"
    @(
        "python310.zip"
        "."
        "Lib\site-packages"
        "import site"
    ) | Set-Content -LiteralPath $pthPath -Encoding ascii
    New-Item -ItemType Directory -Force -Path (Join-Path $RuntimeDir "Lib\site-packages") | Out-Null
}

function New-EmbeddedRuntime([string]$Archive, [string]$Destination) {
    Expand-Archive -LiteralPath $Archive -DestinationPath $Destination -Force
    Enable-EmbeddedSitePackages $Destination
}

function Install-TargetPackages(
    [string]$PythonExe,
    [string]$TargetDirectory,
    [string[]]$PackageArguments
) {
    $arguments = @(
        "-m", "pip", "install",
        "--disable-pip-version-check",
        "--no-input",
        "--only-binary=:all:",
        "--upgrade",
        "--target", $TargetDirectory
    ) + $PackageArguments
    Write-Step ("Installing packages into {0}" -f $TargetDirectory)
    & $PythonExe @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Package installation failed for $TargetDirectory"
    }
}

function Test-PortableRuntime([string]$RuntimeDir, [switch]$CpuOcr) {
    $pythonExe = Join-Path $RuntimeDir "python.exe"
    $testScript = @'
import sys
from pathlib import Path

prefix = Path(sys.prefix).resolve()
base_prefix = Path(sys.base_prefix).resolve()
if prefix != base_prefix:
    raise SystemExit(f"runtime is not self-contained: prefix={prefix}; base_prefix={base_prefix}")

from PIL import Image, ImageDraw, ImageGrab

if __import__("os").environ.get("NIKKE_TEST_CPU_OCR") == "1":
    import cv2
    import numpy
    import openpyxl
    import paddle
    import paddleocr
    print("cpu_ocr_imports_ok", paddle.__version__)
else:
    print("core_imports_ok")

print("runtime_prefix", prefix)
'@
    $testPath = Join-Path $RuntimeDir "_runtime_self_test.py"
    Set-Content -LiteralPath $testPath -Value $testScript -Encoding utf8
    $previousFlag = $env:NIKKE_TEST_CPU_OCR
    try {
        if ($CpuOcr) { $env:NIKKE_TEST_CPU_OCR = "1" } else { Remove-Item Env:NIKKE_TEST_CPU_OCR -ErrorAction SilentlyContinue }
        & $pythonExe $testPath
        if ($LASTEXITCODE -ne 0) {
            throw "Portable runtime validation failed: $RuntimeDir"
        }
    } finally {
        Remove-Item -LiteralPath $testPath -Force -ErrorAction SilentlyContinue
        if ($null -eq $previousFlag) {
            Remove-Item Env:NIKKE_TEST_CPU_OCR -ErrorAction SilentlyContinue
        } else {
            $env:NIKKE_TEST_CPU_OCR = $previousFlag
        }
    }
}

function Copy-DefaultPaddleModels([string]$Destination) {
    $modelDirectories = @(
        "det\ch\ch_PP-OCRv4_det_infer",
        "det\ml\Multilingual_PP-OCRv3_det_infer",
        "rec\ch\ch_PP-OCRv4_rec_infer",
        "cls\ch_ppocr_mobile_v2.0_cls_infer"
    )
    if (-not (Test-Path -LiteralPath $DefaultModelSource)) {
        throw "Verified PaddleOCR model cache was not found: $DefaultModelSource"
    }
    foreach ($relativePath in $modelDirectories) {
        $source = Join-Path $DefaultModelSource $relativePath
        if (-not (Test-Path -LiteralPath (Join-Path $source "inference.pdmodel")) -or
            -not (Test-Path -LiteralPath (Join-Path $source "inference.pdiparams"))) {
            throw "Required verified PaddleOCR model is incomplete: $source"
        }
        $destinationPath = Join-Path $Destination (Join-Path "whl" $relativePath)
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $destinationPath) | Out-Null
        Copy-Item -LiteralPath $source -Destination $destinationPath -Recurse -Force
    }
}

function Publish-StagedDirectory([string]$Stage, [string]$Target, [string]$Name) {
    if (Test-Path -LiteralPath $Target) {
        if (-not $ReplaceExisting) {
            throw "$Name already exists. Re-run with -ReplaceExisting after reviewing it."
        }
        $backupRoot = Join-Path $WorkRoot "backups"
        New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
        $backup = Join-Path $backupRoot ("{0}_{1}" -f $Name, (Get-Date -Format "yyyyMMdd_HHmmss"))
        Write-Step "Backing up existing $Name to $backup"
        Move-Item -LiteralPath $Target -Destination $backup
    }
    Move-Item -LiteralPath $Stage -Destination $Target
}

New-Item -ItemType Directory -Force -Path $WorkRoot | Out-Null
if (-not (Test-Path -LiteralPath $CpuRequirements) -or -not (Test-Path -LiteralPath $CpuLockRequirements)) {
    throw "CPU OCR requirements files were not found. Expected: $CpuRequirements and $CpuLockRequirements"
}

$buildPython = Resolve-BuildPython
$archive = Get-EmbedArchive
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$stageRoot = Join-Path $WorkRoot ("stage_{0}" -f $stamp)
$coreStage = Join-Path $stageRoot "runtime_core"
$cpuStage = Join-Path $stageRoot "runtime_cpu"
$modelStage = Join-Path $stageRoot "paddle_default"

try {
    Write-Step "Building portable runtime_core"
    New-EmbeddedRuntime $archive $coreStage
    Install-TargetPackages $buildPython (Join-Path $coreStage "Lib\site-packages") @("Pillow==12.3.0")
    Test-PortableRuntime $coreStage

    Write-Step "Building portable runtime_cpu"
    Copy-Item -LiteralPath $coreStage -Destination $cpuStage -Recurse -Force
    Install-TargetPackages $buildPython (Join-Path $cpuStage "Lib\site-packages") @("-r", $CpuLockRequirements)
    Test-PortableRuntime $cpuStage -CpuOcr

    Write-Step "Copying verified default PaddleOCR models"
    Copy-DefaultPaddleModels $modelStage

    Publish-StagedDirectory $coreStage $CoreTarget "runtime_core"
    Publish-StagedDirectory $cpuStage $CpuTarget "runtime_cpu"
    Publish-StagedDirectory $modelStage $DefaultModelTarget "paddle_default"
    Write-Step "Portable runtimes and offline PaddleOCR models are ready"
} finally {
    if (Test-Path -LiteralPath $stageRoot) {
        Remove-Item -LiteralPath $stageRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
