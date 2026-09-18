@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   WebGIS - Cau Hinh Ten Mien seismicatlas.local (Windows)
echo ========================================================
echo.

set "HOSTS_FILE=%SystemRoot%\System32\drivers\etc\hosts"
set "DOMAIN=seismicatlas.local"
set "IP=127.0.0.1"

if not "%1"=="" set "IP=%1"

echo Kiem tra cau hinh trong %HOSTS_FILE%...
findstr /i "%DOMAIN%" "%HOSTS_FILE%" >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Ten mien "%DOMAIN%" da duoc cau hinh truoc do trong tep hosts.
) else (
    echo Dang them "%IP% %DOMAIN%" vao tep hosts...
    echo (Yeu cau quyen Administrator)...
    (
        echo.
        echo # WebGIS Local Domain
        echo %IP% %DOMAIN%
    ) >> "%HOSTS_FILE%" 2>nul

    if %errorlevel% equ 0 (
        echo [THANH CONG] Da them "%IP% %DOMAIN%" vao tep hosts!
    ) else (
        echo [ERROR] Khong co quyen ghi vao tep hosts.
        echo Vui long click chuot phai vao file nay va chon "Run as administrator".
    )
)

echo.
echo Bay gio ban co the truy cap WebGIS bang dia chi:
echo   https://seismicatlas.local
echo.
pause
