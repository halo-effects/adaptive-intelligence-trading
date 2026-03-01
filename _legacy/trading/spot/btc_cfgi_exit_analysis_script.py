#!/usr/bin/env python3
"""BTC CFGI Exit Analysis V2 — captures every EXIT transition from V12e backtest,
cross-references with BTC per-coin CFGI, and computes forward returns."""

import sys, json, logging, os
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Setup path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import pandas as pd
import numpy as np

from trading.spot.backtest_engine_v12 import SpotBacktestEngineV12, LifecyclePhase
from trading.spot.macro_indicators import load_historical_fear_greed

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).resolve().parent / "data"
CACHE_DIR = DATA_DIR / "dwell_cache"
RESULTS_DIR = Path(__file__).resolve().parent / "backtest_results" / "v12_lifecycle"

# Load BTC CFGI
cfgi_path = DATA_DIR / "cfgi_cache" / "BTC_cfgi_daily.json"
CFGI_DATA = json.loads(cfgi_path.read_text()) if cfgi_path.exists() else {}
print(f"Loaded {len(CFGI_DATA)} BTC CFGI entries")
print(f"CFGI date range: {min(CFGI_DATA.keys()) if CFGI_DATA else 'N/A'} to {max(CFGI_DATA.keys()) if CFGI_DATA else 'N/A'}")

# Collect all 1h candle data for BTC
def load_all_btc_candles():
    """Load all cached BTC 1h candles."""
    frames = []
    for f in sorted(CACHE_DIR.glob("BTC_USDT_1h_*.csv")):
        df = pd.read_csv(f)
        frames.append(df)
    if not frames:
        raise RuntimeError("No BTC candle data found in dwell_cache")
    combined = pd.concat(frames, ignore_index=True)
    combined = combined.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
    print(f"Loaded {len(combined)} BTC 1h candles")
    print(f"Date range: {datetime.utcfromtimestamp(combined['timestamp'].iloc[0]/1000)} to {datetime.utcfromtimestamp(combined['timestamp'].iloc[-1]/1000)}")
    return combined

all_candles = load_all_btc_candles()

# Build daily close lookup for forward returns
all_candles["dt"] = pd.to_datetime(all_candles["timestamp"], unit="ms", utc=True)
daily = all_candles.set_index("dt").resample("1D").agg({"close": "last"}).dropna()
daily_closes = daily["close"]

def get_forward_return(date_str, days):
    """Get % return from date_str + days forward."""
    try:
        dt = pd.Timestamp(date_str, tz="UTC")
        target = dt + timedelta(days=days)
        # Find closest available date
        mask = daily_closes.index >= target
        if not mask.any():
            return None
        future_price = daily_closes[mask].iloc[0]
        base_mask = daily_closes.index >= dt
        if not base_mask.any():
            return None
        base_price = daily_closes[base_mask].iloc[0]
        return round((future_price - base_price) / base_price * 100, 2)
    except:
        return None

def get_cfgi_for_date(date_str):
    """Get BTC CFGI for a date string (YYYY-MM-DD)."""
    # Try exact match first
    if date_str in CFGI_DATA:
        return CFGI_DATA[date_str]
    # Try nearby dates (±1 day)
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    for delta in [1, -1, 2, -2]:
        alt = (dt + timedelta(days=delta)).strftime("%Y-%m-%d")
        if alt in CFGI_DATA:
            return CFGI_DATA[alt]
    return None

# ---- Monkey-patch to capture EXIT transitions ----
EXIT_LOG = []

original_transition = SpotBacktestEngineV12._transition_to_exit

def patched_transition(self, price, ts, ts_ms, daily_score):
    dt = datetime.utcfromtimestamp(ts_ms / 1000)
    date_str = dt.strftime("%Y-%m-%d")
    EXIT_LOG.append({
        "date": date_str,
        "datetime": dt.isoformat(),
        "price": round(price, 2),
        "conductor_score": round(daily_score, 1),
        "ts_ms": ts_ms,
    })
    return original_transition(self, price, ts, ts_ms, daily_score)

