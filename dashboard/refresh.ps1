# Security Dashboard Generator
# Collects system security data and outputs a self-contained HTML dashboard
# Usage: .\refresh.ps1 > security.html

$ErrorActionPreference = 'SilentlyContinue'
$timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

# ── 1. System Overview ──
$os = Get-CimInstance Win32_OperatingSystem
$cs = Get-CimInstance Win32_ComputerSystem
$hostname = $env:COMPUTERNAME
$osVersion = "$($os.Caption) (Build $($os.BuildNumber))"
$lastBoot = $os.LastBootUpTime.ToString("yyyy-MM-dd HH:mm:ss")
$uptime = (New-TimeSpan -Start $os.LastBootUpTime -End (Get-Date))
$uptimeStr = "{0}d {1}h {2}m" -f $uptime.Days, $uptime.Hours, $uptime.Minutes

# ── 2. Resources ──
$cpuLoad = [math]::Round((Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average, 1)
$ramTotal = [math]::Round($os.TotalVisibleMemorySize / 1MB, 1)
$ramFree = [math]::Round($os.FreePhysicalMemory / 1MB, 1)
$ramUsed = [math]::Round($ramTotal - $ramFree, 1)
$ramPct = [math]::Round(($ramUsed / $ramTotal) * 100, 1)
$disk = Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'"
$diskTotal = [math]::Round($disk.Size / 1GB, 1)
$diskFree = [math]::Round($disk.FreeSpace / 1GB, 1)
$diskUsed = [math]::Round($diskTotal - $diskFree, 1)
$diskPct = [math]::Round(($diskUsed / $diskTotal) * 100, 1)

# ── 3. Network ──
$adapter = Get-NetAdapter | Where-Object { $_.Status -eq 'Up' } | Select-Object -First 1
$adapterName = if ($adapter) { $adapter.Name } else { "None" }
$adapterType = if ($adapter) { $adapter.InterfaceDescription } else { "N/A" }
$ipConfig = Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue | Select-Object -First 1
$ipAddr = if ($ipConfig) { $ipConfig.IPAddress } else { "N/A" }
$gateway = (Get-NetRoute -InterfaceIndex $adapter.ifIndex -DestinationPrefix '0.0.0.0/0' -ErrorAction SilentlyContinue).NextHop
if (-not $gateway) { $gateway = "N/A" }
$dns = (Get-DnsClientServerAddress -InterfaceIndex $adapter.ifIndex -AddressFamily IPv4 -ErrorAction SilentlyContinue).ServerAddresses -join ", "
if (-not $dns) { $dns = "N/A" }
# WiFi signal
$wifiSignal = "N/A"
try {
    $wlanOutput = netsh wlan show interfaces 2>&1
    $sigLine = $wlanOutput | Select-String "Signal"
    if ($sigLine) { $wifiSignal = ($sigLine -split ":\s*")[1].Trim() }
} catch {}

# ── 4. Open Ports ──
$listeners = Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Sort-Object LocalPort
$portsHtml = ""
foreach ($l in $listeners) {
    $proc = Get-Process -Id $l.OwningProcess -ErrorAction SilentlyContinue
    $pname = if ($proc) { $proc.ProcessName } else { "Unknown" }
    $portsHtml += "<tr><td>$($l.LocalPort)</td><td>$($l.LocalAddress)</td><td>$pname</td><td>$($l.OwningProcess)</td></tr>`n"
}

# ── 5. Active Connections (top 20 by process) ──
$conns = Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue
$connGroups = $conns | Group-Object OwningProcess | Sort-Object Count -Descending | Select-Object -First 20
$connsHtml = ""
foreach ($g in $connGroups) {
    $proc = Get-Process -Id $g.Name -ErrorAction SilentlyContinue
    $pname = if ($proc) { $proc.ProcessName } else { "PID $($g.Name)" }
    $remotes = ($g.Group | ForEach-Object { "$($_.RemoteAddress):$($_.RemotePort)" } | Select-Object -Unique | Select-Object -First 5) -join ", "
    $connsHtml += "<tr><td>$pname</td><td>$($g.Count)</td><td class='mono small'>$remotes</td></tr>`n"
}

# ── 6. Running Services ──
$services = Get-Service | Where-Object { $_.Status -eq 'Running' }
$svcCount = $services.Count
$suspiciousSvcKeywords = @('vnc','teamviewer','anydesk','logmein','bomgar','screenconnect','meshagent','remote\s*desktop','remote\s*access','radmin','rustdesk','splashtop','connectwise')
$safeSvcNames = @('RasMan','RpcSs','RpcEptMapper','RpcLocator','RemoteRegistry','SessionEnv','TermService','UmRdpService','WinRM')
$suspiciousSvcs = $services | Where-Object {
    if ($safeSvcNames -contains $_.Name) { return $false }
    $name = $_.Name.ToLower() + " " + $_.DisplayName.ToLower()
    foreach ($kw in $suspiciousSvcKeywords) { if ($name -match $kw) { return $true } }
    return $false
}
$svcsHtml = ""
foreach ($s in $suspiciousSvcs) {
    $svcsHtml += "<tr class='warn-row'><td>$($s.Name)</td><td>$($s.DisplayName)</td><td>Running</td></tr>`n"
}

# ── 7. Security Status ──
$defender = Get-MpComputerStatus -ErrorAction SilentlyContinue
$avEnabled = if ($defender.AntivirusEnabled) { "Enabled" } else { "Disabled" }
$rtProtection = if ($defender.RealTimeProtectionEnabled) { "Enabled" } else { "Disabled" }
$lastScan = if ($defender.QuickScanEndTime) { $defender.QuickScanEndTime.ToString("yyyy-MM-dd HH:mm") } else { "Never" }
$lastFullScan = if ($defender.FullScanEndTime) { $defender.FullScanEndTime.ToString("yyyy-MM-dd HH:mm") } else { "Never" }
$defStatus = if ($defender.AntivirusEnabled -and $defender.RealTimeProtectionEnabled) { "good" } elseif ($defender.AntivirusEnabled) { "warn" } else { "alert" }

$firewalls = Get-NetFirewallProfile -ErrorAction SilentlyContinue
$fwHtml = ""
$fwAllGood = $true
foreach ($fw in $firewalls) {
    $st = if ($fw.Enabled) { "Enabled" } else { "Disabled" }
    $cls = if ($fw.Enabled) { "good" } else { "alert" }
    if (-not $fw.Enabled) { $fwAllGood = $false }
    $fwHtml += "<span class='badge badge-$cls'>$($fw.Name): $st</span> "
}

# ── 8. Recent Logins ──
$loginEvents = Get-WinEvent -FilterHashtable @{LogName='Security'; Id=4624} -MaxEvents 20 -ErrorAction SilentlyContinue |
    Where-Object { $_.Properties[8].Value -in @(2,10,11) } | Select-Object -First 10
$loginsHtml = ""
foreach ($evt in $loginEvents) {
    $logonType = switch ($evt.Properties[8].Value) { 2 {"Interactive"} 10 {"RemoteInteractive"} 11 {"CachedInteractive"} default {"Type $($evt.Properties[8].Value)"} }
    $user = "$($evt.Properties[6].Value)\$($evt.Properties[5].Value)"
    $time = $evt.TimeCreated.ToString("yyyy-MM-dd HH:mm:ss")
    $cls = if ($evt.Properties[8].Value -eq 10) { "class='warn-row'" } else { "" }
    $loginsHtml += "<tr $cls><td>$time</td><td>$user</td><td>$logonType</td></tr>`n"
}
if (-not $loginsHtml) { $loginsHtml = "<tr><td colspan='3'>No recent login events (may require elevation)</td></tr>" }

# ── 9. Startup Programs ──
$startupPaths = @(
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
    'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\Run',
    'HKCU:\SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce'
)
$startupHtml = ""
foreach ($path in $startupPaths) {
    $items = Get-ItemProperty -Path $path -ErrorAction SilentlyContinue
    if ($items) {
        $props = $items.PSObject.Properties | Where-Object { $_.Name -notin @('PSPath','PSParentPath','PSChildName','PSProvider','PSDrive') }
        foreach ($p in $props) {
            $hive = if ($path -match 'HKLM') { "HKLM" } else { "HKCU" }
            $startupHtml += "<tr><td>$($p.Name)</td><td class='mono small'>$([System.Web.HttpUtility]::HtmlEncode($p.Value))</td><td>$hive</td></tr>`n"
        }
    }
}
if (-not $startupHtml) { $startupHtml = "<tr><td colspan='3'>None found</td></tr>" }

# ── 10. Suspicious Processes ──
$allProcs = Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.Id -ne 0 }
# High CPU (approximation via TotalProcessorTime)
$highRamProcs = $allProcs | Sort-Object WorkingSet64 -Descending | Select-Object -First 10
$suspProcHtml = ""
foreach ($p in $highRamProcs) {
    $ramMB = [math]::Round($p.WorkingSet64 / 1MB, 0)
    $cls = if ($ramMB -gt 500) { "class='warn-row'" } else { "" }
    $suspProcHtml += "<tr $cls><td>$($p.ProcessName)</td><td>$($p.Id)</td><td>$ramMB MB</td></tr>`n"
}

