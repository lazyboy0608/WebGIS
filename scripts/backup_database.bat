@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   WebGIS PostGIS Database Backup Utility
echo ========================================================
echo.

if not exist "%~dp0..\backups" (
    mkdir "%~dp0..\backups"
)

for /f "tokens=2 delims==" %%I in ('wmic os get localdatetime /value') do set datetime=%%I
set TIMESTAMP=%datetime:~0,4%-%datetime:~4,2%-%datetime:~6,2%_%datetime:~8,2%-%datetime:~10,2%-%datetime:~12,2%
set BACKUP_FILE=%~dp0..\backups\webgis_backup_%TIMESTAMP%.sql

echo Backing up PostgreSQL / PostGIS database to:
echo %BACKUP_FILE%
echo.

docker exec webgis-postgis pg_dump -U postgres webgis > "%BACKUP_FILE%"

if %errorlevel% equ 0 (
    echo [SUCCESS] Backup completed successfully!
) else (
    echo [ERROR] Backup failed. Make sure webgis-postgis container is running.
)

echo.
pause
