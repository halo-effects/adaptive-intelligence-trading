# bot_watchdog.ps1 - zero-LLM watchdog. Prints NOTHING when healthy.
# Only emits text when a bot is down AND self-restart failed -> that text becomes the alert.
$ErrorActionPreference = 'SilentlyContinue'
$ws = Split-Path $PSScriptRoot -Parent
$stateFile = Join-Path $ws 'memory\watchdog-state.json'

$bots = @(
  @{ Name='V14PMLiveAster'; Status='trading\spot\live\v14pm\status.json';          Task='V14PMLiveAster' },
  @{ Name='V14PMPaper';     Status='trading\spot\paper\v14_portfolio\status.json'; Task='V14PMPaperBot'  },
  @{ Name='V14Paper';       Status='trading\spot\paper\v14\status.json';           Task='V14PaperBot'    },
  @{ Name='V14ETFPaper';    Status='trading\spot\paper\v14etf\status.json';        Task='V14ETFPaperBot' }
)

$alerts = @()
$now = Get-Date

foreach ($b in $bots) {
  $p = Join-Path $ws $b.Status
  $stale = $true
  if (Test-Path $p) {
    $age = (New-TimeSpan -Start (Get-Item $p).LastWriteTime -End $now).TotalMinutes
    $stale = $age -gt 65
  } else { $age = -1 }

  if (-not $stale) { continue }

  # Attempt one silent self-heal.
  Start-ScheduledTask -TaskName $b.Task -ErrorAction SilentlyContinue
  Start-Sleep -Seconds 45

  $healed = $false
  if (Test-Path $p) {
    $age2 = (New-TimeSpan -Start (Get-Item $p).LastWriteTime -End (Get-Date)).TotalMinutes
    $healed = $age2 -le 65
  }
  if (-not $healed) {
    $t = Get-ScheduledTask -TaskName $b.Task -ErrorAction SilentlyContinue
    $st = if ($t) { $t.State } else { 'NO-TASK' }
    $ageTxt = if ($age -lt 0) { 'no status.json' } else { "{0:N0} min stale" -f $age }
    $alerts += "$($b.Name): $ageTxt, task=$st, restart FAILED"
  }
}

# --- Scanner health (staleness + corruption) ---
# Scanner output feeds the bots' allocation decisions, so we validate STRUCTURE,
# not just existence. A truncated/half-written or empty file is treated as unhealthy.
function Test-ScannerHealthy {
  param([string]$Path, [int]$MaxAgeMin = 90)
  if (-not (Test-Path $Path)) { return @{ ok=$false; why='missing' } }
  $age = (New-TimeSpan -Start (Get-Item $Path).LastWriteTime -End (Get-Date)).TotalMinutes
  if ($age -gt $MaxAgeMin) { return @{ ok=$false; why=("{0:N0} min stale" -f $age) } }
  try {
    $j = Get-Content $Path -Raw -ErrorAction Stop | ConvertFrom-Json -ErrorAction Stop
  } catch { return @{ ok=$false; why='invalid JSON (corrupt/truncated)' } }
  if (-not $j.generated_at) { return @{ ok=$false; why='no generated_at' } }
  $tsCount = @($j.trend_scores.PSObject.Properties).Count
  $winCount = @($j.windows).Count
  $scanned = [int]($j.coins_scanned)
  if ($winCount -lt 1)   { return @{ ok=$false; why='no windows' } }
  if ($tsCount -lt 20)   { return @{ ok=$false; why="trend_scores thin ($tsCount)" } }
  if ($scanned -lt 20)   { return @{ ok=$false; why="coins_scanned low ($scanned)" } }
  return @{ ok=$true; why='' }
}

$scanPath = Join-Path $ws 'docs\data\v14\cycle_scanner.json'
$scanHealth = Test-ScannerHealthy -Path $scanPath
if (-not $scanHealth.ok) {
  # Attempt one silent self-heal: re-run the scanner, then re-validate.
  $py = 'C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe'
  try {
    Start-Process -FilePath $py -ArgumentList '-u','-m','trading.spot.v14_cycle_scanner' `
      -WorkingDirectory $ws -WindowStyle Hidden -Wait -ErrorAction SilentlyContinue
  } catch {}
  Start-Sleep -Seconds 5
  $scanHealth2 = Test-ScannerHealthy -Path $scanPath
  if (-not $scanHealth2.ok) {
    $alerts += "V14CycleScanner: scanner data unhealthy ($($scanHealth.why)), re-run FAILED ($($scanHealth2.why))"
  }
}

if ($alerts.Count -gt 0) {
  # Suppress repeat alerts for the same bot set within 6h.
  $sig = ($alerts | Sort-Object) -join '|'
  $prev = if (Test-Path $stateFile) { Get-Content $stateFile -Raw | ConvertFrom-Json } else { $null }
  $repeat = $prev -and $prev.sig -eq $sig -and ((New-TimeSpan -Start ([datetime]$prev.ts) -End $now).TotalHours -lt 6)
  New-Item -ItemType Directory -Force -Path (Split-Path $stateFile) | Out-Null
  @{ sig = $sig; ts = $now.ToString('o') } | ConvertTo-Json | Set-Content $stateFile
  if (-not $repeat) {
    "BOT DOWN - self-restart failed:"
    $alerts | ForEach-Object { "  - $_" }
  }
}