# ── 11. Gateway Status ──
$nodeProc = Get-Process -Name "node" -ErrorAction SilentlyContinue | Select-Object -First 1
$gatewayRunning = if ($nodeProc) { "Running" } else { "Not Found" }
$gatewayStatus = if ($nodeProc) { "good" } else { "alert" }
$gatewayRam = if ($nodeProc) { "$([math]::Round($nodeProc.WorkingSet64 / 1MB, 0)) MB" } else { "N/A" }
# Check for openclaw specifically
$oclawProc = Get-Process -Name "openclaw*" -ErrorAction SilentlyContinue
if ($oclawProc) {
    $gatewayRunning = "Running (openclaw)"
    $gatewayStatus = "good"
    $gatewayRam = "$([math]::Round($oclawProc[0].WorkingSet64 / 1MB, 0)) MB"
}

# ── 12. Scheduled Tasks ──
$tasks = Get-ScheduledTask -ErrorAction SilentlyContinue | Where-Object {
    $_.State -eq 'Ready' -and $_.Author -and $_.Author -notmatch 'Microsoft' -and $_.Author -notmatch '^\$\(' -and $_.Author -notmatch '%SystemRoot%' -and $_.Author -notmatch '%systemRoot%' -and $_.Author -notmatch '%systemroot%'
}
$tasksHtml = ""
foreach ($t in $tasks) {
    $tasksHtml += "<tr><td>$($t.TaskName)</td><td>$($t.Author)</td><td>$($t.TaskPath)</td></tr>`n"
}
if (-not $tasksHtml) { $tasksHtml = "<tr><td colspan='3'>None found</td></tr>" }

