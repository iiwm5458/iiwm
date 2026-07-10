param([switch]$Check)

$ErrorActionPreference = "Stop"
$LauncherPath = Join-Path (Split-Path -Parent $MyInvocation.MyCommand.Path) "nikke_gui_launcher.ps1"

if (-not (Test-Path -LiteralPath $LauncherPath)) {
    throw "GUI launcher was not found: $LauncherPath"
}

if ($Check) {
    & $LauncherPath -Check
} else {
    & $LauncherPath
}

exit $LASTEXITCODE
