import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import requests, time
from datetime import datetime, timezone, timedelta

start_ms = int((datetime.now(timezone.utc) - timedelta(days=90)).timestamp() * 1000)
url = "https://fapi.asterdex.com/fapi/v1/klines"

# Test 3 symbols
for sym in ["BTCUSDT", "HYPEUSDT", "BERAUSDT"]:
    t0 = time.time()
    try:
        r = requests.get(url, params={"symbol": sym, "interval": "1d", "startTime": start_ms, "limit": 95}, timeout=5)
        r.raise_for_status()
        data = r.json()
        elapsed = time.time() - t0
        print(f"{sym}: {len(data)} daily candles ({elapsed:.1f}s)")
    except Exception as e:
        print(f"{sym}: ERROR {e}")
