@echo off
echo ========================================================
echo   WebGIS - Dang tat toan bo cac dich vu Local Dev...
echo ========================================================
echo.

:: Tat cac tien trinh node, uvicorn, redis-server, minio
echo [1/4] Tat Frontend (Node.js)...
taskkill /f /im node.exe >nul 2>&1

echo [2/4] Tat Backend 1 & 2 (Uvicorn / Python)...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8001" ^| findstr "LISTENING"') do taskkill /f /pid %%a >nul 2>&1

echo [3/4] Tat Redis Server...
taskkill /f /im redis-server.exe >nul 2>&1

echo [4/4] Tat MinIO Server...
taskkill /f /im minio.exe >nul 2>&1

echo.
echo ========================================================
echo   DA TAT SACH TOAN BO TIEN TRINH WEBGIS!
echo ========================================================
echo.
timeout /t 2 >nul
