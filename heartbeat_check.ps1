$checks = @(
    'trading/spot/live/v14/status.json',
    'trading/spot/paper/v14/status.json',
    'trading/spot/paper/v14etf/status.json',
    'trading/spot/paper/v14_portfolio/status.json'
)

$now = [datetime]::UtcNow
$alerts = @()

foreach ($f in $checks) {
    $p = Join-Path 'C:\Users\Never\.openclaw\workspace' $f
    if (Test-Path $p) {
        $item = Get-Item $p
        $json = Get-Content $p | ConvertFrom-Json
        $age = ($now - $item.LastWriteTimeUtc).TotalMinutes
        
        $botname = $f.Split('/')[-2]
        $running = $json.running
        $equity = $json.equity
        
        Write-Host "$botname`: running=$running, equity=$equity, age=$('{0:F1}' -f $age)min"
        
        if (-not $running) {
            $alerts += "ALERT: $botname NOT RUNNING"
        }
        if ($age -gt 65) {
            $alerts += "ALERT: $botname stale (age: $('{0:F1}' -f $age)min)"
        }
    } else {
        $alerts += "ERROR: $f not found"
    }
}

Write-Host ""
if ($alerts) {
    Write-Host "=== ALERTS ==="
    $alerts | ForEach-Object { Write-Host $_ }
} else {
    Write-Host "All bots healthy."
}
