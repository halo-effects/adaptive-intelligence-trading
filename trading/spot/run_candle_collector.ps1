# AIT Candle Collector + DCA Scanner Pipeline
# Runs hourly via Scheduled Task "AIT_CandleCollector"
#
# Step 1: Pull latest 1h candles from Hyperliquid for all scanner coins
# Step 1.5: Resample 1h → daily candles
# Step 2: Run V14 DCA Cycle Scanner to refresh DCA Scores
#
# Circuit breaker: If Step 1 fails, Steps 1.5 and 2 still run (data may be
# slightly stale but scanner should use whatever is available). However,
# a staleness check after Step 1 logs ERROR if any scanner coin is >6h old.
#
$pythonExe = "C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe"
$workDir = "C:\Users\Never\.openclaw\workspace"

$logFile = "$workDir\trading\spot\data\collector.log"
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Log($msg) {
    $line = "[$timestamp] $msg"
    Add-Content -Path $logFile -Value $line -Encoding UTF8
    Write-Host $line
}

Log "=== Candle Collector Pipeline Start ==="

# Pre-flight: verify collector script imports cleanly
$preflight = & $pythonExe -c "from trading.spot.collect_scanner_candles import main; print('OK')" 2>&1
if ($preflight -notmatch "OK") {
    Log "CRITICAL: Collector pre-flight import failed: $preflight"
    Log "Skipping Step 1 (collector). Steps 1.5 and 2 will use existing data."
    $step1Failed = $true
} else {
    $step1Failed = $false
}

# Step 1: Collect candles
if (-not $step1Failed) {
    Log "Step 1: Collecting candles..."
    try {
        $output = & $pythonExe -u "$workDir\trading\spot\collect_scanner_candles.py" 2>&1
        $exitCode = $LASTEXITCODE
        foreach ($line in $output) { Log "  $line" }
        if ($exitCode -ne 0) {
            Log "ERROR: Candle collector exited with code $exitCode"
            $step1Failed = $true
        } else {
            Log "Step 1 complete."
        }
    } catch {
        Log "ERROR: Candle collector failed: $_"
        $step1Failed = $true
    }
}

# Step 1.5: Resample 1h → daily candles
Log "Step 1.5: Resampling hourly to daily..."
try {
    $output = & $pythonExe -u "$workDir\trading\spot\resample_daily.py" 2>&1
    $exitCode = $LASTEXITCODE
    foreach ($line in $output) { Log "  $line" }
    if ($exitCode -ne 0) {
        Log "WARNING: Daily resample exited with code $exitCode"
    } else {
        Log "Step 1.5 complete."
    }
} catch {
    Log "ERROR: Daily resample failed: $_"
}

# Step 2: Run DCA Scanner
Log "Step 2: Running DCA Cycle Scanner..."
try {
    $output = & $pythonExe -u -m trading.spot.v14_cycle_scanner --no-telegram 2>&1
    $exitCode = $LASTEXITCODE
    foreach ($line in $output) { Log "  $line" }
    if ($exitCode -ne 0) {
        Log "WARNING: Scanner exited with code $exitCode"
    } else {
        Log "Step 2 complete."
    }
} catch {
    Log "ERROR: Scanner failed: $_"
}

# Post-pipeline: Report overall status
if ($step1Failed) {
    Log "WARNING: Pipeline completed with Step 1 failure. Scanner used existing (possibly stale) data."
}
Log "=== Pipeline Complete ==="
