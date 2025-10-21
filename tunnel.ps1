# tunnel.ps1
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8080" -UseBasicParsing
    Write-Host "✅ برنامه در حال اجراست" -ForegroundColor Green
}
catch {
    Write-Host "❌ برنامه اجرا نیست. اول برنامه را اجرا کنید." -ForegroundColor Red
    exit
}

Write-Host "🌐 در حال اتصال به localhost.run..." -ForegroundColor Yellow

# استفاده از netcat اگر موجود باشد
try {
    & ncat --ssl localhost.run 443
}
catch {
    Write-Host "📋 دستور زیر را در سایت localhost.run کپی کنید:" -ForegroundColor Cyan
    Write-Host "ssh -R 80:localhost:8080 nokey@localhost.run" -ForegroundColor White
    Write-Host ""
    Write-Host "🌍 یا از لینک زیر استفاده کنید:" -ForegroundColor Cyan
    Write-Host "https://localhost.run" -ForegroundColor White
}