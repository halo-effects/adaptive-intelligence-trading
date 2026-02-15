Stop-ScheduledTask -TaskName 'AsterTradingBot'
Start-Sleep 2
Get-Process python* -ErrorAction SilentlyContinue | ForEach-Object { 
    if ($_.Id -ne 10528 -and $_.Id -ne 13192) { 
        Stop-Process -Id $_.Id -Force 
    } 
}
Start-Sleep 3
Start-ScheduledTask -TaskName 'AsterTradingBot'
Start-Sleep 12
Get-Content C:\Users\Never\.openclaw\workspace\trading\live\bot_service.log -Tail 15
