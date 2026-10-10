@echo off
chcp 65001 >nul
echo ========================================================
echo   TRADING SYSTEM - PUBLIC INTERNET ACCESS
echo ========================================================
echo.
echo [1] Checking Cloudflare Tunnel status...
docker compose up -d tunnel
echo.
echo [2] Public Internet URL (HTTPS - Truy cap tu bat ky dau):
for /f "tokens=4" %%a in ('docker logs trading_tunnel 2^>^&1 ^| findstr /c:".trycloudflare.com"') do (
    echo    ^>^>^> %%a ^<^<^<
)
echo.
echo [3] Local Network URL (LAN - Cung mang Wi-Fi):
for /f "tokens=4" %%i in ('route print ^| findstr "\<0.0.0.0\>"') do (
    set LOCAL_IP=%%i
    goto :found_ip
)
:found_ip
echo    http://%LOCAL_IP%:3000
echo.
echo ========================================================
pause
