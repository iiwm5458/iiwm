param(
    [string]$PythonExe = "python"
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Requirements = Join-Path $ScriptDir "requirements-ocr.txt"

if (-not (Test-Path -LiteralPath $Requirements)) {
    throw "requirements-ocr.txt not found: $Requirements"
}

& $PythonExe -m pip install -r $Requirements
