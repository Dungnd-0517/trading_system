Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  TRADING SYSTEM - PUBLIC INTERNET ACCESS" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1] Kiem tra container Cloudflare Tunnel..." -ForegroundColor Yellow
docker compose up -d tunnel | Out-Null

Write-Host "[2] Public Internet URL (HTTPS - Truy cap tu bat ky dau):" -ForegroundColor Green
$log = docker logs trading_tunnel 2>&1
$url = ($log | Select-String -Pattern 'https://[a-zA-Z0-9-]+\.trycloudflare\.com' | Select-Object -Last 1).Matches.Value
if ($url) {
    Write-Host "   >>> $url <<<" -ForegroundColor Green -BackgroundColor DarkGreen
} else {
    Write-Host "   Dang khoi tao tunnel, vui long chay lai sau vai giay..." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3] Local Network URL (LAN - May cung mang Wi-Fi):" -ForegroundColor Cyan
$ip = (Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias 'Wi-Fi*' -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notlike '169.*' }).IPAddress
if (-not $ip) {
    $ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -like '192.168.*' -or $_.IPAddress -like '172.*' -or $_.IPAddress -like '10.*' } | Select-Object -First 1).IPAddress
}
Write-Host "   http://${ip}:3000" -ForegroundColor Cyan

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
