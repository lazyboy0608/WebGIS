@echo off
echo ========================================================
echo   WebGIS - Dang tat toan bo cac dich vu Local Dev...
echo ========================================================
echo.

:: 1. Dong cac cua so cmd co title WebGIS va toan bo cay tien trinh con
echo [1/5] Dong cac cua so dich vu WebGIS...
taskkill /f /t /fi "WINDOWTITLE eq WebGIS*" >nul 2>&1

:: 2. Tat cac process lang nghe tren cac port cua he thong
echo [2/5] Tat cac dich vu theo Port (5173, 8000, 8001, 6379, 9000, 9001)...
for %%p in (5173 8000 8001 6379 9000 9001) do (
    for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":%%p" ^| findstr "LISTENING"') do (
        taskkill /f /t /pid %%a >nul 2>&1
    )
)

:: 3. Tat Frontend (Node.js)
echo [3/5] Tat Frontend (Node.js)...
taskkill /f /im node.exe >nul 2>&1

:: 4. Tat Redis Server
echo [4/5] Tat Redis Server...
taskkill /f /im redis-server.exe >nul 2>&1

:: 5. Tat MinIO Server
echo [5/5] Tat MinIO Server...
taskkill /f /im minio.exe >nul 2>&1

echo.
echo ========================================================
echo   DA TAT SACH TOAN BO TIEN TRINH WEBGIS!
echo ========================================================
echo.
timeout /t 2 >nul
