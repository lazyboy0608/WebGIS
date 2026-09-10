# ========================================================
# WebGIS - Tat toan bo he thong Local Dev (PowerShell)
# ========================================================

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  WebGIS - Dang tat toan bo cac tien trinh Local..." -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Kill Node.js
Write-Host "[1/4] Tat Frontend (Node.js)..." -ForegroundColor Yellow
Stop-Process -Name "node" -Force -ErrorAction SilentlyContinue

# 2. Kill Python Uvicorn ports 8000 & 8001
Write-Host "[2/4] Tat Backend 1 & Backend 2 (Uvicorn)..." -ForegroundColor Yellow
$ports = @(8000, 8001)
foreach ($port in $ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        if ($conn.OwningProcess) {
            Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
        }
    }
}

# 3. Kill Redis Server
Write-Host "[3/4] Tat Redis Server..." -ForegroundColor Yellow
Stop-Process -Name "redis-server" -Force -ErrorAction SilentlyContinue

# 4. Kill MinIO Server
Write-Host "[4/4] Tat MinIO Server..." -ForegroundColor Yellow
Stop-Process -Name "minio" -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "========================================================" -ForegroundColor Green
Write-Host "  DA TAT SACH TOAN BO TIEN TRINH WEBGIS!" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Green
Write-Host ""