# ── Severity calculations ──
$cpuClass = if ($cpuLoad -gt 90) { "alert" } elseif ($cpuLoad -gt 70) { "warn" } else { "good" }
$ramClass = if ($ramPct -gt 90) { "alert" } elseif ($ramPct -gt 75) { "warn" } else { "good" }
$diskClass = if ($diskPct -gt 90) { "alert" } elseif ($diskPct -gt 80) { "warn" } else { "good" }

# Count issues for summary
$issues = 0
$warnings = 0
if (-not $defender.RealTimeProtectionEnabled) { $issues++ }
if (-not $fwAllGood) { $issues++ }
if ($suspiciousSvcs.Count -gt 0) { $warnings += $suspiciousSvcs.Count }
if ($cpuLoad -gt 90) { $issues++ } elseif ($cpuLoad -gt 70) { $warnings++ }
if ($ramPct -gt 90) { $issues++ } elseif ($ramPct -gt 75) { $warnings++ }
$overallClass = if ($issues -gt 0) { "alert" } elseif ($warnings -gt 0) { "warn" } else { "good" }
$overallText = if ($issues -gt 0) { "$issues ALERT(S)" } elseif ($warnings -gt 0) { "$warnings WARNING(S)" } else { "ALL CLEAR" }

# ── Generate HTML ──
Add-Type -AssemblyName System.Web

