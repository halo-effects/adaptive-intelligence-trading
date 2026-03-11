# Restart PM and Live bots for CFGI fix
$tasks = @('V14PMPaperBot', 'V14LiveAster')

$procs = Get-Process python*, python3* -ErrorAction SilentlyContinue | Where-Object {
    try { $_.CommandLine -match 'portfolio_paper|live_aster' } catch { $false }
}
if ($procs) {
    Write-Host "Killing $($procs.Count) processes..."
    $procs | ForEach-Object { Stop-Process -Id $_.Id -Force }
    Start-Sleep -Seconds 3
}

foreach ($t in $tasks) {
    Start-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
    Write-Host "Started $t"
}

Start-Sleep -Seconds 15
foreach ($t in $tasks) {
    $info = Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
    Write-Host "$t => $($info.State)"
}
