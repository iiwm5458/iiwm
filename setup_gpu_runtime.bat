@echo off
chcp 65001 >nul
setlocal

set "SCRIPT_DIR=%~dp0"

echo =======================================================
echo NIKKE OCR GPU runtime setup
echo.
echo This script will configure GPU acceleration for this tool.
echo It may download third-party components from the official PyPI source,
echo including PaddlePaddle GPU and NVIDIA CUDA/cuDNN runtime packages.
echo.
echo Continue only if you accept the corresponding third-party license terms.
echo Press Ctrl+C to cancel, or press any key to continue.
echo =======================================================
echo.
pause
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%setup_gpu_runtime.ps1" %*

set "CODE=%ERRORLEVEL%"
echo.
if "%CODE%"=="0" (
    echo GPU runtime setup completed. Restart the GUI and select GPU mode.
) else (
    echo GPU runtime setup failed. Check the error above or gpu_runtime_setup_*.log.
)
echo.
pause
exit /b %CODE%
