@echo off
setlocal

set "SCRIPT_DIR=%~dp0"
set "WORKER_EXE=%SCRIPT_DIR%nikke_character_capture_worker.exe"
set "RUNTIME_CPU_PY=%SCRIPT_DIR%runtime_cpu\Scripts\python.exe"
set "USER_PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"

if exist "%WORKER_EXE%" (
    "%WORKER_EXE%" %*
) else if exist "%RUNTIME_CPU_PY%" (
    "%RUNTIME_CPU_PY%" -c "from PIL import Image, ImageDraw, ImageGrab" >nul 2>nul
    if "%ERRORLEVEL%"=="0" (
        "%RUNTIME_CPU_PY%" "%SCRIPT_DIR%nikke_character_capture.py" %*
    ) else if exist "%USER_PY%" (
        "%USER_PY%" "%SCRIPT_DIR%nikke_character_capture.py" %*
    ) else (
        python "%SCRIPT_DIR%nikke_character_capture.py" %*
    )
) else if exist "%USER_PY%" (
    "%USER_PY%" "%SCRIPT_DIR%nikke_character_capture.py" %*
) else (
    python "%SCRIPT_DIR%nikke_character_capture.py" %*
)

set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" pause
exit /b %CODE%
