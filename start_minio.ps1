$ErrorActionPreference = "Stop"

$RootDir = $PSScriptRoot
$ToolsDir = Join-Path $RootDir "tools\minio"
$MinioExe = Join-Path $ToolsDir "minio.exe"
$DataDir = Join-Path $RootDir "storage\minio_data"

if (!(Test-Path $ToolsDir)) {
    New-Item -ItemType Directory -Force -Path $ToolsDir | Out-Null
}

if (!(Test-Path $DataDir)) {
    New-Item -ItemType Directory -Force -Path $DataDir | Out-Null
}

if (!(Test-Path $MinioExe)) {
    Write-Host "[MinIO] Dang tai minio.exe tu https://dl.min.io ..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri "https://dl.min.io/server/minio/release/windows-amd64/minio.exe" -OutFile $MinioExe
    Write-Host "[MinIO] Da tai minio.exe thanh cong!" -ForegroundColor Green
}

$env:MINIO_ROOT_USER = "minioadmin"
$env:MINIO_ROOT_PASSWORD = "minioadmin"

Write-Host "========================================================" -ForegroundColor Yellow
Write-Host "  MinIO Server dang khoi dong..." -ForegroundColor Yellow
Write-Host "  - S3 API:      http://localhost:9000" -ForegroundColor Cyan
Write-Host "  - Web Console: http://localhost:9001" -ForegroundColor Cyan
Write-Host "  - User:        minioadmin" -ForegroundColor White
Write-Host "  - Password:    minioadmin" -ForegroundColor White
Write-Host "  - Storage Dir: $DataDir" -ForegroundColor Gray
Write-Host "========================================================" -ForegroundColor Yellow

& $MinioExe server $DataDir --address ":9000" --console-address ":9001"
