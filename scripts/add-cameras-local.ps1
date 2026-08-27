# 15 ta yakka IP kamerani sbozor'ga (LOKAL, localhost:8080) qurilma sifatida
# qo'shadi va har biriga kashfiyotni boshlaydi. Parol bir marta so'raladi.
#
#   powershell -ExecutionPolicy Bypass -File scripts\add-cameras-local.ps1
#
# Qayta ishga tushirish xavfsiz: allaqachon qo'shilgan manzil (409) o'tkazib
# yuboriladi, kashfiyot esa baribir yangilanadi.

$ErrorActionPreference = "Stop"
$Base = "http://localhost:8080/api/v1"

$Cameras = @(
    "192.168.1.100", "192.168.1.105", "192.168.1.109", "192.168.1.110",
    "192.168.1.113", "192.168.1.115", "192.168.1.116", "192.168.1.117",
    "192.168.1.118", "192.168.1.119", "192.168.1.120", "192.168.1.121",
    "192.168.1.122", "192.168.1.123", "192.168.1.124"
)

$sec = Read-Host "Kameralar paroli (admin foydalanuvchisi uchun)" -AsSecureString
$ptr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
$CamPass = [Runtime.InteropServices.Marshal]::PtrToStringAuto($ptr)
[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)

Write-Host "Kirish (bozor admini +998901000003)..." -ForegroundColor Cyan
$login = Invoke-RestMethod -Uri "$Base/auth/login" -Method Post -ContentType "application/json" `
    -Body (@{ phone = "+998901000003"; password = "Sinov#2026" } | ConvertTo-Json)
$H = @{ Authorization = "Bearer $($login.access_token)" }

$added = 0; $skipped = 0; $failed = 0
foreach ($ip in $Cameras) {
    $body = @{ address = $ip; username = "admin"; password = $CamPass } | ConvertTo-Json
    try {
        $dev = Invoke-RestMethod -Uri "$Base/nvr-devices" -Method Post -Headers $H `
            -ContentType "application/json" -Body $body
        $added++
        Write-Host ("[+] {0} qo'shildi (id={1})" -f $ip, $dev.id) -ForegroundColor Green
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        if ($code -eq 409) {
            $skipped++
            Write-Host "[=] $ip allaqachon bor" -ForegroundColor Yellow
            $all = (Invoke-RestMethod -Uri "$Base/nvr-devices" -Headers $H).items
            $dev = $all | Where-Object { $_.host -eq $ip } | Select-Object -First 1
        } else {
            $failed++
            Write-Host "[x] $ip xato: HTTP $code $($_.ErrorDetails.Message)" -ForegroundColor Red
            continue
        }
    }
    if ($dev -and $dev.id) {
        try {
            Invoke-RestMethod -Uri "$Base/nvr-devices/$($dev.id)/discover" `
                -Method Post -Headers $H -ContentType "application/json" -Body "{}" | Out-Null
            Write-Host "    kashfiyot boshlandi" -ForegroundColor Gray
        } catch {
            Write-Host "    kashfiyot: $($_.ErrorDetails.Message)" -ForegroundColor Yellow
        }
    }
}
$CamPass = $null

Write-Host ""
Write-Host "Qo'shildi: $added, bor edi: $skipped, xato: $failed" -ForegroundColor Cyan
Write-Host "Kashfiyot fonda ishlayapti (~1-2 daqiqa). Kutilmoqda..." -ForegroundColor Cyan
Start-Sleep -Seconds 75

$cams = Invoke-RestMethod -Uri "$Base/cameras" -Headers $H
$n = ($cams | Measure-Object).Count
if ($cams.items) { $n = ($cams.items | Measure-Object).Count }
Write-Host ""
Write-Host "KAMERALAR REESTRIDA: $n ta kamera" -ForegroundColor Green
Write-Host "UI: http://localhost:8080 -> Kameralar bo'limi" -ForegroundColor Green
