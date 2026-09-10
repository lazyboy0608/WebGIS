@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   WebGIS PostGIS Database Restore Utility
echo ========================================================
echo.

if "%~1"=="" (
    echo Usage: Drag and drop a .sql backup file onto this script.
    echo Or run: restore_database.bat path\to\backup_file.sql
    echo.
    pause
    exit /b 1
)

set BACKUP_FILE=%~1

if not exist "%BACKUP_FILE%" (
    echo [ERROR] Backup file does not exist: %BACKUP_FILE%
    pause
    exit /b 1
)

echo WARNING: This will overwrite existing data in webgis database!
set /p CONFIRM="Are you sure you want to proceed? (Y/N): "
if /i not "%CONFIRM%"=="Y" (
    echo Restore cancelled.
    pause
    exit /b 0
)

echo.
echo Restoring database from %BACKUP_FILE%...
docker exec -i webgis-postgis psql -U postgres -d webgis < "%BACKUP_FILE%"

if %errorlevel% equ 0 (
    echo [SUCCESS] Database restored successfully!
) else (
    echo [ERROR] Restore failed.
)

echo.
pause
