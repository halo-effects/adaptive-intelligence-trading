@echo off
cd /d "C:\Users\Never\.openclaw\workspace"
"C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe" -B -u -m trading.spot.run_v14_portfolio_live_aster --capital 340 --confirm --skip-backfill
