param(
    [string]$PipIndexUrl = "https://pypi.org/simple"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$RuntimeDir = Join-Path $ScriptDir "runtime_gpu"
$GpuPython = Join-Path $RuntimeDir "Scripts\python.exe"
$BaseRuntimeDir = Join-Path $ScriptDir "runtime_python310_base"
$BasePython = Join-Path $BaseRuntimeDir "python.exe"
$Requirements = Join-Path $ScriptDir "dataanalysis\arena_ocr_tool\requirements-ocr-gpu.txt"
$Wheelhouse = Join-Path $ScriptDir "wheelhouse_gpu"
$LogPath = Join-Path $ScriptDir ("gpu_runtime_setup_{0}.log" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

function Write-Log {
    param([string]$Message)
    $line = "[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message
    Write-Host $line
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
}

function Invoke-Logged {
    param(
        [Parameter(Mandatory=$true)][string]$FilePath,
        [string[]]$Arguments = @()
    )
    Write-Log ("> {0} {1}" -f $FilePath, ($Arguments -join " "))
    $oldErrorActionPreference = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    try {
        & $FilePath @Arguments 2>&1 | ForEach-Object {
            $text = $_.ToString()
            Write-Host $text
            Add-Content -LiteralPath $LogPath -Value $text -Encoding UTF8
        }
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $oldErrorActionPreference
    }
    if ($exitCode -ne 0) {
        throw "Command failed with exit code $exitCode"
    }
}

function Test-PrivateGpuBaseRuntime {
    try {
        if (-not (Test-Path -LiteralPath $BasePython)) {
            return $false
        }
        $info = & $BasePython -c "import platform,sys,venv,ensurepip; print('.'.join(map(str, sys.version_info[:3]))); print(platform.architecture()[0])" 2>$null
        return ($LASTEXITCODE -eq 0 -and $info.Count -ge 2 -and $info[0] -like "3.10.*" -and $info[1] -eq "64bit")
    } catch {
        return $false
    }
}

function Test-GpuRuntimeUsesPrivateBase {
    if (-not (Test-Path -LiteralPath $GpuPython)) {
        return $false
    }
    $venvConfig = Join-Path $RuntimeDir "pyvenv.cfg"
    if (-not (Test-Path -LiteralPath $venvConfig)) {
        return $false
    }
    try {
        $homeLine = Get-Content -LiteralPath $venvConfig | Where-Object { $_ -match "^home\s*=" } | Select-Object -First 1
        if (-not $homeLine) {
            return $false
        }
        $venvHome = (($homeLine -replace "^home\s*=\s*", "").TrimEnd("\"))
        $expectedHome = ([IO.Path]::GetFullPath($BaseRuntimeDir)).TrimEnd("\")
        return ([IO.Path]::GetFullPath($venvHome)).TrimEnd("\") -eq $expectedHome
    } catch {
        return $false
    }
}

function Reset-ToolGpuRuntime {
    if (-not (Test-Path -LiteralPath $RuntimeDir)) {
        return
    }
    $resolvedToolRoot = ([IO.Path]::GetFullPath($ScriptDir)).TrimEnd("\") + "\"
    $resolvedRuntime = [IO.Path]::GetFullPath($RuntimeDir)
    if (-not $resolvedRuntime.StartsWith($resolvedToolRoot, [StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to remove GPU runtime outside the tool directory: $RuntimeDir"
    }
    Write-Log "Replacing legacy or incomplete runtime_gpu with a tool-private environment"
    Remove-Item -LiteralPath $RuntimeDir -Recurse -Force
}

Write-Log "Start configuring NIKKE OCR GPU runtime"
Write-Log ("Tool directory: {0}" -f $ScriptDir)

if (-not (Test-Path $Requirements)) {
    throw "GPU requirements file not found: $Requirements"
}

$nvidiaSmiCommand = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
$nvidiaSmiPath = if ($nvidiaSmiCommand) { $nvidiaSmiCommand.Source } else { $null }
if (-not $nvidiaSmiPath) {
    $commonSmi = Join-Path $env:ProgramFiles "NVIDIA Corporation\NVSMI\nvidia-smi.exe"
    if (Test-Path $commonSmi) {
        $nvidiaSmiPath = $commonSmi
    }
}
if (-not $nvidiaSmiPath) {
    throw "nvidia-smi was not found. Please install or repair the NVIDIA display driver first."
}

Write-Log "Checking NVIDIA driver"
Invoke-Logged -FilePath $nvidiaSmiPath -Arguments @()

if (-not (Test-PrivateGpuBaseRuntime)) {
    throw "The bundled Python 3.10 GPU base runtime is missing or invalid. Please reinstall the complete tool package."
}

if (-not (Test-GpuRuntimeUsesPrivateBase)) {
    Reset-ToolGpuRuntime
    Write-Log "Creating runtime_gpu from the bundled private Python 3.10 runtime"
    Invoke-Logged -FilePath $BasePython -Arguments @("-m", "venv", $RuntimeDir)
} else {
    Write-Log "Existing tool-private runtime_gpu detected; dependencies will be installed/repaired in place"
}

Write-Log "Upgrading pip/setuptools/wheel"
$bootstrapArguments = @("-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel")
if (-not (Test-Path $Wheelhouse)) {
    $bootstrapArguments += @("--index-url", $PipIndexUrl)
}
Invoke-Logged -FilePath $GpuPython -Arguments $bootstrapArguments

Write-Log "Removing incompatible CPU PaddlePaddle package if present"
Invoke-Logged -FilePath $GpuPython -Arguments @("-m", "pip", "uninstall", "-y", "paddlepaddle")

Write-Log "Installing GPU OCR dependencies"
if (Test-Path $Wheelhouse) {
    Write-Log ("Offline wheelhouse detected: {0}" -f $Wheelhouse)
    Invoke-Logged -FilePath $GpuPython -Arguments @("-m", "pip", "install", "--upgrade", "--no-index", "--find-links", $Wheelhouse, "-r", $Requirements)
} else {
    Write-Log ("Using pip index: {0}" -f $PipIndexUrl)
    Invoke-Logged -FilePath $GpuPython -Arguments @("-m", "pip", "install", "--upgrade", "--index-url", $PipIndexUrl, "-r", $Requirements)
}

Write-Log "Writing Windows NVIDIA DLL search path helper"
$sitePackages = (& $GpuPython -c "import site; print(site.getsitepackages()[0])").Trim()
if (-not $sitePackages -or -not (Test-Path $sitePackages)) {
    throw "Could not locate runtime_gpu site-packages."
}

$sitecustomize = @'
"""Register bundled NVIDIA runtime DLL directories for Paddle GPU on Windows."""

from __future__ import annotations

import os
from pathlib import Path


if os.name == "nt" and hasattr(os, "add_dll_directory"):
    site_packages = Path(__file__).resolve().parent
    for relative in (
        "nvidia/cuda_runtime/bin",
        "nvidia/cublas/bin",
        "nvidia/cuda_nvrtc/bin",
        "nvidia/cudnn/bin",
    ):
        dll_dir = site_packages / relative
        if dll_dir.exists():
            try:
                os.add_dll_directory(str(dll_dir))
            except OSError:
                pass
'@
Set-Content -LiteralPath (Join-Path $sitePackages "sitecustomize.py") -Value $sitecustomize -Encoding UTF8

Write-Log "Verifying GPU OCR runtime for GUI detection"
$verifyPath = Join-Path $env:TEMP ("nikke_gpu_verify_{0}.py" -f ([Guid]::NewGuid().ToString("N")))
$verify = @'
from PIL import Image
import cv2
import numpy
import openpyxl
import paddle
import paddleocr

compiled = paddle.device.is_compiled_with_cuda()
count = paddle.device.cuda.device_count()
print("paddle", paddle.__version__)
print("compiled_with_cuda", compiled)
print("cuda_device_count", count)
raise SystemExit(0 if compiled and count > 0 else 1)
'@
Set-Content -LiteralPath $verifyPath -Value $verify -Encoding UTF8
try {
    Invoke-Logged -FilePath $GpuPython -Arguments @($verifyPath)
} finally {
    Remove-Item -LiteralPath $verifyPath -Force -ErrorAction SilentlyContinue
}

Write-Log "GPU runtime setup succeeded. Restart the GUI and select GPU mode."
