@echo off
cd /d C:\Users\Never\.openclaw\workspace
"C:\Users\Never\AppData\Local\Programs\Python\Python312\python.exe" -u -m trading.spot.run_v14_live_aster --confirm --skip-backfill >> "C:\Users\Never\.openclaw\workspace\trading\spot\live\v14\stdout.log" 2>&1