$html = @"
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Security Dashboard — $hostname</title>
<style>
  :root {
    --bg: #0d1117; --card: #161b22; --border: #30363d; --text: #e6edf3;
    --text-dim: #8b949e; --green: #3fb950; --amber: #d29922; --red: #f85149;
    --blue: #58a6ff; --purple: #bc8cff;
  }
  * { margin:0; padding:0; box-sizing:border-box; }
  body { background:var(--bg); color:var(--text); font-family:'Segoe UI',system-ui,-apple-system,sans-serif; padding:20px; min-height:100vh; }
  .header { display:flex; justify-content:space-between; align-items:center; padding:16px 24px; background:var(--card); border:1px solid var(--border); border-radius:12px; margin-bottom:20px; }
  .header h1 { font-size:1.4rem; font-weight:600; display:flex; align-items:center; gap:10px; }
  .header h1::before { content:''; }
  .header .meta { text-align:right; font-size:0.85rem; color:var(--text-dim); }
  .status-banner { padding:12px 24px; border-radius:10px; margin-bottom:20px; font-weight:600; font-size:1.1rem; text-align:center; letter-spacing:0.5px; }
  .status-banner.good { background:rgba(63,185,80,0.15); border:1px solid var(--green); color:var(--green); }
  .status-banner.warn { background:rgba(210,153,34,0.15); border:1px solid var(--amber); color:var(--amber); }
  .status-banner.alert { background:rgba(248,81,73,0.15); border:1px solid var(--red); color:var(--red); }
  .grid { display:grid; grid-template-columns:repeat(auto-fit, minmax(420px, 1fr)); gap:16px; }
  .card { background:var(--card); border:1px solid var(--border); border-radius:10px; padding:20px; overflow:hidden; }
  .card h2 { font-size:0.95rem; font-weight:600; color:var(--blue); margin-bottom:14px; text-transform:uppercase; letter-spacing:1px; display:flex; align-items:center; gap:8px; }
  .card h2 .icon { font-size:1.1rem; }
  .kv { display:grid; grid-template-columns:140px 1fr; gap:6px 12px; font-size:0.9rem; }
  .kv .label { color:var(--text-dim); }
  .kv .value { font-weight:500; }
  table { width:100%; border-collapse:collapse; font-size:0.82rem; }
  th { text-align:left; color:var(--text-dim); font-weight:500; padding:6px 8px; border-bottom:1px solid var(--border); font-size:0.78rem; text-transform:uppercase; letter-spacing:0.5px; }
  td { padding:5px 8px; border-bottom:1px solid rgba(48,54,61,0.5); }
  tr:hover { background:rgba(88,166,255,0.04); }
  .warn-row { background:rgba(210,153,34,0.08); }
  .warn-row td { color:var(--amber); }
  .badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:0.8rem; font-weight:600; }
  .badge-good { background:rgba(63,185,80,0.15); color:var(--green); }
  .badge-warn { background:rgba(210,153,34,0.15); color:var(--amber); }
  .badge-alert { background:rgba(248,81,73,0.15); color:var(--red); }
  .meter { height:6px; background:var(--border); border-radius:3px; overflow:hidden; margin-top:4px; }
  .meter-fill { height:100%; border-radius:3px; transition:width 0.3s; }
  .meter-fill.good { background:var(--green); }
  .meter-fill.warn { background:var(--amber); }
  .meter-fill.alert { background:var(--red); }
  .mono { font-family:'Cascadia Code','Fira Code',monospace; }
  .small { font-size:0.78rem; }
  .card.full-width { grid-column: 1 / -1; }
  .resource-grid { display:grid; grid-template-columns:repeat(3, 1fr); gap:16px; }
  .resource-item { text-align:center; }
  .resource-item .big { font-size:2rem; font-weight:700; }
  .resource-item .sub { font-size:0.8rem; color:var(--text-dim); margin-top:2px; }
  .scrollable { max-height:320px; overflow-y:auto; }
  .scrollable::-webkit-scrollbar { width:6px; }
  .scrollable::-webkit-scrollbar-track { background:var(--bg); }
  .scrollable::-webkit-scrollbar-thumb { background:var(--border); border-radius:3px; }
  @media (max-width:900px) { .grid { grid-template-columns:1fr; } .resource-grid { grid-template-columns:1fr; } }
</style>
</head>
<body>

<div class="header">
  <h1>Security Dashboard</h1>
  <div class="meta">
    <div><strong>$hostname</strong></div>
    <div>Last refresh: $timestamp</div>
  </div>
</div>

<div class="status-banner $overallClass">&#x2B24; SYSTEM STATUS: $overallText</div>

<div class="grid">

<!-- System Overview -->
<div class="card">
  <h2>💻 System Overview</h2>
  <div class="kv">
    <span class="label">Hostname</span><span class="value">$hostname</span>
    <span class="label">OS</span><span class="value">$osVersion</span>
    <span class="label">Last Boot</span><span class="value">$lastBoot</span>
    <span class="label">Uptime</span><span class="value">$uptimeStr</span>
  </div>
</div>

<!-- Resources -->
<div class="card">
  <h2><span class="icon">📊</span> Resources</h2>
  <div class="resource-grid">
    <div class="resource-item">
      <div class="big $cpuClass" style="color:var(--$cpuClass)">${cpuLoad}%</div>
      <div class="sub">CPU</div>
      <div class="meter"><div class="meter-fill $cpuClass" style="width:${cpuLoad}%"></div></div>
    </div>
    <div class="resource-item">
      <div class="big $ramClass" style="color:var(--$ramClass)">${ramPct}%</div>
      <div class="sub">RAM ${ramUsed}/${ramTotal} GB</div>
      <div class="meter"><div class="meter-fill $ramClass" style="width:${ramPct}%"></div></div>
    </div>
    <div class="resource-item">
      <div class="big $diskClass" style="color:var(--$diskClass)">${diskPct}%</div>
      <div class="sub">Disk ${diskUsed}/${diskTotal} GB</div>
      <div class="meter"><div class="meter-fill $diskClass" style="width:${diskPct}%"></div></div>
    </div>
  </div>
