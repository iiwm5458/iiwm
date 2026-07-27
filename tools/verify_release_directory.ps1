param(
    [Parameter(Mandatory = $true)]
    [string]$ReleaseRoot
)

$ErrorActionPreference = "Stop"
$ReleaseRoot = [IO.Path]::GetFullPath($ReleaseRoot)

function Require-Path([string]$RelativePath) {
    $path = Join-Path $ReleaseRoot $RelativePath
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing release path: $RelativePath"
    }
    return $path
}

$required = @(
    "run_gui.bat",
    "nikke_gui_bootstrap.ps1",
    "nikke_gui_launcher.ps1",
    "nikke_round_stitcher.py",
    "nikke_image_tools.py",
    "nikke_character_capture.py",
    "nikke_round_config.json",
    "assets",
    "vendor\LibreHardwareMonitorLib",
    "runtime_core\python.exe",
    "runtime_cpu\python.exe",
    "runtime_python310_base\python.exe",
    "setup_gpu_runtime.bat",
    "setup_gpu_runtime_cn.bat",
    "setup_gpu_runtime_aliyun.bat",
    "setup_gpu_runtime.ps1",
    "dataanalysis\arena_ocr_tool\main.py",
    "dataanalysis\arena_ocr_tool\recognizer",
    "dataanalysis\arena_ocr_tool\data\nikke_names.json",
    "dataanalysis\arena_ocr_tool\models\paddle_default\whl\det\ch\ch_PP-OCRv4_det_infer\inference.pdmodel",
    "dataanalysis\arena_ocr_tool\models\paddle_default\whl\rec\ch\ch_PP-OCRv4_rec_infer\inference.pdmodel"
)
foreach ($item in $required) { Require-Path $item | Out-Null }

$corePython = Require-Path "runtime_core\python.exe"
$cpuPython = Require-Path "runtime_cpu\python.exe"
$gpuBasePython = Require-Path "runtime_python310_base\python.exe"
& $corePython -c "import sys; from pathlib import Path; from PIL import ImageGrab; assert Path(sys.prefix).resolve() == Path(sys.base_prefix).resolve(); print('core_runtime_ok')"
if ($LASTEXITCODE -ne 0) { throw "runtime_core validation failed" }
& $corePython (Require-Path "nikke_image_tools.py") "--help" *> $null
if ($LASTEXITCODE -ne 0) { throw "Image tools runtime validation failed" }
& $cpuPython -c "import sys; from pathlib import Path; import paddle, paddleocr, cv2, openpyxl; assert Path(sys.prefix).resolve() == Path(sys.base_prefix).resolve(); print('cpu_runtime_ok', paddle.__version__)"
if ($LASTEXITCODE -ne 0) { throw "runtime_cpu validation failed" }
& $gpuBasePython -c "import ensurepip, ssl, sqlite3, sys, venv; assert sys.version_info[:2] == (3, 10); print('gpu_base_runtime_ok')"
if ($LASTEXITCODE -ne 0) { throw "runtime_python310_base validation failed" }

$offlineHome = Join-Path $ReleaseRoot "_offline_model_validation"
Remove-Item -LiteralPath $offlineHome -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $offlineHome | Out-Null
$previousHome = $env:HOME
$previousUserProfile = $env:USERPROFILE
try {
    $env:HOME = $offlineHome
    $env:USERPROFILE = $offlineHome
    $toolRoot = Join-Path $ReleaseRoot "dataanalysis\arena_ocr_tool"
    & $cpuPython -c "import sys; sys.path.insert(0, r'$toolRoot'); from recognizer.arena_ocr import ArenaOCRRecognizer; from PIL import Image; reader=ArenaOCRRecognizer(False); assert reader.available, reader.error; reader.recognize_region(Image.new('RGB',(160,64),'white')); print('offline_models_ok')"
    if ($LASTEXITCODE -ne 0) { throw "Offline PaddleOCR validation failed" }
} finally {
    $env:HOME = $previousHome
    $env:USERPROFILE = $previousUserProfile
    Remove-Item -LiteralPath $offlineHome -Recurse -Force -ErrorAction SilentlyContinue
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ReleaseRoot "nikke_gui_bootstrap.ps1") -Check
if ($LASTEXITCODE -ne 0) { throw "GUI release validation failed" }

Write-Host "release verification ok: $ReleaseRoot"
