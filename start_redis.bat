@echo off
setlocal

set "REDIS_DIR=%~dp0tools\redis"
set "REDIS_EXE=%REDIS_DIR%\redis-server.exe"
set "REDIS_CONF=%REDIS_DIR%\redis.windows.conf"
set "REDIS_DATA=%~dp0storage\redis_data"

if not exist "%REDIS_DIR%" mkdir "%REDIS_DIR%"
if not exist "%REDIS_DATA%" mkdir "%REDIS_DATA%"

if not exist "%REDIS_EXE%" (
    echo [Redis] Dang tai Redis for Windows tu GitHub...
    powershell -Command "Invoke-WebRequest -Uri 'https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip' -OutFile '%REDIS_DIR%\redis.zip'; Expand-Archive -Path '%REDIS_DIR%\redis.zip' -DestinationPath '%REDIS_DIR%' -Force; Remove-Item '%REDIS_DIR%\redis.zip' -Force"
    if not exist "%REDIS_EXE%" (
        echo [ERROR] Khong the tai redis-server.exe. Vui long kiem tra ket noi mang.
        pause
        exit /b 1
    )
    echo [Redis] Tai thanh cong!
)

echo ========================================================
echo   WebGIS Redis Server dang khoi dong...
echo   - Port:        6379
echo   - Executable:  %REDIS_EXE%
echo   - Storage:     %REDIS_DATA%
echo   - Max Memory:  2GB (allkeys-lru)
echo ========================================================

"%REDIS_EXE%" "%REDIS_CONF%" --dir "%REDIS_DATA%" --maxmemory 2gb --maxmemory-policy allkeys-lru

pause
