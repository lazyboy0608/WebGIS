# PowerShell script to start Redis for WebGIS Platform
$ErrorActionPreference = "Continue"

$RedisDir = Join-Path $PSScriptRoot "tools\redis"
$RedisExe = Join-Path $RedisDir "redis-server.exe"
$RedisConf = Join-Path $RedisDir "redis.windows.conf"
$RedisData = Join-Path $PSScriptRoot "storage\redis_data"

if (!(Test-Path $RedisDir)) { New-Item -ItemType Directory -Path $RedisDir -Force | Out-Null }
if (!(Test-Path $RedisData)) { New-Item -ItemType Directory -Path $RedisData -Force | Out-Null }

# Download portable standalone Windows Redis if not found
if (!(Test-Path $RedisExe)) {
    Write-Host "[Redis] Dang tai Redis for Windows tu GitHub..." -ForegroundColor Yellow
    $zipPath = Join-Path $RedisDir "redis.zip"
    Invoke-WebRequest -Uri "https://github.com/tporadowski/redis/releases/download/v5.0.14.1/Redis-x64-5.0.14.1.zip" -OutFile $zipPath
    Expand-Archive -Path $zipPath -DestinationPath $RedisDir -Force
    Remove-Item $zipPath -Force
    Write-Host "[Redis] Tai thanh cong!" -ForegroundColor Green
}

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  WebGIS Redis Server dang khoi dong..." -ForegroundColor Green
Write-Host "  - Port:        6379" -ForegroundColor Yellow
Write-Host "  - Executable:  $RedisExe" -ForegroundColor Yellow
Write-Host "  - Storage:     $RedisData" -ForegroundColor Yellow
Write-Host "  - Max Memory:  2GB (allkeys-lru)" -ForegroundColor Yellow
Write-Host "========================================================" -ForegroundColor Cyan

& "$RedisExe" "$RedisConf" --dir "$RedisData" --maxmemory 2gb --maxmemory-policy allkeys-lru
