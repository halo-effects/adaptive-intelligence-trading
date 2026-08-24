"""Pull TON legacy funding rates and add to the export as funding-GRAM-legacy-TON.csv"""
import csv
import io
import json
import requests
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

EXPORT_DIR = Path(__file__).resolve().parent.parent / "exports" / "funding-rate-signal-export"
LOOKBACK_MS = int((datetime.now(timezone.utc) - timedelta(days=548)).timestamp() * 1000)

def ms_to_iso(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

print("Fetching TON legacy funding rates from Binance...")
all_rows = []
start_time = LOOKBACK_MS
endpoint = "https://fapi.binance.com/fapi/v1/fundingRate"

while True:
    resp = requests.get(endpoint, params={"symbol": "TONUSDT", "startTime": start_time, "limit": 1000}, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    if not data:
        break
    for item in data:
        all_rows.append({
            "funding_time_utc": ms_to_iso(int(item["fundingTime"])),
            "funding_time_ms": int(item["fundingTime"]),
            "funding_rate": item["fundingRate"],
        })
    last_ts = int(data[-1]["fundingTime"])
    if last_ts <= start_time or len(data) < 1000:
        break
    start_time = last_ts + 1
    time.sleep(0.3)

print(f"  Got {len(all_rows)} TON funding rates")
if all_rows:
    print(f"  Range: {all_rows[0]['funding_time_utc']} to {all_rows[-1]['funding_time_utc']}")

# Write CSV
out_path = EXPORT_DIR / "funding" / "funding-GRAM-legacy-TON.csv"
with open(out_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["funding_time_utc", "funding_rate"])
    for row in all_rows:
        writer.writerow([row["funding_time_utc"], row["funding_rate"]])
print(f"  Written: {out_path}")

# Update manifest
manifest_path = EXPORT_DIR / "manifest.json"
with open(manifest_path, "r", encoding="utf-8") as f:
    manifest = json.load(f)

manifest["coins"]["GRAM"]["funding_legacy_ton"] = {
    "source": "binance",
    "endpoint": "/fapi/v1/fundingRate",
    "symbol_used": "TONUSDT",
    "note": "GRAM was renamed from TON on 2026-06-15. This file contains the pre-rename funding history under the TON ticker. Same token, same contract.",
    "rows": len(all_rows),
    "first": all_rows[0]["funding_time_utc"] if all_rows else None,
    "last": all_rows[-1]["funding_time_utc"] if all_rows else None,
}

with open(manifest_path, "w", encoding="utf-8") as f:
    json.dump(manifest, f, indent=2, ensure_ascii=False)
print("  Manifest updated")

# Re-zip
import zipfile, os
zip_path = EXPORT_DIR.parent / f"funding-rate-signal-export-20260705.zip"
with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
    for root, dirs, files in os.walk(EXPORT_DIR):
        for file in files:
            fp = Path(root) / file
            zf.write(fp, fp.relative_to(EXPORT_DIR))

print(f"  ZIP updated: {zip_path} ({zip_path.stat().st_size / 1_048_576:.1f} MB)")
