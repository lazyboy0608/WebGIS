@echo off
setlocal

set "MINIO_DIR=%~dp0tools\minio"
set "MINIO_EXE=%MINIO_DIR%\minio.exe"
set "DATA_DIR=%~dp0storage\minio_data"

if not exist "%MINIO_DIR%" mkdir "%MINIO_DIR%"
if not exist "%DATA_DIR%" mkdir "%DATA_DIR%"

if not exist "%MINIO_EXE%" (
    echo [MinIO] Dang tai minio.exe tu dl.min.io...
    powershell -Command "Invoke-WebRequest -Uri 'https://dl.min.io/server/minio/release/windows-amd64/minio.exe' -OutFile '%MINIO_EXE%'"
    if not exist "%MINIO_EXE%" (
        echo [ERROR] Khong the tai minio.exe. Vui long kiem tra ket noi mang.
        pause
        exit /b 1
    )
    echo [MinIO] Tai thanh cong!
)

set "MINIO_ROOT_USER=minioadmin"
set "MINIO_ROOT_PASSWORD=minioadmin"

echo ========================================================
echo   MinIO Server dang khoi dong...
echo   - S3 API:      http://localhost:9000
echo   - Web Console: http://localhost:9001
echo   - User:        minioadmin
echo   - Password:    minioadmin
echo   - Storage:     %DATA_DIR%
echo ========================================================

"%MINIO_EXE%" server "%DATA_DIR%" --address ":9000" --console-address ":9001"

pause