SpotBacktestEngineV12._transition_to_exit = patched_transition

# ---- Run the backtest (same as run_v12_chained.py btc medium) ----
from trading.spot.run_v12_chained import run_chained, PRESETS, DEFAULT_V12_PARAMS, V12_PROFILE_OVERRIDES

preset = PRESETS["btc"]
fg = load_historical_fear_greed()

print(f"\nRunning BTC Medium V12e backtest...")
print(f"Period: {preset['start']} to {preset['end']}")

result, chunks = run_chained(
    symbol=preset["symbol"],
    timeframe="1h",
    start=preset["start"],
    end=preset["end"],
    capital=preset["capital"],
    fg=fg,
    v12_params=DEFAULT_V12_PARAMS,
    profile="medium",
    exchange="binance",
)

print(f"\nBacktest complete. {len(EXIT_LOG)} EXIT transitions captured.")

# ---- Build analysis ----
print("\n" + "="*80)
print("EXIT TRANSITION DETAILS")
print("="*80)

# Deduplicate (same date might fire multiple times in same candle loop)
seen_dates = set()
unique_exits = []
for e in EXIT_LOG:
    if e["date"] not in seen_dates:
        seen_dates.add(e["date"])
        unique_exits.append(e)

print(f"Unique EXIT dates: {len(unique_exits)}")

# Enrich with CFGI and forward returns
for e in unique_exits:
    e["cfgi"] = get_cfgi_for_date(e["date"])
    e["fwd_7d"] = get_forward_return(e["date"], 7)
    e["fwd_14d"] = get_forward_return(e["date"], 14)
    e["fwd_30d"] = get_forward_return(e["date"], 30)
    e["fwd_60d"] = get_forward_return(e["date"], 60)

# ---- Generate markdown report ----
lines = []
lines.append("# BTC CFGI Exit Analysis V2")
lines.append("")
lines.append(f"**Generated**: 2025-02-22")
lines.append(f"**Engine**: V12e backtest_engine_v12.py")
lines.append(f"**Profile**: Medium")
lines.append(f"**Period**: {preset['start']} to {preset['end']}")
lines.append(f"**Total EXIT transitions**: {len(unique_exits)}")
lines.append(f"**CFGI data range**: {min(CFGI_DATA.keys()) if CFGI_DATA else 'N/A'} to {max(CFGI_DATA.keys()) if CFGI_DATA else 'N/A'}")
lines.append("")

# Step 2: All exits table
lines.append("## All EXIT Transitions")
lines.append("")
lines.append("| # | Date | Price | Conductor | BTC CFGI | 7d % | 14d % | 30d % | 60d % |")
lines.append("|---|------|-------|-----------|----------|------|-------|-------|-------|")

pre_cfgi = []
with_cfgi = []

for i, e in enumerate(unique_exits):
    cfgi_str = str(int(e["cfgi"])) if e["cfgi"] is not None else "N/A"
    fwd = lambda k: f"{e[k]:+.1f}" if e[k] is not None else "N/A"
    lines.append(f"| {i+1} | {e['date']} | ${e['price']:,.0f} | {e['conductor_score']:.0f} | {cfgi_str} | {fwd('fwd_7d')} | {fwd('fwd_14d')} | {fwd('fwd_30d')} | {fwd('fwd_60d')} |")
    
    if e["cfgi"] is None:
        pre_cfgi.append(e)
    else:
        with_cfgi.append(e)

lines.append("")

# Step 4: Pre-CFGI exits
lines.append("## Exits Without CFGI Data (Pre-July 2022)")
lines.append("")
if pre_cfgi:
    lines.append("| # | Date | Price | Conductor | 7d % | 14d % | 30d % | 60d % |")
    lines.append("|---|------|-------|-----------|------|-------|-------|-------|")
    for i, e in enumerate(pre_cfgi):
        fwd = lambda k: f"{e[k]:+.1f}" if e[k] is not None else "N/A"
        lines.append(f"| {i+1} | {e['date']} | ${e['price']:,.0f} | {e['conductor_score']:.0f} | {fwd('fwd_7d')} | {fwd('fwd_14d')} | {fwd('fwd_30d')} | {fwd('fwd_60d')} |")
