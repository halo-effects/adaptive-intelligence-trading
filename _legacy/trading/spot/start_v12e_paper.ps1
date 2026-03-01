$python = "C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe"
$script = "C:\Users\Never\.openclaw\workspace\trading\spot\run_v12e_paper.py"
$env:PYTHONIOENCODING = "utf-8"
$env:CFGI_API_KEY = [System.Environment]::GetEnvironmentVariable('CFGI_API_KEY', 'User')
& $python $script --profile medium --capital 10000 --timeframe 1h --exchange hyperliquid
