@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   WebGIS - Sinh Chung Chi SSL ^& CA Noi Bo
echo ========================================================
echo.

set "ROOT_PATH=%~dp0.."

if exist "%ROOT_PATH%\backend\data-serving\.venv\Scripts\python.exe" (
    "%ROOT_PATH%\backend\data-serving\.venv\Scripts\python.exe" "%ROOT_PATH%\scripts\generate_ssl_certs.py"
) else (
    python "%ROOT_PATH%\scripts\generate_ssl_certs.py"
)

if %errorlevel% neq 0 (
    echo [ERROR] Khong the sinh chung chi SSL.
    pause
    exit /b 1
)

echo.
pause
