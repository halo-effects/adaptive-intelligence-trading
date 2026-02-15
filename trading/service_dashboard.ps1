# Dashboard HTTP Server — persistent service wrapper with auto-restart
# Run via Task Scheduler at logon

$ErrorActionPreference = "Continue"
$python = "C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe"
$dashDir = "C:\Users\Never\.openclaw\workspace\trading\live"
$logFile = "$dashDir\dashboard_service.log"

while ($true) {
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content $logFile "$timestamp [START] Dashboard server starting on port 8080..."
    
    try {
        & $python -u -m http.server 8080 --directory $dashDir 2>&1 | Tee-Object -Append $logFile
    } catch {
        Add-Content $logFile "$timestamp [ERROR] $($_.Exception.Message)"
    }
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content $logFile "$timestamp [CRASH] Dashboard exited. Restarting in 5s..."
    Start-Sleep -Seconds 5
}
