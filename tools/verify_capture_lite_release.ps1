param(
    [Parameter(Mandatory = $true)]
    [string]$ReleaseRoot
)

$ErrorActionPreference = "Stop"
$ReleaseRoot = [IO.Path]::GetFullPath($ReleaseRoot)

function Require-Path([string]$RelativePath) {
    $path = Join-Path $ReleaseRoot $RelativePath
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing lightweight release path: $RelativePath"
    }
    return $path
}

foreach ($item in @(
    "run_capture_lite.bat",
    "nikke_capture_lite_launcher.ps1",
    "nikke_round_stitcher.py",
    "nikke_character_capture.py",
    "nikke_round_config.json",
    "assets",
    "runtime_core\python.exe",
    "group_custom_backgrounds\pixiewall-a1cg6q-3840x2160.jpg"
)) {
    Require-Path $item | Out-Null
}

foreach ($forbidden in @(
    "runtime_cpu",
    "runtime_python310_base",
    "runtime_gpu",
    "dataanalysis",
    "vendor",
    "setup_gpu_runtime.bat",
    "setup_gpu_runtime_cn.bat",
    "setup_gpu_runtime.ps1",
    "GPU_OCR_RUNTIME_SETUP_GUIDE.md",
    "GPU_OCR_RUNTIME_SETUP_GUIDE.pdf"
)) {
    if (Test-Path -LiteralPath (Join-Path $ReleaseRoot $forbidden)) {
        throw "Lightweight release contains excluded OCR/GPU resource: $forbidden"
    }
}

$corePython = Require-Path "runtime_core\python.exe"
& $corePython -c "import sys; from pathlib import Path; from PIL import ImageGrab; assert Path(sys.prefix).resolve() == Path(sys.base_prefix).resolve(); print('lite_core_runtime_ok')"
if ($LASTEXITCODE -ne 0) { throw "runtime_core validation failed" }
& $corePython (Require-Path "nikke_round_stitcher.py") "--help" *> $null
if ($LASTEXITCODE -ne 0) { throw "Lightweight screenshot worker validation failed" }

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Require-Path "nikke_capture_lite_launcher.ps1") -Check
if ($LASTEXITCODE -ne 0) { throw "Lightweight GUI validation failed" }

$launcher = Get-Content -LiteralPath (Require-Path "nikke_capture_lite_launcher.ps1") -Raw -Encoding utf8
foreach ($required in @(
    "Show-LiteFullVersionRequired",
    "该功能依赖 PaddleCPU/PaddleGPU 图像识别环境，请指挥官安装完整版工具。",
    'SeasonCaptureButton" Grid.Row="3" Height="64" Style="{StaticResource DarkButton}" Margin="0,0,0,16" Visibility="Collapsed"'
)) {
    if (-not $launcher.Contains($required)) {
        throw "Lightweight launcher is missing required boundary behavior: $required"
    }
}
foreach ($forbidden in @(
    '$OcrPythonExe = Resolve-OcrPythonExe',
    '$OcrGpuPythonExe = Resolve-OcrGpuPythonExe',
    'GPU_OCR_RUNTIME_SETUP_GUIDE.pdf'
)) {
    if ($launcher.Contains($forbidden)) {
        throw "Lightweight launcher still references full OCR behavior: $forbidden"
    }
}

Write-Host "lightweight release verification ok: $ReleaseRoot"
