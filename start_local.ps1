# ========================================================
# WebGIS - Khoi dong toan bo he thong Local Dev (PowerShell)
# ========================================================

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  WebGIS - Khoi dong toan bo he thong Local Dev" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$rootPath = "d:\WebGIS"

# 1. Redis Server
Write-Host "[1/5] Khoi dong Redis Server (Port 6379)..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/k title WebGIS-Redis && cd /d $rootPath\tools\redis && redis-server.exe redis.windows.conf" -WindowStyle Normal

# 2. MinIO Server
Write-Host "[2/5] Khoi dong MinIO Server (Port 9000/9001)..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/k title WebGIS-MinIO && set MINIO_ROOT_USER=minioadmin&& set MINIO_ROOT_PASSWORD=minioadmin&& $rootPath\tools\minio\minio.exe server $rootPath\storage\minio_data --console-address :9001 --address :9000" -WindowStyle Normal

# 3. Backend 1: SEGY Processing
Write-Host "[3/5] Khoi dong Backend 1: SEGY Processing (Port 8000)..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/k title WebGIS-BE1-Processing && cd /d $rootPath\backend\segy-processing-service && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload" -WindowStyle Normal

# 4. Backend 2: Data Serving
Write-Host "[4/5] Khoi dong Backend 2: Data Serving (Port 8001)..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/k title WebGIS-BE2-DataServing && cd /d $rootPath\backend\data-serving && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload" -WindowStyle Normal

# 5. Frontend
Write-Host "[5/5] Khoi dong Frontend (Port 5173)..." -ForegroundColor Yellow
Start-Process -FilePath "cmd.exe" -ArgumentList "/k title WebGIS-Frontend && cd /d $rootPath\frontend && npm run dev" -WindowStyle Normal

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  TAT CA DICH VU DA DUOC KHOI DONG THANH CONG!" -ForegroundColor Green
Write-Host ""
Write-Host "  - Frontend Web App:     http://localhost:5173" -ForegroundColor White
Write-Host "  - Backend 1 (SEGY API): http://localhost:8000/docs" -ForegroundColor White
Write-Host "  - Backend 2 (Data API): http://localhost:8001/docs" -ForegroundColor White
Write-Host "  - MinIO Console:        http://localhost:9001 (minioadmin / minioadmin)" -ForegroundColor White
Write-Host "  - MinIO S3 API:         http://localhost:9000" -ForegroundColor White
Write-Host "  - Redis Cache:          127.0.0.1:6379" -ForegroundColor White
Write-Host ""
Write-Host "  (De tat toan bo he thong, chay: .\stop_local.ps1)" -ForegroundColor Gray
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
