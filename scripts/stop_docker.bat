@echo off
echo ========================================================
echo   WebGIS - Stopping all services...
echo ========================================================
echo.

docker compose down

echo.
echo [DONE] All WebGIS services have been stopped safely.
echo.
pause
