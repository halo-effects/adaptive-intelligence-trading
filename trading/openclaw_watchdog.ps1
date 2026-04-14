# OpenClaw Watchdog
# Monitors gateway + trading bots. Restarts any that are down.
# Designed to run as a Scheduled Task every 5 minutes.

$logFile = "$env:USERPROFILE\.openclaw\watchdog.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# ---------- Helper ----------
function Check-Task {
    param(
        [string]$Name,
        [string]$TaskName,
        [string]$StatusFile,
        [int]$StaleMinutes = 120
    )
    
    # First check: is the scheduled task in "Running" state?
    $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if (-not $task) { return }  # Task doesn't exist, skip
    
    if ($task.State -eq "Running") {
        # Task says it's running. Only intervene if status file is VERY stale (2 hours)
        # This catches hung processes that are alive but not processing
        if ($StatusFile -and (Test-Path $StatusFile)) {
            $age = ((Get-Date).ToUniversalTime() - (Get-Item $StatusFile).LastWriteTimeUtc).TotalMinutes
            if ($age -gt $StaleMinutes) {
                Add-Content -Path $logFile -Value "$timestamp - $Name task running but status stale (${age}m > ${StaleMinutes}m), restarting..."
                try {
                    Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
                    Start-Sleep -Seconds 3
                    Start-ScheduledTask -TaskName $TaskName
                    Add-Content -Path $logFile -Value "$timestamp - $Name restarted (was hung)"
                } catch {
                    Add-Content -Path $logFile -Value "$timestamp - ERROR: Failed to restart $Name : $_"
                }
            }
        }
        return  # Task is running and not stale — leave it alone
    }
    
    # Task is NOT running (Ready/Stopped) — restart it
    Add-Content -Path $logFile -Value "$timestamp - $Name task state: $($task.State), restarting..."
    try {
        Start-ScheduledTask -TaskName $TaskName
        Start-Sleep -Seconds 5
        $check = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
        if ($check.State -eq "Running") {
            Add-Content -Path $logFile -Value "$timestamp - $Name restarted successfully"
        } else {
            Add-Content -Path $logFile -Value "$timestamp - WARNING: $Name restart attempted but state is $($check.State)"
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
Check-Task -Name "V14 Paper Bot" -TaskName "V14PaperBot" `
    -StatusFile "$env:USERPROFILE\.openclaw\workspace\trading\spot\paper\v14\status.json" `
    -StaleMinutes 120

# ---------- 3. V14-ETF Paper Bot ----------
Check-Task -Name "V14-ETF Paper Bot" -TaskName "V14ETFPaperBot" `
    -StatusFile "$env:USERPROFILE\.openclaw\workspace\trading\spot\paper\v14etf\status.json" `
    -StaleMinutes 120

# ---------- 4. V14-PM Portfolio Paper Bot ----------
Check-Task -Name "V14-PM Paper Bot" -TaskName "V14PMPaperBot" `
    -StatusFile "$env:USERPROFILE\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json" `
    -StaleMinutes 120

# ---------- 5. V14 Live Bot (Aster - REAL MONEY) ----------
Check-Task -Name "V14 Live Bot (Aster)" -TaskName "V14LiveAster" `
    -StatusFile "$env:USERPROFILE\.openclaw\workspace\trading\spot\live\v14\status.json" `
    -StaleMinutes 120