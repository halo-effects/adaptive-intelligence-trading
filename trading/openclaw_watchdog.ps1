# OpenClaw Watchdog
# Monitors gateway + trading bots. Restarts any that are down.
# Designed to run as a Scheduled Task every 5 minutes.

$logFile = "$env:USERPROFILE\.openclaw\watchdog.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# ---------- Helper ----------
function Check-And-Restart {
    param(
        [string]$Name,
        [string]$TaskName,
        [scriptblock]$IsRunning
    )
    
    $running = & $IsRunning
    if ($running) { return }
    
    Add-Content -Path $logFile -Value "$timestamp - $Name not found, restarting task '$TaskName'..."
    
    try {
        # Stop first in case it's in a bad state
        Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 5
        
        $check = & $IsRunning
        if ($check) {
            Add-Content -Path $logFile -Value "$timestamp - $Name restarted successfully via '$TaskName'"
        } else {
            Add-Content -Path $logFile -Value "$timestamp - WARNING: $Name restart attempted but still not detected"
        }
    } catch {
        Add-Content -Path $logFile -Value "$timestamp - ERROR: Failed to restart $Name : $_"
    }
}

# ---------- 1. OpenClaw Gateway ----------
$gwRunning = Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
    Where-Object { $_.CommandLine -like '*openclaw*gateway*' }

if (-not $gwRunning) {
    Add-Content -Path $logFile -Value "$timestamp - Gateway not found, restarting..."
    try {
        Start-Process -FilePath "openclaw" -ArgumentList "gateway","start" -WindowStyle Hidden -PassThru | Out-Null
        Start-Sleep -Seconds 5
        $check = Get-CimInstance Win32_Process -Filter "Name='node.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like '*openclaw*gateway*' }
        if ($check) {
            Add-Content -Path $logFile -Value "$timestamp - Gateway restarted successfully (PID: $($check.ProcessId))"
        } else {
            Add-Content -Path $logFile -Value "$timestamp - WARNING: Gateway restart attempted but process not found"
        }
    } catch {
        Add-Content -Path $logFile -Value "$timestamp - ERROR: Failed to restart gateway: $_"
    }
}

# ---------- 2. V14 Paper Bot ----------
Check-And-Restart -Name "V14 Paper Bot" -TaskName "V14PaperBot" -IsRunning {
    $statusFile = "$env:USERPROFILE\.openclaw\workspace\trading\spot\paper\v14\status.json"
    if (-not (Test-Path $statusFile)) { return $false }
    $age = ((Get-Date).ToUniversalTime() - (Get-Item $statusFile).LastWriteTimeUtc).TotalMinutes
    # If status.json hasn't been written in 65 min, consider it dead
    return ($age -lt 65)
}

# ---------- 3. V14-ETF Paper Bot ----------
Check-And-Restart -Name "V14-ETF Paper Bot" -TaskName "V14ETFPaperBot" -IsRunning {
    $statusFile = "$env:USERPROFILE\.openclaw\workspace\trading\spot\paper\v14etf\status.json"
    if (-not (Test-Path $statusFile)) { return $false }
    $age = ((Get-Date).ToUniversalTime() - (Get-Item $statusFile).LastWriteTimeUtc).TotalMinutes
    # If status.json hasn't been written in 65 min, consider it dead
    return ($age -lt 65)
}
