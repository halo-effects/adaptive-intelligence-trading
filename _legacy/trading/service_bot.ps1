# Aster Trading Bot — persistent service wrapper with auto-restart
# Run via Task Scheduler at logon

$ErrorActionPreference = "Continue"
$env:PYTHONIOENCODING = "utf-8"

# Read API keys from registry (set via setx)
if (-not $env:ASTER_API_KEY) {
    $env:ASTER_API_KEY = [System.Environment]::GetEnvironmentVariable('ASTER_API_KEY', 'User')
}
if (-not $env:ASTER_API_SECRET) {
    $env:ASTER_API_SECRET = [System.Environment]::GetEnvironmentVariable('ASTER_API_SECRET', 'User')
}

$python = "C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe"
$workdir = "C:\Users\Never\.openclaw\workspace"
$logFile = "$workdir\trading\live\bot_service.log"

Set-Location $workdir

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content $logFile "$timestamp [START] Bot starting..."
    
    try {
        & $python -u -m trading.run_aster 2>&1 | Tee-Object -Append $logFile
    } catch {
        Add-Content $logFile "$timestamp [ERROR] $($_.Exception.Message)"
    }
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content $logFile "$timestamp [CRASH] Bot exited. Restarting in 10s..."
    Start-Sleep -Seconds 10
}
