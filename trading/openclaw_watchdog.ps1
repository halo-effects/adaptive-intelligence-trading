# OpenClaw Gateway Watchdog
# Checks if the gateway is running; restarts if not.
# Designed to run as a Scheduled Task every 5 minutes.

$logFile = "$env:USERPROFILE\.openclaw\watchdog.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# Check if openclaw gateway is running (node process with "openclaw" in command line)
$gateway = Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -like '*openclaw*gateway*' }

if ($gateway) {
    # Running fine, no action needed
    exit 0
}

# Not running — restart it
Add-Content -Path $logFile -Value "$timestamp - Gateway not found, restarting..."

try {
    Start-Process -FilePath "openclaw" -ArgumentList "gateway","start" -WindowStyle Hidden -PassThru | Out-Null
    Start-Sleep -Seconds 5
    
    # Verify it came back
    $check = Get-CimInstance Win32_Process -Filter "Name='node.exe'" | Where-Object { $_.CommandLine -like '*openclaw*gateway*' }
    if ($check) {
        Add-Content -Path $logFile -Value "$timestamp - Gateway restarted successfully (PID: $($check.ProcessId))"
    } else {
        Add-Content -Path $logFile -Value "$timestamp - WARNING: Gateway restart attempted but process not found"
    }
} catch {
    Add-Content -Path $logFile -Value "$timestamp - ERROR: Failed to restart gateway: $_"
}
