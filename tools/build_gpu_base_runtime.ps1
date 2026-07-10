param(
    [string]$BuildPythonExe = "",
    [switch]$ReplaceExisting
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WorkRoot = Join-Path $ProjectRoot "work\gpu_base_runtime_build"
$Target = Join-Path $ProjectRoot "runtime_python310_base"

function Write-Step([string]$Message) {
    Write-Host ("[{0}] {1}" -f (Get-Date -Format "HH:mm:ss"), $Message)
}

function Resolve-BuildPython {
    $candidate = if ($BuildPythonExe) {
        $BuildPythonExe
    } else {
        Join-Path $env:LOCALAPPDATA "Programs\Python\Python310\python.exe"
    }
    if (-not (Test-Path -LiteralPath $candidate)) {
        throw "Python 3.10 x64 build interpreter was not found. Pass -BuildPythonExe with its full path."
    }

    $result = & $candidate -c "import platform,sys; print(sys.version_info[:2] == (3, 10)); print(platform.architecture()[0])"
    if ($LASTEXITCODE -ne 0 -or $result.Count -lt 2 -or $result[0].Trim() -ne "True" -or $result[1].Trim() -ne "64bit") {
        throw "Build interpreter must be Python 3.10 64-bit: $candidate"
    }
    return (Resolve-Path -LiteralPath $candidate).Path
}

function Assert-ChildPath([string]$Path, [string]$Parent, [string]$Label) {
    $resolvedPath = [IO.Path]::GetFullPath($Path)
    $resolvedParent = [IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
    if (-not $resolvedPath.StartsWith($resolvedParent, [StringComparison]::OrdinalIgnoreCase)) {
        throw "$Label must stay inside ${Parent}: $Path"
    }
}

function Remove-GeneratedDirectory([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return }
    Assert-ChildPath $Path $WorkRoot "Generated directory"
    Remove-Item -LiteralPath $Path -Recurse -Force
}

function Remove-UnneededRuntimeFiles([string]$Stage) {
    foreach ($relative in @(
        "Lib\site-packages",
        "Lib\test",
        "Lib\idlelib",
        "Lib\lib2to3",
        "Lib\tkinter",
        "Lib\turtledemo"
    )) {
        $path = Join-Path $Stage $relative
        if (Test-Path -LiteralPath $path) {
            Remove-Item -LiteralPath $path -Recurse -Force
        }
    }

    Get-ChildItem -LiteralPath $Stage -Recurse -Force -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $Stage -Recurse -Force -File -Filter "*.pyc" -ErrorAction SilentlyContinue |
        Remove-Item -Force
    Get-ChildItem -LiteralPath (Join-Path $Stage "DLLs") -Force -File |
        Where-Object { $_.Name -match "\.pdb$|_d\.(dll|pyd)$" } |
        Remove-Item -Force
}

function Test-GpuBaseRuntime([string]$RuntimeDir) {
    $pythonExe = Join-Path $RuntimeDir "python.exe"
    $check = & $pythonExe -c "import ensurepip, sqlite3, ssl, sys, venv; assert sys.version_info[:2] == (3, 10); print('base_runtime_ok', sys.version)"
    if ($LASTEXITCODE -ne 0 -or -not $check) {
        throw "GPU base runtime import validation failed."
    }

    $venvDir = Join-Path $WorkRoot ("venv_smoke_{0}" -f ([Guid]::NewGuid().ToString("N")))
    try {
        & $pythonExe -m venv $venvDir
        if ($LASTEXITCODE -ne 0) {
            throw "GPU base runtime could not create a virtual environment."
        }
        $venvPython = Join-Path $venvDir "Scripts\python.exe"
        & $venvPython -c "import pip, sys; print('venv_ok', sys.version)"
        if ($LASTEXITCODE -ne 0) {
            throw "GPU base runtime virtual environment validation failed."
        }
    } finally {
        Remove-GeneratedDirectory $venvDir
    }
}

function Publish-Stage([string]$Stage) {
    if (Test-Path -LiteralPath $Target) {
        if (-not $ReplaceExisting) {
            throw "Target already exists: $Target. Re-run with -ReplaceExisting after reviewing it."
        }
        $backupRoot = Join-Path $WorkRoot "backups"
        New-Item -ItemType Directory -Force -Path $backupRoot | Out-Null
        $backup = Join-Path $backupRoot ("runtime_python310_base_{0}" -f (Get-Date -Format "yyyyMMdd_HHmmss"))
        Write-Step "Backing up existing runtime to $backup"
        Move-Item -LiteralPath $Target -Destination $backup
    }
    Move-Item -LiteralPath $Stage -Destination $Target
}

New-Item -ItemType Directory -Force -Path $WorkRoot | Out-Null
$buildPython = Resolve-BuildPython
$sourceRoot = Split-Path -Parent $buildPython
$stage = Join-Path $WorkRoot ("stage_{0}" -f (Get-Date -Format "yyyyMMdd_HHmmss"))

try {
    Write-Step "Building private Python 3.10 GPU base runtime from $sourceRoot"
    New-Item -ItemType Directory -Force -Path $stage | Out-Null

    foreach ($file in @(
        "LICENSE.txt",
        "python.exe",
        "pythonw.exe",
        "python3.dll",
        "python310.dll",
        "vcruntime140.dll",
        "vcruntime140_1.dll"
    )) {
        $source = Join-Path $sourceRoot $file
        if (-not (Test-Path -LiteralPath $source)) {
            throw "Required CPython runtime file is missing: $source"
        }
        Copy-Item -LiteralPath $source -Destination (Join-Path $stage $file) -Force
    }

    foreach ($directory in @("DLLs", "Lib")) {
        $source = Join-Path $sourceRoot $directory
        if (-not (Test-Path -LiteralPath $source)) {
            throw "Required CPython runtime directory is missing: $source"
        }
        Copy-Item -LiteralPath $source -Destination (Join-Path $stage $directory) -Recurse -Force
    }

    Remove-UnneededRuntimeFiles $stage
    Test-GpuBaseRuntime $stage
    Publish-Stage $stage

    $sizeMb = [math]::Round(((Get-ChildItem -LiteralPath $Target -Recurse -Force -File | Measure-Object -Property Length -Sum).Sum) / 1MB, 1)
    Write-Step "Private GPU base runtime is ready: $Target ($sizeMb MB)"
} finally {
    Remove-GeneratedDirectory $stage
}
