@echo off
setlocal enabledelayedexpansion

echo ========================================================
echo   WebGIS - Cai Dat Root CA Vao Windows (O Khoa Xanh 100%%)
echo ========================================================
echo.

set "CERT_PATH=%~dp0..\certs\rootCA.crt"

if not exist "%CERT_PATH%" (
    echo [ERROR] Khong tim thay tep Root CA tai: %CERT_PATH%
    echo Vui long chay scripts\generate_ssl_certs.bat truoc.
    pause
    exit /b 1
)

echo Dang cai dat WebGIS Root CA vao "Trusted Root Certification Authorities"...
echo (Yeu cau quyen Administrator - Neu co hop thoai hien len hay chon Yes/Dong y)
echo.

certutil -addstore -f "ROOT" "%CERT_PATH%"

if %errorlevel% equ 0 (
    echo.
    echo ========================================================
    echo   [THANH CONG] Da tin cay WebGIS Root CA!
    echo   Trinh duyet Edge/Chrome se hien thi O KHOA XANH (HTTPS)
    echo   khi truy cap https://seismicatlas.local hoac https://localhost
    echo ========================================================
) else (
    echo.
    echo [ERROR] Cai dat that bai. Vui long click chuot phai vao file nay
    echo va chon "Run as administrator" (Chay duoi quyen Admin).
)

echo.
pause
