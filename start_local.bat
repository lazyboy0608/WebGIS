@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   WebGIS - Khoi dong toan bo he thong Local Dev
echo ========================================================
echo.

:: 1. Khoi dong Redis Server
echo [1/5] Khoi dong Redis Server (Port 6379)...
start "WebGIS-Redis" /min cmd /c "d:\WebGIS\start_redis.bat"

:: 2. Khoi dong MinIO Server
echo [2/5] Khoi dong MinIO Server (Port 9000/9001)...
start "WebGIS-MinIO" /min cmd /c "d:\WebGIS\start_minio.bat"

:: 3. Khoi dong Backend 1: SEGY Processing Service
echo [3/5] Khoi dong Backend 1: SEGY Processing (Port 8000)...
start "WebGIS-BE1-Processing" /min cmd /c "cd /d d:\WebGIS\backend\segy-processing-service && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload"

:: 4. Khoi dong Backend 2: Data Serving Service
echo [4/5] Khoi dong Backend 2: Data Serving (Port 8001)...
start "WebGIS-BE2-DataServing" /min cmd /c "cd /d d:\WebGIS\backend\data-serving && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload"

:: 5. Khoi dong Frontend (Vite Dev Server)
echo [5/5] Khoi dong Frontend (Port 5173)...
start "WebGIS-Frontend" /min cmd /c "cd /d d:\WebGIS\frontend && npm run dev"

echo.
echo ========================================================
echo   TAT CA DICH VU DA DUOC KHOI DONG THANH CONG!
echo.
echo   - Frontend Web App:     http://localhost:5173
echo   - Backend 1 (SEGY API): http://localhost:8000/docs
echo   - Backend 2 (Data API): http://localhost:8001/docs
echo   - MinIO Console:        http://localhost:9001
echo   - Redis Cache:          127.0.0.1:6379
echo.
echo   (De dung toan bo he thong, chay file: stop_local.bat)
echo ========================================================
echo.
timeout /t 3 >nul
