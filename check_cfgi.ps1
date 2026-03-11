Start-Sleep -Seconds 60
$pm = Get-Content 'C:\Users\Never\.openclaw\workspace\trading\spot\paper\v14_portfolio\status.json' | ConvertFrom-Json
Write-Host "PM fear_greed_index: $($pm.fear_greed_index)"
Write-Host "PM coins with CFGI:"
foreach ($sym in $pm.symbols) {
    $c = $pm.coins.$sym
    Write-Host "  $sym => cfgi: $($c.cfgi)"
}
Write-Host ""
$live = Get-Content 'C:\Users\Never\.openclaw\workspace\trading\spot\live\v14\status.json' | ConvertFrom-Json
Write-Host "Live fear_greed_index: $($live.fear_greed_index)"
foreach ($sym in $live.symbols) {
    $c = $live.coins.$sym
    Write-Host "  $sym => cfgi: $($c.cfgi)"
}
