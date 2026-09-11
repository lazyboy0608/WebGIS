# ========================================================
# WebGIS - Tat toan bo he thong Local Dev (PowerShell)
# ========================================================

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  WebGIS - Dang tat toan bo cac tien trinh Local..." -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Dong cac cua so cmd co title WebGIS
Write-Host "[1/5] Dong cac cua so dich vu WebGIS..." -ForegroundColor Yellow
taskkill /f /t /fi "WINDOWTITLE eq WebGIS*" 2>$null | Out-Null

# 2. Tat cac process lang nghe tren port (5173, 8000, 8001, 6379, 9000, 9001)
Write-Host "[2/5] Tat tien trinh theo Ports (5173, 8000, 8001, 6379, 9000, 9001)..." -ForegroundColor Yellow
$ports = @(5173, 8000, 8001, 6379, 9000, 9001)
foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        if ($conn.OwningProcess -and $conn.OwningProcess -ne 0) {
            taskkill /f /t /pid $conn.OwningProcess 2>$null | Out-Null
        }
    }
}

# 3. Kill Node.js / Vite
Write-Host "[3/5] Tat Frontend (Node.js)..." -ForegroundColor Yellow
Get-CimInstance Win32_Process -Filter "Name = 'node.exe'" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*WebGIS*"
} | ForEach-Object {
    taskkill /f /t /pid $_.ProcessId 2>$null | Out-Null
}

# 4. Kill Python / Uvicorn under WebGIS
Write-Host "[4/5] Tat Backend Python / Uvicorn..." -ForegroundColor Yellow
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*WebGIS*" -or $_.CommandLine -like "*uvicorn*"
} | ForEach-Object {
    taskkill /f /t /pid $_.ProcessId 2>$null | Out-Null
}

# 5. Kill Redis & MinIO
Write-Host "[5/5] Tat Redis & MinIO Server..." -ForegroundColor Yellow
Stop-Process -Name "redis-server" -Force -ErrorAction SilentlyContinue
Stop-Process -Name "minio" -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  DA TAT SACH TOAN BO TIEN TRINH WEBGIS!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