</div>

<!-- Network -->
<div class="card">
  <h2><span class="icon">🌐</span> Network</h2>
  <div class="kv">
    <span class="label">Adapter</span><span class="value">$adapterName</span>
    <span class="label">Description</span><span class="value">$adapterType</span>
    <span class="label">IP Address</span><span class="value mono">$ipAddr</span>
    <span class="label">Gateway</span><span class="value mono">$gateway</span>
    <span class="label">DNS</span><span class="value mono">$dns</span>
    <span class="label">WiFi Signal</span><span class="value">$wifiSignal</span>
  </div>
</div>

<!-- Security Status -->
<div class="card">
  <h2><span class="icon">🔒</span> Security Status</h2>
  <div class="kv">
    <span class="label">Antivirus</span><span class="value"><span class="badge badge-$defStatus">$avEnabled</span></span>
    <span class="label">Real-Time</span><span class="value"><span class="badge badge-$defStatus">$rtProtection</span></span>
    <span class="label">Last Quick Scan</span><span class="value">$lastScan</span>
    <span class="label">Last Full Scan</span><span class="value">$lastFullScan</span>
    <span class="label">Firewall</span><span class="value">$fwHtml</span>
  </div>
</div>

<!-- Gateway Status -->
<div class="card">
  <h2><span class="icon">⚡</span> OpenClaw Gateway</h2>
  <div class="kv">
    <span class="label">Status</span><span class="value"><span class="badge badge-$gatewayStatus">$gatewayRunning</span></span>
    <span class="label">RAM Usage</span><span class="value">$gatewayRam</span>
  </div>
</div>

<!-- Running Services -->
<div class="card">
  <h2><span class="icon">⚙️</span> Services</h2>
  <div class="kv" style="margin-bottom:12px">
    <span class="label">Running</span><span class="value">$svcCount services</span>
    <span class="label">Flagged</span><span class="value"><span class="badge badge-$(if($suspiciousSvcs.Count -gt 0){'warn'}else{'good'})">$($suspiciousSvcs.Count) suspicious</span></span>
  </div>
  $(if($svcsHtml){@"
  <div class="scrollable"><table><tr><th>Name</th><th>Display Name</th><th>Status</th></tr>$svcsHtml</table></div>
"@})
</div>

<!-- Open Ports -->
<div class="card">
  <h2><span class="icon">🔌</span> Open Ports ($($listeners.Count) listening)</h2>
  <div class="scrollable">
    <table><tr><th>Port</th><th>Address</th><th>Process</th><th>PID</th></tr>
    $portsHtml
    </table>
  </div>
</div>

<!-- Active Connections -->
<div class="card">
  <h2><span class="icon">🔗</span> Active Connections (top 20)</h2>
  <div class="scrollable">
    <table><tr><th>Process</th><th>Count</th><th>Remote Endpoints</th></tr>
    $connsHtml
    </table>
  </div>
</div>

<!-- Recent Logins -->
<div class="card">
  <h2><span class="icon">👤</span> Recent Logins</h2>
  <div class="scrollable">
    <table><tr><th>Time</th><th>User</th><th>Type</th></tr>
    $loginsHtml
    </table>
  </div>
</div>

<!-- Startup Programs -->
<div class="card">
  <h2><span class="icon">🚀</span> Startup Programs</h2>
  <div class="scrollable">
    <table><tr><th>Name</th><th>Command</th><th>Hive</th></tr>
    $startupHtml
    </table>
  </div>
</div>

<!-- Top Processes by RAM -->
<div class="card">
  <h2><span class="icon">🔍</span> Top Processes by Memory</h2>
  <div class="scrollable">
    <table><tr><th>Process</th><th>PID</th><th>RAM</th></tr>
    $suspProcHtml
    </table>
  </div>
</div>

<!-- Scheduled Tasks -->
<div class="card">
  <h2><span class="icon">📋</span> Scheduled Tasks (non-Microsoft)</h2>
  <div class="scrollable">
    <table><tr><th>Task</th><th>Author</th><th>Path</th></tr>
    $tasksHtml
    </table>
  </div>
</div>

</div>

<div style="text-align:center; padding:24px; color:var(--text-dim); font-size:0.8rem;">
  Security Dashboard &bull; Generated $timestamp &bull; Run <code>refresh.ps1</code> to update
</div>

</body>
</html>
"@

# Output to file directly with UTF8 encoding
$outputPath = Join-Path $PSScriptRoot "security.html"
[System.IO.File]::WriteAllText($outputPath, $html, [System.Text.UTF8Encoding]::new($false))
Write-Host "Dashboard written to $outputPath"
