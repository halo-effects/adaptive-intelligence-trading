Set objShell = CreateObject("WScript.Shell")
objShell.Run "powershell.exe -NonInteractive -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File ""C:\Users\Never\.openclaw\workspace\trading\sync_dashboard.ps1""", 0, False
