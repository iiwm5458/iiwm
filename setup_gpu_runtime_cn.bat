@echo off
chcp 65001 >nul
setlocal

set "SCRIPT_DIR=%~dp0"
set "CN_PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple"

echo =======================================================
echo NIKKE OCR GPU runtime setup - China mainland mirror
echo.
echo This script will configure GPU acceleration for this tool.
echo It will download third-party components from a China mainland PyPI mirror:
echo %CN_PIP_INDEX%
echo.
echo Components may include PaddlePaddle GPU and NVIDIA CUDA/cuDNN runtime packages.
echo Continue only if you accept the corresponding third-party license terms.
echo Press Ctrl+C to cancel, or press any key to continue.
echo =======================================================
echo.
pause
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%setup_gpu_runtime.ps1" -PipIndexUrl "%CN_PIP_INDEX%" %*

set "CODE=%ERRORLEVEL%"
echo.
if "%CODE%"=="0" (
    echo GPU runtime setup completed. Restart the GUI and select GPU mode.
) else (
    echo GPU runtime setup failed. Check the error above or gpu_runtime_setup_*.log.
    echo If this mirror fails, try setup_gpu_runtime.bat or edit CN_PIP_INDEX in this file.
)
echo.
pause
exit /b %CODE%
