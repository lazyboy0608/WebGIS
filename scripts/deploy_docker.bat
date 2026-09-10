@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   WebGIS Production Deployment (Docker Multi-Stage)
echo ========================================================
echo.

:: 1. Check Docker status
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker daemon is not running!
    echo Please start Docker Desktop or Docker service first.
    pause
    exit /b 1
)

:: 2. Build and Start All Services
echo [1/3] Building and starting all Docker containers...
docker compose up -d --build --remove-orphans

if %errorlevel% neq 0 (
    echo [ERROR] Failed to start Docker containers.
    pause
    exit /b 1
)

:: 3. Run Database Migrations
echo.
echo [2/3] Waiting for database to be ready and running Alembic migrations...
timeout /t 5 /nobreak >nul
docker compose exec -T data-serving alembic upgrade head

:: 4. Get Host IP for LAN
echo.
echo [3/3] System successfully started!
echo ========================================================
echo   WebGIS Web Server is running on Port 80!
echo.
echo   Local Access:      http://localhost
echo   LAN Access:        http://<YOUR_LAN_IP>
echo ========================================================
echo.
pause
