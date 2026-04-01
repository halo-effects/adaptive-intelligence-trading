Get-Process python -ErrorAction SilentlyContinue | Select-Object Id, Path | Format-Table -AutoSize
