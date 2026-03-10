# OpenClaw Upgrade Checklist

> **Why this exists:** A previous upgrade wiped memory files and required expensive token-heavy
> recovery loops. This checklist prevents that from happening again.

## Pre-Update (do ALL of these before running `openclaw update`)

### 1. Stop All Bots
```powershell
# Stop PM bot
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "run_v14" } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host "Killed $($_.ProcessId)" }

# Disable scheduled tasks so nothing restarts mid-update
Disable-ScheduledTask -TaskName "V14LiveAster"
Disable-ScheduledTask -TaskName "V14PaperBot"
Disable-ScheduledTask -TaskName "V14ETFPaperBot"
Disable-ScheduledTask -TaskName "V14PMPaperBot"
Disable-ScheduledTask -TaskName "V14CycleScanner"
Disable-ScheduledTask -TaskName "AIT_DashboardSync"
```

### 2. Manual Workspace Backup
```powershell
$date = Get-Date -Format "yyyy-MM-dd_HHmm"
$backupDir = "$env:USERPROFILE\openclaw-backups"
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
Compress-Archive -Path "$env:USERPROFILE\.openclaw\workspace\*" -DestinationPath "$backupDir\workspace_$date.zip" -Force
Write-Host "Workspace backup: $backupDir\workspace_$date.zip"
Write-Host "Size: $((Get-Item "$backupDir\workspace_$date.zip").Length / 1MB) MB"
```

### 3. Backup OpenClaw Config
```powershell
# Try the new backup command first (v2026.3.8+)
openclaw backup create --only-config

# Also manual copy as insurance
Compress-Archive -Path "$env:USERPROFILE\.openclaw\config\*" -DestinationPath "$backupDir\config_$date.zip" -Force -ErrorAction SilentlyContinue
```

### 4. Write Pre-Update Snapshot
Run this and save the output — it's what "normal" looks like:
```powershell
Write-Host "=== OpenClaw Version ==="
openclaw --version

Write-Host "`n=== Scheduled Tasks ==="
Get-ScheduledTask | Where-Object { $_.TaskName -match "V14|AIT|Candle" } | Select-Object TaskName, State | Format-Table

Write-Host "`n=== Cron Jobs ==="
openclaw cron list

Write-Host "`n=== Critical Files (checksums) ==="
foreach ($f in @("MEMORY.md","SOUL.md","USER.md","AGENTS.md","HEARTBEAT.md","TOOLS.md","IDENTITY.md")) {
    $path = "$env:USERPROFILE\.openclaw\workspace\$f"
    if (Test-Path $path) {
        $hash = (Get-FileHash $path -Algorithm MD5).Hash.Substring(0,8)
        $size = (Get-Item $path).Length
        Write-Host "  $f : $hash ($size bytes)"
    } else {
        Write-Host "  $f : MISSING"
    }
}

Write-Host "`n=== Memory Files ==="
Get-ChildItem "$env:USERPROFILE\.openclaw\workspace\memory\*.md" | Select-Object Name, Length, LastWriteTime | Format-Table

Write-Host "`n=== Bot Status Files ==="
foreach ($d in @("trading\spot\live\v14","trading\spot\paper\v14","trading\spot\paper\v14etf","trading\spot\paper\v14_portfolio")) {
    $status = "$env:USERPROFILE\.openclaw\workspace\$d\status.json"
    if (Test-Path $status) {
        $s = Get-Content $status -Raw | ConvertFrom-Json
        Write-Host "  $d : equity=$($s.equity) running=$($s.running)"
    }
}
```

### 5. Verify Backup Integrity
```powershell
# Quick check — can we read critical files from the zip?
$zip = [System.IO.Compression.ZipFile]::OpenRead("$backupDir\workspace_$date.zip")
$critical = @("MEMORY.md","SOUL.md","USER.md","AGENTS.md","HEARTBEAT.md")
foreach ($f in $critical) {
    $entry = $zip.Entries | Where-Object { $_.Name -eq $f }
    if ($entry) { Write-Host "OK: $f ($($entry.Length) bytes)" }
    else { Write-Host "MISSING: $f — ABORT UPDATE" }
}
$zip.Dispose()
```

---

## Run Update

```powershell
openclaw update
# or: npm install -g openclaw@latest
```

---

## Post-Update Verification

### 6. Check Version
```powershell
openclaw --version
openclaw status
```

### 7. Diff Critical Workspace Files
```powershell
# Re-run the checksum block from step 4 and compare
# If ANY critical file changed or is missing → restore from backup immediately
```

### 8. Verify Memory
Start a new session and confirm:
- [ ] Gee Gee knows who it is (IDENTITY.md / SOUL.md intact)
- [ ] Gee Gee knows who Brett is (USER.md intact)
- [ ] MEMORY.md has long-term context
- [ ] AGENTS.md has operating instructions
- [ ] HEARTBEAT.md has bot monitoring config
- [ ] Daily memory files exist in memory/

### 9. Verify Config
```powershell
# Cron jobs still exist?
openclaw cron list

# Gateway running?
openclaw gateway status
```

### 10. Re-enable and Restart Bots
```powershell
# Re-enable scheduled tasks
Enable-ScheduledTask -TaskName "V14LiveAster"
Enable-ScheduledTask -TaskName "V14PaperBot"
Enable-ScheduledTask -TaskName "V14ETFPaperBot"
Enable-ScheduledTask -TaskName "V14PMPaperBot"
Enable-ScheduledTask -TaskName "V14CycleScanner"
Enable-ScheduledTask -TaskName "AIT_DashboardSync"

# Start bots manually (don't wait for scheduled task triggers)
# PM bot — no --fresh unless trade history needs reset
Start-Process -FilePath "C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe" -ArgumentList "-u -m trading.spot.run_v14_portfolio_paper --capital 50000 --profile high --leverage 1.0" -WorkingDirectory "$env:USERPROFILE\.openclaw\workspace" -WindowStyle Hidden

# Verify each bot starts
Start-Sleep 10
Get-WmiObject Win32_Process -Filter "Name='python.exe'" | Where-Object { $_.CommandLine -match "run_v14" } | Select-Object ProcessId, @{N='Bot';E={if($_.CommandLine -match 'portfolio'){'PM'}elseif($_.CommandLine -match 'etf'){'ETF'}elseif($_.CommandLine -match 'live_aster'){'LIVE'}else{'V14'}}} | Format-Table
```

---

## Rollback (if things went wrong)

### Workspace Files Missing/Changed
```powershell
# Extract specific files from backup
$backupZip = Get-ChildItem "$env:USERPROFILE\openclaw-backups\workspace_*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Expand-Archive -Path $backupZip.FullName -DestinationPath "$env:USERPROFILE\.openclaw\workspace" -Force
Write-Host "Restored from $($backupZip.Name)"
```

### Config Lost
```powershell
$configZip = Get-ChildItem "$env:USERPROFILE\openclaw-backups\config_*.zip" | Sort-Object LastWriteTime -Descending | Select-Object -First 1
Expand-Archive -Path $configZip.FullName -DestinationPath "$env:USERPROFILE\.openclaw\config" -Force
openclaw gateway restart
```

### DO NOT
- Loop through memory files trying to reconstruct from fragments (expensive, unreliable)
- Run multiple sessions simultaneously trying to fix things (token burn)
- Start bots before verifying workspace integrity

---

## Notes
- Created: 2026-03-09 after painful v2026.3.2 upgrade experience
- Backup location: `%USERPROFILE%\openclaw-backups\`
- Estimated update time: 5-10 minutes (plus bot restart verification)
- If `openclaw backup create` works reliably, the manual zip steps can be simplified in future
