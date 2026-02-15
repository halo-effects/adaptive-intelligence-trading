# Aster Live Trader Launcher
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONLEGACYWINDOWSSTDIO = "utf-8"

# Read from persistent user env vars (set via setx)
if (-not $env:ASTER_API_KEY) {
    $env:ASTER_API_KEY = [System.Environment]::GetEnvironmentVariable('ASTER_API_KEY', 'User')
}
if (-not $env:ASTER_API_SECRET) {
    $env:ASTER_API_SECRET = [System.Environment]::GetEnvironmentVariable('ASTER_API_SECRET', 'User')
}

if (-not $env:ASTER_API_KEY -or -not $env:ASTER_API_SECRET) {
    Write-Host "ERROR: ASTER_API_KEY and ASTER_API_SECRET not found." -ForegroundColor Red
    exit 1
}

Write-Host "Starting Aster trader... API Key: $($env:ASTER_API_KEY.Substring(0,8))..." -ForegroundColor Green

Set-Location C:\Users\Never\.openclaw\workspace
& C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe -m trading.run_aster
