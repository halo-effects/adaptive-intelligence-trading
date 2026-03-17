Set objShell = CreateObject("WScript.Shell")
objShell.Run "powershell.exe -NonInteractive -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command ""Set-Location 'C:\Users\Never\.openclaw\workspace'; & 'C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe' -u -m trading.spot.run_v14_live_aster --confirm --skip-backfill""", 0, False