else:
    lines.append("*None*")
lines.append("")

# Step 3: CFGI gating analysis
lines.append("## CFGI Gate Analysis")
lines.append("")
lines.append("Only exits WITH CFGI data are analyzed below.")
lines.append("")

for threshold in [65, 70, 75, 80]:
    passing = [e for e in with_cfgi if e["cfgi"] >= threshold]
    blocked = [e for e in with_cfgi if e["cfgi"] < threshold]
    
    lines.append(f"### Gate: CFGI >= {threshold}")
    lines.append("")
    lines.append(f"- **Total with CFGI**: {len(with_cfgi)}")
    lines.append(f"- **Pass**: {len(passing)}")
    lines.append(f"- **Blocked**: {len(blocked)}")
    lines.append("")
    
    if passing:
        lines.append("**Exits that PASS:**")
        lines.append("")
        lines.append("| Date | Price | Conductor | CFGI | 7d % | 14d % | 30d % | 60d % |")
        lines.append("|------|-------|-----------|------|------|-------|-------|-------|")
        for e in passing:
            fwd = lambda k, e=e: f"{e[k]:+.1f}" if e[k] is not None else "N/A"
            lines.append(f"| {e['date']} | ${e['price']:,.0f} | {e['conductor_score']:.0f} | {int(e['cfgi'])} | {fwd('fwd_7d')} | {fwd('fwd_14d')} | {fwd('fwd_30d')} | {fwd('fwd_60d')} |")
        lines.append("")
        
        lines.append("**Exits that are BLOCKED:**")
        lines.append("")
        if blocked:
            lines.append("| Date | Price | Conductor | CFGI | 7d % | 14d % | 30d % | 60d % |")
            lines.append("|------|-------|-----------|------|------|-------|-------|-------|")
            for e in blocked:
                fwd = lambda k, e=e: f"{e[k]:+.1f}" if e[k] is not None else "N/A"
                lines.append(f"| {e['date']} | ${e['price']:,.0f} | {e['conductor_score']:.0f} | {int(e['cfgi'])} | {fwd('fwd_7d')} | {fwd('fwd_14d')} | {fwd('fwd_30d')} | {fwd('fwd_60d')} |")
        else:
            lines.append("*None blocked*")
        lines.append("")
    else:
        lines.append("*No exits pass this threshold.*")
        lines.append("")

# Summary stats
lines.append("## Summary Statistics")
lines.append("")
lines.append("| Metric | Value |")
lines.append("|--------|-------|")
lines.append(f"| Total EXIT transitions | {len(unique_exits)} |")
lines.append(f"| With CFGI data | {len(with_cfgi)} |")
lines.append(f"| Without CFGI data (pre-July 2022) | {len(pre_cfgi)} |")

if with_cfgi:
    cfgi_vals = [e["cfgi"] for e in with_cfgi]
    lines.append(f"| CFGI range | {min(cfgi_vals):.0f} - {max(cfgi_vals):.0f} |")
    lines.append(f"| CFGI mean | {np.mean(cfgi_vals):.1f} |")
    lines.append(f"| CFGI median | {np.median(cfgi_vals):.1f} |")

lines.append("")

# Write output
output_path = Path(__file__).resolve().parent / "btc_cfgi_exit_analysis_v2.md"
output_path.write_text("\n".join(lines), encoding="utf-8")
print(f"\nReport written to: {output_path}")

# Also dump raw data as JSON for reference
raw_path = Path(__file__).resolve().parent / "btc_cfgi_exit_analysis_v2_raw.json"
raw_path.write_text(json.dumps(unique_exits, indent=2, default=str), encoding="utf-8")
print(f"Raw data written to: {raw_path}")
