param(
    [string]$Version = "0.1.0",
    [string]$IsccPath = ""
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
# Keep the compiler staging root short so deeply nested Paddle files stay below Windows path limits.
$ReleaseRoot = Join-Path $ProjectRoot ("dist\r_{0}" -f $Version)
$InstallerScript = Join-Path $ProjectRoot "installer\NIKKE_Arena_Tool.iss"

function Clear-ReleaseBytecode([string]$Root) {
    Get-ChildItem -LiteralPath $Root -Recurse -Force -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
        Remove-Item -Recurse -Force
    Get-ChildItem -LiteralPath $Root -Recurse -Force -File -Filter "*.pyc" -ErrorAction SilentlyContinue |
        Remove-Item -Force
}

if (-not $IsccPath) {
    $candidates = @(
        (Join-Path $ProjectRoot "work\inno_setup\program\ISCC.exe"),
        "C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
        "C:\Program Files\Inno Setup 6\ISCC.exe"
    )
    $IsccPath = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $IsccPath -or -not (Test-Path -LiteralPath $IsccPath)) {
    throw "Inno Setup compiler ISCC.exe was not found. Install Inno Setup 6, then re-run with -IsccPath."
}

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "build_release_directory.ps1") -Version $Version -DestinationRoot $ReleaseRoot -ReplaceExisting
if ($LASTEXITCODE -ne 0) { throw "Release directory build failed" }

& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "verify_release_directory.ps1") -ReleaseRoot $ReleaseRoot
if ($LASTEXITCODE -ne 0) { throw "Release directory validation failed" }
Clear-ReleaseBytecode $ReleaseRoot

& $IsccPath ("/DAppVersion={0}" -f $Version) ("/DReleaseRoot={0}" -f $ReleaseRoot) $InstallerScript
if ($LASTEXITCODE -ne 0) { throw "Inno Setup compilation failed" }

Write-Host ("installer build complete: {0}" -f (Join-Path $ProjectRoot ("dist\installer\NIKKE_Arena_Tool_Setup_{0}.exe" -f $Version)))
